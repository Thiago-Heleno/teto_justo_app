from datetime import datetime, timedelta, timezone
import logging
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from fastapi import BackgroundTasks, HTTPException

from schemas.notificacao import DispositivoPushRegistrar, TicketPush
from services.score import ServicoScore


_URL_EXPO = "https://exp.host/--/api/v2/push/send"
_URL_RECIBOS_EXPO = "https://exp.host/--/api/v2/push/getReceipts"
_LIMITE_LOTE = 100
_LIMITE_LOTE_RECIBOS = 1000
_TIMEOUT_SEGUNDOS = 10
_LOGGER = logging.getLogger(__name__)
_ERROS_RECIBO = {
    "MessageTooBig", "MessageRateExceeded", "MismatchSenderId", "InvalidCredentials",
}
_MENSAGENS_TAREFA = {
    "tarefa_atribuida": ("Nova tarefa para você", "Uma tarefa foi atribuída a você."),
    "prazo_alterado": ("Prazo da tarefa alterado", "O prazo de uma tarefa sua foi atualizado."),
    "atribuicao_removida": (
        "Responsável pela tarefa alterado", "Você deixou de ser responsável por uma tarefa."
    ),
    "prazo_encerrado": (
        "Prazo de execução encerrado", "O prazo para concluir uma tarefa sua foi encerrado."
    ),
}


