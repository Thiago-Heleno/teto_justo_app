from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException
from postgrest.exceptions import APIError

from services.autorizacao import ServicoAutorizacaoCasa
from services.ciclo_vida_tarefa import instante_utc
from services.tarefa import ServicoTarefa


class ServicoReclamacao:
    def __init__(self, cliente_supabase, tarefas_fundo: BackgroundTasks | None = None):
        self.supabase = cliente_supabase
        self.tarefas = ServicoTarefa(cliente_supabase, tarefas_fundo)

    def reclamar_tarefa(
        self, id_tarefa: UUID, id_usuario: UUID, conclusao_esperada: datetime | None = None
    ) -> dict:
        tarefa = self.tarefas._buscar_tarefa_bruta(id_tarefa)
        id_casa = str(tarefa["fk_casa_id"])
        casas = (
            self.supabase.table("casa").select("politica_reclamacao").eq("id", id_casa).execute()
        ).data
        if not casas:
            raise HTTPException(status_code=404, detail="Casa não encontrada.")

        moradores = ServicoAutorizacaoCasa(self.supabase).registros_por_ids(
            "pertencer",
            "fk_casa_id",
            [id_casa],
            "fk_usuario_id",
            ("fk_usuario_id",),
            ativo=True,
        )
        ids_moradores = {str(morador["fk_usuario_id"]) for morador in moradores}
        if str(id_usuario) not in ids_moradores:
            raise HTTPException(status_code=403, detail="Apenas moradores ativos podem reclamar.")
        responsaveis = self.tarefas._buscar_usuarios_atribuidos(id_tarefa)
        if str(id_usuario) in responsaveis:
            raise HTTPException(
                status_code=403,
                detail="O responsável pela tarefa não pode reclamar dela.",
            )
        if tarefa["estado_atual"] != "finalizado":
            raise HTTPException(
                status_code=409,
                detail="Só é possível reclamar de uma tarefa finalizada.",
            )
        agora = datetime.now(timezone.utc)
        concluida_em = tarefa.get("concluida_em")
        if not concluida_em or not (
            timedelta(0) <= agora - instante_utc(concluida_em) <= timedelta(hours=24)
        ):
            raise HTTPException(
                status_code=409,
                detail="A reclamação deve ser feita até 24h após a conclusão.",
            )
        if conclusao_esperada and instante_utc(conclusao_esperada) != instante_utc(concluida_em):
            raise HTTPException(
                status_code=409, detail="A conclusão da tarefa mudou. Atualize para continuar."
            )
        politica = casas[0]["politica_reclamacao"]
        if politica == "nenhuma":
            raise HTTPException(status_code=409, detail="Esta casa não permite reclamações.")

        ciclo = tarefa.get("reaberturas") or 0
        try:
            self.supabase.table("reclamacao_tarefa").insert(
                {
                    "fk_tarefa_id": str(id_tarefa),
                    "fk_usuario_id": str(id_usuario),
                    "ciclo": ciclo,
                }
            ).execute()
        except APIError as erro:
            if erro.code != "23505":
                raise
            raise HTTPException(
                status_code=409,
                detail="Você já reclamou desta tarefa neste ciclo.",
            ) from erro

        limite = self.tarefas._limite_reclamacoes(ids_moradores, responsaveis)
        reclamacoes = (
            self.supabase.table("reclamacao_tarefa")
            .select("fk_usuario_id", count="exact")
            .eq("fk_tarefa_id", str(id_tarefa))
            .eq("ciclo", ciclo)
            .execute()
        )
        reabrir = politica == "votacao" and (reclamacoes.count or 0) >= limite
        if reabrir:
            tarefa = self.tarefas.ciclo_vida.reabrir(tarefa, responsaveis, agora)
        resultado = self.tarefas._montar_resposta(tarefa, agora)
        if reabrir:
            tipo_aviso = "tarefa_reaberta"
        elif politica == "uma_reclamacao":
            tipo_aviso = "tarefa_reclamada"
        else:
            tipo_aviso = None
        if tipo_aviso:
            self.tarefas.notificacoes.notificar_tarefa(tipo_aviso, resultado, responsaveis)
        return resultado
