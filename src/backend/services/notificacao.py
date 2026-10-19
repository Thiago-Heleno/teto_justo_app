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