class ServicoNotificacao:
    def __init__(self, supabase_client, tarefas_fundo: BackgroundTasks | None = None):
        self.supabase = supabase_client
        self.tarefas_fundo = tarefas_fundo

    def notificar_tarefa(
        self, tipo: str, tarefa: dict, ids_usuarios: list[str] | None = None
    ) -> None:
        if ids_usuarios == []:
            return
        argumentos = (tipo, dict(tarefa), list(ids_usuarios) if ids_usuarios is not None else None)
        if self.tarefas_fundo is not None:
            self.tarefas_fundo.add_task(self._notificar_tarefa, *argumentos)
        else:
            self._notificar_tarefa(*argumentos)

    def _notificar_tarefa(self, tipo: str, tarefa: dict, ids_usuarios: list[str] | None) -> None:
        try:
            if "fk_casa_id" not in tarefa:
                registros = (
                    self.supabase.table("tarefa").select("id,fk_casa_id")
                    .eq("id", str(tarefa["id"])).execute()
                ).data or []
                if not registros:
                    return
                tarefa = registros[0]
            if ids_usuarios is None:
                ids_usuarios = self._responsaveis(tarefa["id"])
            titulo, mensagem = _MENSAGENS_TAREFA[tipo]
            self._enviar_aviso_normal(
                ids_usuarios, titulo, mensagem,
                {
                    "tipo": tipo, "tarefa_id": str(tarefa["id"]),
                    "casa_id": str(tarefa["fk_casa_id"]),
                },
            )
        except Exception:
            # A notificação é secundária; não propaga erros nem detalhes que contenham tokens.
            _LOGGER.warning("Não foi possível preparar uma notificação normal.")

    def _responsaveis(self, id_tarefa: str) -> list[str]:
        registros = (
            self.supabase.table("atribuida").select("fk_usuario_id")
            .eq("fk_tarefa_id", str(id_tarefa)).execute()
        ).data or []
        return list(dict.fromkeys(str(item["fk_usuario_id"]) for item in registros))

    def reiniciar_aviso_inicio(self, tarefa: dict) -> None:
        if self.tarefas_fundo is not None:
            self.tarefas_fundo.add_task(self._reiniciar_aviso_inicio, dict(tarefa))
        else:
            self._reiniciar_aviso_inicio(tarefa)

    def _reiniciar_aviso_inicio(self, tarefa: dict) -> None:
        if not tarefa.get("data_inicio"):
            return
        try:
            (
                self.supabase.table("tarefa").update({"aviso_inicio_tentado_em": None})
                .eq("id", str(tarefa["id"])).eq("data_inicio", tarefa["data_inicio"])
                .eq("estado_atual", "pendente").execute()
            )
        except Exception:
            _LOGGER.warning("Não foi possível reiniciar o aviso de início da tarefa.")

    def _enviar_aviso_normal(
        self, usuarios: list[str], titulo: str, mensagem: str, dados: dict
    ) -> dict:
        try:
            return self.enviar_push(
                [UUID(str(usuario)) for usuario in usuarios], titulo, mensagem, dados
            )
        except Exception:
            _LOGGER.warning("Não foi possível enviar uma notificação normal.")
            return {"aceitos": [], "invalidos": [], "falhas": [{"erro": "EnvioNaoConfirmado"}]}

    def avisar_inicios(self, agora: datetime | None = None) -> dict[str, int]:
        instante = agora or datetime.now(timezone.utc)
        if instante.tzinfo is None or instante.utcoffset() is None:
            raise ValueError("O instante do processamento deve conter fuso horário.")
        instante = instante.astimezone(timezone.utc)
        limite = instante + timedelta(hours=24)
        tarefas = []
        while True:
            pagina = (
                self.supabase.table("tarefa")
                .select("id,fk_casa_id,data_inicio,rotatividade_id")
                .eq("estado_atual", "pendente")
                .is_("aviso_inicio_tentado_em", "null")
                .gt("data_inicio", instante.isoformat())
                .lte("data_inicio", limite.isoformat())
                .order("id").range(len(tarefas), len(tarefas) + 99).execute()
            ).data or []
            tarefas.extend(pagina)
            if len(pagina) < 100:
                break

        resultado = {"tarefas_elegiveis": len(tarefas), "avisos_enviados": 0, "falhas": 0}
        resumos = {}
        for tarefa in tarefas:
            usuarios = self._responsaveis(tarefa["id"])
            if not usuarios:
                continue
            reserva = (
                self.supabase.table("tarefa")
                .update({"aviso_inicio_tentado_em": instante.isoformat()})
                .eq("id", tarefa["id"]).eq("data_inicio", tarefa["data_inicio"])
                .eq("estado_atual", "pendente").is_("aviso_inicio_tentado_em", "null").execute()
            )
            if not reserva.data:
                continue
            if tarefa.get("rotatividade_id"):
                for usuario in usuarios:
                    chave = (usuario, str(tarefa["fk_casa_id"]))
                    resumos[chave] = resumos.get(chave, 0) + 1
                continue
            envio = self._enviar_aviso_normal(
                usuarios, "Sua tarefa começa em breve",
                "Uma tarefa sua começa nas próximas 24 horas.",
                {
                    "tipo": "inicio_tarefa", "tarefa_id": tarefa["id"],
                    "casa_id": tarefa["fk_casa_id"],
                },
            )
            resultado["avisos_enviados"] += len(envio["aceitos"])
            resultado["falhas"] += len(envio["falhas"])

        for (usuario, casa), quantidade in resumos.items():
            mensagem = (
                "Você tem uma tarefa do rodízio começando nas próximas 24 horas."
                if quantidade == 1 else
                f"Você tem {quantidade} tarefas do rodízio começando nas próximas 24 horas."
            )
            envio = self._enviar_aviso_normal(
                [usuario], "Novas tarefas do rodízio", mensagem,
                {"tipo": "rodizio_distribuido", "casa_id": casa},
            )
            resultado["avisos_enviados"] += len(envio["aceitos"])
            resultado["falhas"] += len(envio["falhas"])
        return resultado

    def registrar_dispositivo(
        self, id_usuario: UUID, dados: DispositivoPushRegistrar
    ) -> dict:
        resposta = (
            self.supabase.table("dispositivo_push")
            .upsert(
                {"fk_usuario_id": str(id_usuario), **dados.model_dump()},
                on_conflict="token",
            )
            .execute()
        )
        if not resposta.data:
            raise HTTPException(
                status_code=503, detail="Não foi possível registrar o dispositivo."
            )
        return resposta.data[0]

    def remover_dispositivo(self, id_usuario: UUID | str, token: str) -> None:
        (
            self.supabase.table("dispositivo_push")
            .delete()
            .eq("fk_usuario_id", str(id_usuario))
            .eq("token", token)
            .execute()
        )

    @staticmethod
    def _data_horaria(valor: str | datetime) -> datetime:
        if isinstance(valor, datetime):
            data = valor
        else:
            data = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        if data.tzinfo is None or data.utcoffset() is None:
            return data.replace(tzinfo=timezone.utc)
        return data.astimezone(timezone.utc)

    def _fuso_tarefa(self, tarefa: dict) -> ZoneInfo:
        # O fuso pertence à casa, não à tabela tarefa.
        try:
            resposta = (
                self.supabase.table("casa")
                .select("timezone")
                .eq("id", tarefa["fk_casa_id"])
                .execute()
            )
            nome_fuso = (resposta.data or [{}])[0].get("timezone")
            return ZoneInfo(nome_fuso or "America/Sao_Paulo")
        except Exception:
            # Mantém o job resiliente e compatível com casas legadas.
            return ZoneInfo("America/Sao_Paulo")

    def avisar_vencimentos(self, agora: datetime | None = None) -> dict[str, int]:
        instante = agora or datetime.now(timezone.utc)
        if instante.tzinfo is None or instante.utcoffset() is None:
            raise ValueError("O instante do processamento deve conter fuso horário.")
        instante = instante.astimezone(timezone.utc)
        limite = instante + timedelta(hours=36)

        tarefas_hoje = []
        while True:
            pagina = (
                self.supabase.table("tarefa")
                .select(
                    "id,fk_casa_id,data_inicio,data_fim,estado_atual,atraso_maximo,"
                    "aviso_enviado_em"
                )
                .in_("estado_atual", ["pendente", "atrasada"])
                .is_("aviso_enviado_em", "null")
                .gt("data_fim", instante.isoformat())
                .lte("data_fim", limite.isoformat())
                .order("id")
                .range(len(tarefas_hoje), len(tarefas_hoje) + 99)
                .execute()
            ).data or []
            tarefas_hoje.extend(pagina)
            if len(pagina) < 100:
                break

        tarefas_atrasadas = []
        while True:
            pagina = (
                self.supabase.table("tarefa")
                .select(
                    "id,fk_casa_id,data_fim,estado_atual,atraso_maximo,"
                    "aviso_atraso_enviado_em"
                )
                .in_("estado_atual", ["pendente", "atrasada"])
                .is_("aviso_atraso_enviado_em", "null")
                .lte("data_fim", instante.isoformat())
                .order("id")
                .range(len(tarefas_atrasadas), len(tarefas_atrasadas) + 99)
                .execute()
            ).data or []
            tarefas_atrasadas.extend(pagina)
            if len(pagina) < 100:
                break

        resultado = {"tarefas_elegiveis": 0, "avisos_enviados": 0, "falhas": 0}
        for tarefa in tarefas_hoje:
            data_fim = self._data_horaria(tarefa["data_fim"])
            fuso = self._fuso_tarefa(tarefa)
            hoje_local = instante.astimezone(fuso).date()
            if data_fim.astimezone(fuso).date() != hoje_local:
                continue
            data_inicio = tarefa.get("data_inicio")
            if data_inicio and self._data_horaria(data_inicio) > instante:
                continue

            atribuicoes = (
                self.supabase.table("atribuida")
                .select("fk_usuario_id")
                .eq("fk_tarefa_id", tarefa["id"])
                .execute()
            ).data or []
            if not atribuicoes:
                continue

            reserva = (
                self.supabase.table("tarefa")
                .update({"aviso_enviado_em": instante.isoformat()})
                .eq("id", tarefa["id"])
                .eq("data_fim", tarefa["data_fim"])
                .in_("estado_atual", ["pendente", "atrasada"])
                .is_("aviso_enviado_em", "null")
                .execute()
            )
            if not reserva.data:
                continue

            resultado["tarefas_elegiveis"] += 1
            envio = self.enviar_push(
                [UUID(item["fk_usuario_id"]) for item in atribuicoes],
                "Sua tarefa vence hoje",
                "A tarefa vence hoje e já pode ser concluída.",
                {
                    "tipo": "tarefa_vence_hoje",
                    "tarefa_id": tarefa["id"],
                    "casa_id": tarefa["fk_casa_id"],
                },
            )
            resultado["avisos_enviados"] += len(envio["aceitos"])
            resultado["falhas"] += len(envio["falhas"])

        for tarefa in tarefas_atrasadas:
            data_fim = self._data_horaria(tarefa["data_fim"])
            dias_atraso = ServicoScore.calcular_dias_atraso(data_fim, instante)
            if dias_atraso <= 0 or dias_atraso > tarefa["atraso_maximo"]:
                continue

            atribuicoes = (
                self.supabase.table("atribuida")
                .select("fk_usuario_id")
                .eq("fk_tarefa_id", tarefa["id"])
                .execute()
            ).data or []
            if not atribuicoes:
                continue

            reserva = (
                self.supabase.table("tarefa")
                .update({"aviso_atraso_enviado_em": instante.isoformat()})
                .eq("id", tarefa["id"])
                .eq("data_fim", tarefa["data_fim"])
                .in_("estado_atual", ["pendente", "atrasada"])
                .is_("aviso_atraso_enviado_em", "null")
                .execute()
            )
            if not reserva.data:
                continue

            resultado["tarefas_elegiveis"] += 1
            envio = self.enviar_push(
                [UUID(item["fk_usuario_id"]) for item in atribuicoes],
                "Sua tarefa está atrasada",
                "A tarefa está atrasada, mas ainda pode ser concluída.",
                {
                    "tipo": "tarefa_atrasada",
                    "tarefa_id": tarefa["id"],
                    "casa_id": tarefa["fk_casa_id"],
                },
            )
            resultado["avisos_enviados"] += len(envio["aceitos"])
            resultado["falhas"] += len(envio["falhas"])
        return resultado

    def enviar_push(
        self,
        ids_usuarios: list[UUID],
        titulo: str,
        mensagem: str,
        dados: dict | None = None,
    ) -> dict:
        resultado = {"aceitos": [], "invalidos": [], "falhas": []}
        if not ids_usuarios:
            return resultado

        ids = list(dict.fromkeys(str(id_usuario) for id_usuario in ids_usuarios))
        dispositivos = []
        while True:
            pagina = (
                self.supabase.table("dispositivo_push")
                .select("id,token,fk_usuario_id")
                .in_("fk_usuario_id", ids)
                .order("id")
                .range(len(dispositivos), len(dispositivos) + _LIMITE_LOTE - 1)
                .execute()
            ).data or []
            dispositivos.extend(pagina)
            if len(pagina) < _LIMITE_LOTE:
                break

        # Carrega todas as páginas antes das exclusões para não deslocar os offsets.
        for inicio in range(0, len(dispositivos), _LIMITE_LOTE):
            lote = dispositivos[inicio : inicio + _LIMITE_LOTE]
            mensagens = [
                {
                    "to": dispositivo["token"],
                    "title": titulo,
                    "body": mensagem,
                    **(
                        {"categoryId": "tarefa_pendente"}
                        if dados and dados.get("tipo") in {"tarefa_vence_hoje", "tarefa_atrasada"}
                        else {}
                    ),
                    **({"data": dados} if dados is not None else {}),
                }
                for dispositivo in lote
            ]
            try:
                resposta = httpx.post(
                    _URL_EXPO, json=mensagens, timeout=_TIMEOUT_SEGUNDOS
                )
                resposta.raise_for_status()
                conteudo = resposta.json()
                tickets = conteudo.get("data") if isinstance(conteudo, dict) else None
                if (
                    not isinstance(tickets, list)
                    or len(tickets) != len(lote)
                    or conteudo.get("errors")
                ):
                    raise ValueError("Resposta de push inválida.")
            except (httpx.HTTPError, ValueError):
                resultado["falhas"].extend(
                    {"dispositivo_id": d["id"], "erro": "EnvioNaoConfirmado"}
                    for d in lote
                )
                continue

            for dispositivo, ticket in zip(lote, tickets):
                status = ticket.get("status") if isinstance(ticket, dict) else None
                if status == "ok" and isinstance(ticket.get("id"), str) and ticket["id"]:
                    resultado["aceitos"].append(
                        {
                            "dispositivo_id": dispositivo["id"],
                            "usuario_id": dispositivo["fk_usuario_id"],
                            "ticket_id": ticket["id"],
                        }
                    )
                    continue

                detalhes = ticket.get("details") if isinstance(ticket, dict) else None
                if (
                    status == "error"
                    and isinstance(detalhes, dict)
                    and detalhes.get("error") == "DeviceNotRegistered"
                ):
                    # Um cadastro reassociado a outra conta não é apagado por envio antigo.
                    self.remover_dispositivo(
                        dispositivo["fk_usuario_id"], dispositivo["token"]
                    )
                    resultado["invalidos"].append(dispositivo["id"])
                else:
                    resultado["falhas"].append(
                        {
                            "dispositivo_id": dispositivo["id"],
                            "erro": "EnvioRecusado" if status == "error" else "EnvioNaoConfirmado",
                        }
                    )

        return resultado

    def consultar_recibos(self, tickets: list[TicketPush]) -> dict:
        resultado = {"confirmados": [], "invalidos": [], "pendentes": [], "falhas": []}
        for inicio in range(0, len(tickets), _LIMITE_LOTE_RECIBOS):
            lote = {
                str(ticket.ticket_id): ticket.model_dump(mode="json")
                for ticket in tickets[inicio : inicio + _LIMITE_LOTE_RECIBOS]
            }
            try:
                resposta = httpx.post(
                    _URL_RECIBOS_EXPO, json={"ids": list(lote)}, timeout=_TIMEOUT_SEGUNDOS
                )
                resposta.raise_for_status()
                conteudo = resposta.json()
                recibos = conteudo.get("data") if isinstance(conteudo, dict) else None
                if not isinstance(recibos, dict) or conteudo.get("errors"):
                    raise ValueError("Resposta de recibos inválida.")
            except (httpx.HTTPError, ValueError):
                resultado["falhas"].extend(
                    {**ticket, "erro": "ConsultaNaoConfirmada"} for ticket in lote.values()
                )
                continue

            for ticket_id, ticket in lote.items():
                if ticket_id not in recibos:
                    resultado["pendentes"].append(ticket)
                    continue
                recibo = recibos[ticket_id]
                status = recibo.get("status") if isinstance(recibo, dict) else None
                if status == "ok":
                    resultado["confirmados"].append(ticket)
                    continue
                detalhes = recibo.get("details") if isinstance(recibo, dict) else None
                erro = detalhes.get("error") if isinstance(detalhes, dict) else None
                if status == "error" and erro == "DeviceNotRegistered":
                    try:
                        (
                            self.supabase.table("dispositivo_push").delete()
                            .eq("id", ticket["dispositivo_id"])
                            .eq("fk_usuario_id", ticket["usuario_id"]).execute()
                        )
                    except Exception:
                        resultado["falhas"].append({**ticket, "erro": "LimpezaNaoConfirmada"})
                    else:
                        resultado["invalidos"].append(ticket)
                else:
                    codigo = "ReciboInvalido"
                    if status == "error":
                        codigo = erro if isinstance(erro, str) and erro in _ERROS_RECIBO else (
                            "ReciboRecusado"
                        )
                    resultado["falhas"].append({**ticket, "erro": codigo})

        return resultado
