from datetime import datetime, timezone

from services.score import ServicoScore


class ServicoPenalidade:
    TAMANHO_PAGINA = 500
    ESTADOS_ABERTOS = ("pendente", "atrasada")

    def __init__(self, supabase):
        self.supabase = supabase

    @staticmethod
    def _instante_utc(valor: str | datetime) -> datetime:
        instante = datetime.fromisoformat(valor) if isinstance(valor, str) else valor
        if instante.tzinfo is None or instante.utcoffset() is None:
            return instante.replace(tzinfo=timezone.utc)
        return instante.astimezone(timezone.utc)

    def _listar_tarefas_abertas(self) -> list[dict]:
        tarefas = []
        inicio = 0
        while True:
            pagina = (
                self.supabase.table("tarefa")
                .select("id,estado_atual,data_fim,atraso_maximo")
                .in_("estado_atual", self.ESTADOS_ABERTOS)
                .order("id")
                .range(inicio, inicio + self.TAMANHO_PAGINA - 1)
                .execute()
            ).data
            tarefas.extend(pagina)
            if len(pagina) < self.TAMANHO_PAGINA:
                return tarefas
            inicio += self.TAMANHO_PAGINA

    def _estado_calculado(self, tarefa: dict, agora: datetime) -> str:
        data_fim = self._instante_utc(tarefa["data_fim"])
        dias_atraso = ServicoScore.calcular_dias_atraso(data_fim, agora)
        if dias_atraso == 0:
            return "pendente"
        if dias_atraso > tarefa["atraso_maximo"]:
            return "nao_feito"
        return "atrasada"

    def _atualizar_estado(self, tarefa: dict, estado: str) -> bool:
        resposta = (
            self.supabase.table("tarefa")
            .update({"estado_atual": estado})
            .eq("id", str(tarefa["id"]))
            .eq("estado_atual", tarefa["estado_atual"])
            .eq("data_fim", tarefa["data_fim"])
            .eq("atraso_maximo", tarefa["atraso_maximo"])
            .execute()
        )
        return bool(resposta.data)

    def processar_tarefas(self, agora: datetime | None = None) -> dict[str, int]:
        instante = self._instante_utc(agora or datetime.now(timezone.utc))
        tarefas = self._listar_tarefas_abertas()
        marcadas_atrasadas = 0
        marcadas_nao_feitas = 0

        for tarefa in tarefas:
            estado_calculado = self._estado_calculado(tarefa, instante)
            if estado_calculado == tarefa["estado_atual"]:
                continue
            if not self._atualizar_estado(tarefa, estado_calculado):
                continue
            if estado_calculado == "atrasada":
                marcadas_atrasadas += 1
            elif estado_calculado == "nao_feito":
                marcadas_nao_feitas += 1

        return {
            "tarefas_analisadas": len(tarefas),
            "marcadas_atrasadas": marcadas_atrasadas,
            "marcadas_nao_feitas": marcadas_nao_feitas,
        }
