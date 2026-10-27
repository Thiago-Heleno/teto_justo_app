from datetime import datetime, timezone

from fastapi import BackgroundTasks

from services.ciclo_vida_tarefa import ESTADOS_ABERTOS, ServicoCicloVidaTarefa, instante_utc
from services.notificacao import ServicoNotificacao


class ServicoPenalidade:
    TAMANHO_PAGINA = 500

    def __init__(self, supabase, tarefas_fundo: BackgroundTasks | None = None):
        self.supabase = supabase
        self.notificacoes = ServicoNotificacao(supabase, tarefas_fundo)
        self.ciclo_vida = ServicoCicloVidaTarefa(supabase, self.notificacoes)

    def _listar_tarefas_abertas(self) -> list[dict]:
        tarefas = []
        inicio = 0
        while True:
            pagina = (
                self.supabase.table("tarefa")
                .select("id,fk_casa_id,estado_atual,data_fim,atraso_maximo")
                .in_("estado_atual", ESTADOS_ABERTOS)
                .order("id")
                .range(inicio, inicio + self.TAMANHO_PAGINA - 1)
                .execute()
            ).data
            tarefas.extend(pagina)
            if len(pagina) < self.TAMANHO_PAGINA:
                return tarefas
            inicio += self.TAMANHO_PAGINA

    def processar_tarefas(self, agora: datetime | None = None) -> dict[str, int]:
        instante = instante_utc(agora or datetime.now(timezone.utc))
        tarefas = self._listar_tarefas_abertas()
        marcadas_atrasadas = 0
        marcadas_nao_feitas = 0

        for tarefa in tarefas:
            estado_anterior = tarefa["estado_atual"]
            atualizada = self.ciclo_vida.sincronizar_estado(tarefa, instante)
            if atualizada is None or atualizada["estado_atual"] == estado_anterior:
                continue
            estado_calculado = atualizada["estado_atual"]
            if estado_calculado == "atrasada":
                marcadas_atrasadas += 1
            elif estado_calculado == "nao_feito":
                marcadas_nao_feitas += 1

        return {
            "tarefas_analisadas": len(tarefas),
            "marcadas_atrasadas": marcadas_atrasadas,
            "marcadas_nao_feitas": marcadas_nao_feitas,
        }
