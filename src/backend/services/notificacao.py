from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from fastapi import HTTPException

from schemas.notificacao import DispositivoPushRegistrar


_URL_EXPO = "https://exp.host/--/api/v2/push/send"
_LIMITE_LOTE = 100
_TIMEOUT_SEGUNDOS = 10


class ServicoNotificacao:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

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

    def avisar_vencimentos(self, agora: datetime | None = None) -> dict[str, int]:
        instante = agora or datetime.now(timezone.utc)
        limite = instante + timedelta(hours=25)
        tarefas = []
        while True:
            pagina = (
                self.supabase.table("tarefa")
                .select("id,fk_casa_id,data_fim,estado_atual")
                .in_("estado_atual", ["pendente", "atrasada"])
                .is_("aviso_enviado_em", "null")
                .gt("data_fim", instante.isoformat())
                .lte("data_fim", limite.isoformat())
                .order("id")
                .range(len(tarefas), len(tarefas) + 99)
                .execute()
            ).data or []
            tarefas.extend(pagina)
            if len(pagina) < 100:
                break

        resultado = {"tarefas_elegiveis": len(tarefas), "avisos_enviados": 0, "falhas": 0}
        for tarefa in tarefas:
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
            envio = self.enviar_push(
                [UUID(item["fk_usuario_id"]) for item in atribuicoes],
                "Tarefa perto do vencimento",
                "Você tem uma tarefa com prazo próximo.",
                {"tarefa_id": tarefa["id"], "casa_id": tarefa["fk_casa_id"]},
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
                        {"dispositivo_id": dispositivo["id"], "ticket_id": ticket["id"]}
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
