from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from postgrest.exceptions import APIError

from services.ciclo_vida_tarefa import instante_utc
from services.notificacao import ServicoNotificacao

JANELA_ROLETA = timedelta(hours=24)


def resumir_roleta(tarefa: dict, agora: datetime) -> dict | None:
    if tarefa.get("roleta_expira_em") is None:
        return None
    expira_em = instante_utc(tarefa["roleta_expira_em"])
    abre_em = expira_em - JANELA_ROLETA
    atribuida_em = tarefa.get("roleta_atribuida_em")
    if atribuida_em:
        estado = "atribuida"
    elif tarefa.get("roleta_responsavel_id"):
        estado = "atribuindo"
    elif agora < abre_em:
        estado = "agendada"
    elif agora < expira_em:
        estado = "aberta"
    else:
        estado = "expirada"
    return {
        "abre_em": abre_em,
        "expira_em": expira_em,
        "estado": estado,
        "atribuida_em": atribuida_em,
        "responsavel_id": tarefa["roleta_responsavel_id"] if atribuida_em else None,
        "origem": tarefa["roleta_origem"] if atribuida_em else None,
    }


class ServicoRoletaRotatividade:
    def __init__(self, supabase, tarefas_fundo=None):
        self.supabase = supabase
        self.notificacoes = ServicoNotificacao(supabase, tarefas_fundo)

    def buscar_tarefa(self, id_tarefa: str) -> dict:
        registros = self.supabase.table("tarefa").select("*").eq("id", id_tarefa).execute().data
        if not registros:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        return registros[0]

    def decidir(self, tarefa: dict, responsavel: str, origem: str, agora: datetime) -> dict:
        id_tarefa = str(tarefa["id"])
        instante = agora.isoformat()
        consulta = (
            self.supabase.table("tarefa")
            .update(
                {
                    "roleta_responsavel_id": responsavel,
                    "roleta_decidida_em": instante,
                    "roleta_origem": origem,
                }
            )
            .eq("id", id_tarefa)
            .eq("estado_atual", "pendente")
            .is_("roleta_responsavel_id", "null")
        )
        if origem == "giro":
            consulta = consulta.gt("roleta_expira_em", instante).lte(
                "roleta_expira_em", (agora + JANELA_ROLETA).isoformat()
            )
        else:
            consulta = consulta.lte("roleta_expira_em", instante)
        try:
            atualizadas = consulta.execute().data
        except APIError as erro:
            if erro.code == "23503":
                raise HTTPException(
                    status_code=409, detail="O vínculo do participante mudou. Tente novamente."
                ) from erro
            raise
        atual = atualizadas[0] if atualizadas else self.buscar_tarefa(id_tarefa)
        if not atual.get("roleta_responsavel_id"):
            raise HTTPException(
                status_code=409, detail="A roleta não está disponível para esta ação."
            )
        return atual

    def atribuir(self, tarefa: dict) -> dict:
        if tarefa.get("roleta_atribuida_em"):
            return tarefa
        id_tarefa = str(tarefa["id"])
        responsavel = str(tarefa["roleta_responsavel_id"])
        self.supabase.table("atribuida").upsert(
            {"fk_tarefa_id": id_tarefa, "fk_usuario_id": responsavel},
            on_conflict="fk_usuario_id,fk_tarefa_id",
            ignore_duplicates=True,
        ).execute()
        agora = max(datetime.now(timezone.utc), instante_utc(tarefa["roleta_decidida_em"]))
        vencimento = max(instante_utc(tarefa["data_fim"]), agora + JANELA_ROLETA)
        atualizadas = (
            self.supabase.table("tarefa")
            .update({"roleta_atribuida_em": agora.isoformat(), "data_fim": vencimento.isoformat()})
            .eq("id", id_tarefa)
            .eq("roleta_responsavel_id", responsavel)
            .is_("roleta_atribuida_em", "null")
            .execute()
        ).data
        if not atualizadas:
            return self.buscar_tarefa(id_tarefa)
        atual = atualizadas[0]
        self.notificacoes.notificar_tarefa("tarefa_atribuida", atual, [responsavel])
        return atual
