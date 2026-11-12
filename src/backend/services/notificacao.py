from datetime import datetime, timedelta, timezone
import logging
import os
from urllib.parse import quote
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
import firebase_admin
from fastapi import BackgroundTasks, HTTPException
from firebase_admin import credentials, messaging
from firebase_admin.exceptions import FirebaseError
from postgrest.exceptions import APIError

from core.fuso import FUSO_UTC, fuso_armazenado
from schemas.notificacao import DispositivoPushRegistrar, TicketPush
from services.ciclo_vida_tarefa import instante_utc
from services.score import ServicoScore


_URL_EXPO = "https://exp.host/--/api/v2/push/send"
_URL_RECIBOS_EXPO = "https://exp.host/--/api/v2/push/getReceipts"
_LIMITE_LOTE = 100
_LIMITE_LOTE_RECIBOS = 1000
_TIMEOUT_SEGUNDOS = 10
_FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
_LOGGER = logging.getLogger(__name__)
_ERROS_RECIBO = {
    "MessageTooBig",
    "MessageRateExceeded",
    "MismatchSenderId",
    "InvalidCredentials",
}
_MENSAGENS_TAREFA = {
    "tarefa_atribuida": ("Nova tarefa para você", "Uma tarefa foi atribuída a você."),
    "prazo_alterado": ("Prazo da tarefa alterado", "O prazo de uma tarefa sua foi atualizado."),
    "atribuicao_removida": (
        "Responsável pela tarefa alterado",
        "Você deixou de ser responsável por uma tarefa.",
    ),
    "prazo_encerrado": (
        "Prazo de execução encerrado",
        "O prazo para concluir uma tarefa sua foi encerrado.",
    ),
    "tarefa_reclamada": (
        "Sua tarefa recebeu uma reclamação",
        "Uma tarefa sua recebeu uma reclamação.",
    ),
    "tarefa_reaberta": (
        "Sua tarefa foi reaberta",
        "Uma tarefa sua foi reaberta e precisa de atenção.",
    ),
}


def _firebase_app():
    if not _FIREBASE_SERVICE_ACCOUNT:
        return None
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass
    try:
        import json

        return firebase_admin.initialize_app(
            credentials.Certificate(json.loads(_FIREBASE_SERVICE_ACCOUNT))
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        _LOGGER.warning("Não foi possível configurar o Firebase Admin.")
        return None


def _link_web(dados: dict | None) -> str | None:
    # O FCM só abre a página ao tocar na notificação quando recebe um link HTTPS.
    base = os.getenv("WEB_APP_URL", "").rstrip("/")
    if not base.startswith("https://"):
        return None
    tarefa_id = (dados or {}).get("tarefa_id")
    return f"{base}/tarefas" + (f"?abrir={quote(str(tarefa_id))}" if tarefa_id else "")


class _ConsultaDispositivosFalhou(RuntimeError):
    pass


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
                    self.supabase.table("tarefa")
                    .select("id,fk_casa_id")
                    .eq("id", str(tarefa["id"]))
                    .execute()
                ).data or []
                if not registros:
                    return
                tarefa = registros[0]
            if ids_usuarios is None:
                ids_usuarios = self._responsaveis(tarefa["id"])
            titulo, mensagem = _MENSAGENS_TAREFA[tipo]
            self._enviar_aviso_normal(
                ids_usuarios,
                titulo,
                mensagem,
                {
                    "tipo": tipo,
                    "tarefa_id": str(tarefa["id"]),
                    "casa_id": str(tarefa["fk_casa_id"]),
                },
            )
        except Exception:
            # A notificação é secundária; não propaga erros nem detalhes que contenham tokens.
            _LOGGER.warning("Não foi possível preparar uma notificação normal.")

    def _responsaveis(self, id_tarefa: str) -> list[str]:
        registros = (
            self.supabase.table("atribuida")
            .select("fk_usuario_id")
            .eq("fk_tarefa_id", str(id_tarefa))
            .execute()
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
                self.supabase.table("tarefa")
                .update({"aviso_inicio_tentado_em": None})
                .eq("id", str(tarefa["id"]))
                .eq("data_inicio", tarefa["data_inicio"])
                .eq("estado_atual", "pendente")
                .execute()
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
                .order("id")
                .range(len(tarefas), len(tarefas) + 99)
                .execute()
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
                .eq("id", tarefa["id"])
                .eq("data_inicio", tarefa["data_inicio"])
                .eq("estado_atual", "pendente")
                .is_("aviso_inicio_tentado_em", "null")
                .execute()
            )
            if not reserva.data:
                continue
            if tarefa.get("rotatividade_id"):
                for usuario in usuarios:
                    chave = (usuario, str(tarefa["fk_casa_id"]))
                    resumos[chave] = resumos.get(chave, 0) + 1
                continue
            envio = self._enviar_aviso_normal(
                usuarios,
                "Sua tarefa começa em breve",
                "Uma tarefa sua começa nas próximas 24 horas.",
                {
                    "tipo": "inicio_tarefa",
                    "tarefa_id": tarefa["id"],
                    "casa_id": tarefa["fk_casa_id"],
                },
            )
            resultado["avisos_enviados"] += len(envio["aceitos"])
            resultado["falhas"] += len(envio["falhas"])

        for (usuario, casa), quantidade in resumos.items():
            mensagem = (
                "Você tem uma tarefa do rodízio começando nas próximas 24 horas."
                if quantidade == 1
                else f"Você tem {quantidade} tarefas do rodízio começando nas próximas 24 horas."
            )
            envio = self._enviar_aviso_normal(
                [usuario],
                "Novas tarefas do rodízio",
                mensagem,
                {"tipo": "rodizio_distribuido", "casa_id": casa},
            )
            resultado["avisos_enviados"] += len(envio["aceitos"])
            resultado["falhas"] += len(envio["falhas"])
        return resultado

    def registrar_dispositivo(self, id_usuario: UUID, dados: DispositivoPushRegistrar) -> dict:
        resposta = (
            self.supabase.table("dispositivo_push")
            .upsert(
                {
                    "fk_usuario_id": str(id_usuario),
                    **dados.model_dump(exclude_none=True),
                },
                on_conflict="token",
            )
            .execute()
        )
        if not resposta.data:
            raise HTTPException(status_code=503, detail="Não foi possível registrar o dispositivo.")
        return resposta.data[0]

    def remover_dispositivo(self, id_usuario: UUID | str, token: str) -> None:
        (
            self.supabase.table("dispositivo_push")
            .delete()
            .eq("fk_usuario_id", str(id_usuario))
            .eq("token", token)
            .execute()
        )

    def _fuso_da_casa(self, id_casa: str) -> ZoneInfo:
        resposta = (
            self.supabase.table("casa")
            .select("timezone")
            .eq("id", id_casa)
            .execute()
        )
        nome_fuso = (resposta.data or [{}])[0].get("timezone")
        return fuso_armazenado(nome_fuso) or FUSO_UTC

    def _processar_aviso_vencimento(
        self,
        tarefa: dict,
        coluna: str,
        marca: str,
        tipo: str,
        titulo: str,
        mensagem: str,
        resultado: dict[str, int],
    ) -> None:
        try:
            usuarios = [UUID(usuario) for usuario in self._responsaveis(tarefa["id"])]
            if not usuarios:
                return

            reserva = (
                self.supabase.table("tarefa")
                .update({coluna: marca})
                .eq("id", tarefa["id"])
                .eq("data_fim", tarefa["data_fim"])
                .in_("estado_atual", ["pendente", "atrasada"])
                .is_(coluna, "null")
                .execute()
            )
            if not reserva.data:
                return
        except (APIError, httpx.RequestError):
            _LOGGER.warning("Não foi possível preparar o aviso de vencimento da tarefa.")
            resultado["falhas"] += 1
            return

        resultado["tarefas_elegiveis"] += 1
        try:
            envio = self.enviar_push(
                usuarios,
                titulo,
                mensagem,
                {"tipo": tipo, "tarefa_id": tarefa["id"], "casa_id": tarefa["fk_casa_id"]},
            )
        except _ConsultaDispositivosFalhou:
            _LOGGER.warning("Não foi possível consultar os dispositivos para o aviso da tarefa.")
            resultado["falhas"] += 1
            try:
                (
                    self.supabase.table("tarefa")
                    .update({coluna: None})
                    .eq("id", tarefa["id"])
                    .eq("data_fim", tarefa["data_fim"])
                    .eq(coluna, marca)
                    .execute()
                )
            except (APIError, httpx.RequestError):
                _LOGGER.warning("Não foi possível liberar a reserva do aviso de vencimento.")
        except Exception:
            _LOGGER.warning("Não foi possível concluir o envio do aviso de vencimento.")
            resultado["falhas"] += 1
        else:
            resultado["avisos_enviados"] += len(envio["aceitos"])
            resultado["falhas"] += len(envio["falhas"])

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
                    "id,fk_casa_id,data_inicio,data_fim,estado_atual,atraso_maximo,aviso_enviado_em"
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
                .select("id,fk_casa_id,data_fim,estado_atual,atraso_maximo,aviso_atraso_enviado_em")
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
            data_fim = instante_utc(tarefa["data_fim"])
            try:
                fuso = self._fuso_da_casa(tarefa["fk_casa_id"])
            except (APIError, httpx.RequestError):
                _LOGGER.warning("Não foi possível consultar o fuso para o aviso de vencimento.")
                resultado["falhas"] += 1
                continue
            hoje_local = instante.astimezone(fuso).date()
            if data_fim.astimezone(fuso).date() != hoje_local:
                continue
            data_inicio = tarefa.get("data_inicio")
            if data_inicio and instante_utc(data_inicio) > instante:
                continue

            self._processar_aviso_vencimento(
                tarefa,
                "aviso_enviado_em",
                instante.isoformat(),
                "tarefa_vence_hoje",
                "Sua tarefa vence hoje",
                "A tarefa vence hoje e já pode ser concluída.",
                resultado,
            )

        for tarefa in tarefas_atrasadas:
            data_fim = instante_utc(tarefa["data_fim"])
            dias_atraso = ServicoScore.calcular_dias_atraso(data_fim, instante)
            if dias_atraso <= 0 or dias_atraso > tarefa["atraso_maximo"]:
                continue

            self._processar_aviso_vencimento(
                tarefa,
                "aviso_atraso_enviado_em",
                instante.isoformat(),
                "tarefa_atrasada",
                "Sua tarefa está atrasada",
                "A tarefa está atrasada, mas ainda pode ser concluída.",
                resultado,
            )
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
            try:
                pagina = (
                    self.supabase.table("dispositivo_push")
                    .select("id,token,fk_usuario_id,plataforma")
                    .in_("fk_usuario_id", ids)
                    .order("id")
                    .range(len(dispositivos), len(dispositivos) + _LIMITE_LOTE - 1)
                    .execute()
                ).data or []
            except (APIError, httpx.RequestError) as erro:
                raise _ConsultaDispositivosFalhou from erro
            dispositivos.extend(pagina)
            if len(pagina) < _LIMITE_LOTE:
                break

        # Carrega todas as páginas antes das exclusões para não deslocar os offsets.
        for inicio in range(0, len(dispositivos), _LIMITE_LOTE):
            lote = dispositivos[inicio : inicio + _LIMITE_LOTE]
            expo_lote = [d for d in lote if d.get("plataforma") != "web"]
            web_lote = [d for d in lote if d.get("plataforma") == "web"]
            if expo_lote:
                mensagens = [
                    {
                        "to": dispositivo["token"],
                        "title": titulo,
                        "body": mensagem,
                        **(
                            {"categoryId": "tarefa_pendente"}
                            if dados
                            and dados.get("tipo") in {"tarefa_vence_hoje", "tarefa_atrasada"}
                            else {}
                        ),
                        **({"data": dados} if dados is not None else {}),
                    }
                    for dispositivo in expo_lote
                ]
                self._enviar_lote_expo(expo_lote, mensagens, resultado)
            for dispositivo in web_lote:
                self._enviar_fcm(dispositivo, titulo, mensagem, dados, resultado)
        return resultado

    def _enviar_lote_expo(self, lote: list[dict], mensagens: list[dict], resultado: dict) -> None:
        try:
            resposta = httpx.post(_URL_EXPO, json=mensagens, timeout=_TIMEOUT_SEGUNDOS)
            resposta.raise_for_status()
            conteudo = resposta.json()
            tickets = conteudo.get("data") if isinstance(conteudo, dict) else None
            if not isinstance(tickets, list) or len(tickets) != len(lote) or conteudo.get("errors"):
                raise ValueError("Resposta de push inválida.")
        except (httpx.HTTPError, ValueError):
            resultado["falhas"].extend(
                {"dispositivo_id": d["id"], "erro": "EnvioNaoConfirmado"} for d in lote
            )
            return

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
                self.remover_dispositivo(dispositivo["fk_usuario_id"], dispositivo["token"])
                resultado["invalidos"].append(dispositivo["id"])
            else:
                resultado["falhas"].append(
                    {
                        "dispositivo_id": dispositivo["id"],
                        "erro": "EnvioRecusado" if status == "error" else "EnvioNaoConfirmado",
                    }
                )

    def _enviar_fcm(
        self, dispositivo: dict, titulo: str, mensagem: str, dados: dict | None, resultado: dict
    ) -> None:
        if _firebase_app() is None:
            resultado["falhas"].append(
                {"dispositivo_id": dispositivo["id"], "erro": "FirebaseNaoConfigurado"}
            )
            return
        try:
            mensagem_fcm = messaging.Message(
                token=dispositivo["token"],
                notification=messaging.Notification(title=titulo, body=mensagem),
                data={str(chave): str(valor) for chave, valor in (dados or {}).items()},
                webpush=messaging.WebpushConfig(
                    fcm_options=messaging.WebpushFCMOptions(link=_link_web(dados))
                ),
            )
            messaging.send(mensagem_fcm)
        except messaging.UnregisteredError:
            self.remover_dispositivo(dispositivo["fk_usuario_id"], dispositivo["token"])
            resultado["invalidos"].append(dispositivo["id"])
        except (FirebaseError, ValueError, TypeError):
            resultado["falhas"].append(
                {"dispositivo_id": dispositivo["id"], "erro": "EnvioNaoConfirmado"}
            )
        else:
            resultado["aceitos"].append(
                {
                    "dispositivo_id": dispositivo["id"],
                    "usuario_id": dispositivo["fk_usuario_id"],
                },
            )

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
                            self.supabase.table("dispositivo_push")
                            .delete()
                            .eq("id", ticket["dispositivo_id"])
                            .eq("fk_usuario_id", ticket["usuario_id"])
                            .execute()
                        )
                    except Exception:
                        resultado["falhas"].append({**ticket, "erro": "LimpezaNaoConfirmada"})
                    else:
                        resultado["invalidos"].append(ticket)
                else:
                    codigo = "ReciboInvalido"
                    if status == "error":
                        codigo = (
                            erro
                            if isinstance(erro, str) and erro in _ERROS_RECIBO
                            else ("ReciboRecusado")
                        )
                    resultado["falhas"].append({**ticket, "erro": codigo})

        return resultado
