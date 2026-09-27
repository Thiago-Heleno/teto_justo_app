from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException


class ServicoPlacar:
    TAMANHO_PAGINA = 1000

    def __init__(self, supabase):
        self.supabase = supabase

    def garantir_acesso(self, id_casa: UUID, id_usuario: UUID) -> None:
        casa = (
            self.supabase.table("casa")
            .select("fk_usuario_id")
            .eq("id", str(id_casa))
            .execute()
        ).data
        if not casa:
            raise HTTPException(status_code=404, detail="Casa não encontrada.")
        if str(casa[0]["fk_usuario_id"]) == str(id_usuario):
            return
        vinculo = (
            self.supabase.table("pertencer")
            .select("fk_usuario_id")
            .eq("fk_casa_id", str(id_casa))
            .eq("fk_usuario_id", str(id_usuario))
            .execute()
        ).data
        if not vinculo:
            raise HTTPException(status_code=403, detail="Acesso restrito aos moradores da casa.")

    @staticmethod
    def _instante_utc(valor: str | datetime) -> datetime:
        instante = datetime.fromisoformat(valor) if isinstance(valor, str) else valor
        if instante.tzinfo is None:
            return instante.replace(tzinfo=timezone.utc)
        return instante.astimezone(timezone.utc)

    @staticmethod
    def _meia_noite_utc(dia: date, fuso: ZoneInfo) -> datetime:
        return datetime.combine(dia, time.min, tzinfo=fuso).astimezone(timezone.utc)

    def _eventos_da_casa(self, id_casa: UUID):
        inicio = 0
        while True:
            pagina = (
                self.supabase.table("score_event")
                .select("id,fk_usuario_id,pontuacao,criado_em")
                .eq("fk_casa_id", str(id_casa))
                .order("id")
                .range(inicio, inicio + self.TAMANHO_PAGINA - 1)
                .execute()
            ).data
            yield from pagina
            if len(pagina) < self.TAMANHO_PAGINA:
                break
            inicio += self.TAMANHO_PAGINA

    def _dados(self, id_casa: UUID, agora: datetime):
        resposta_casa = (
            self.supabase.table("casa")
            .select("timezone")
            .eq("id", str(id_casa))
            .execute()
        )
        if not resposta_casa.data:
            raise HTTPException(status_code=404, detail="Casa não encontrada.")

        nome_fuso = resposta_casa.data[0].get("timezone") or "America/Sao_Paulo"
        try:
            fuso = ZoneInfo(nome_fuso)
        except (ValueError, KeyError) as erro:
            raise HTTPException(status_code=500, detail="Fuso horário da casa inválido.") from erro

        vinculos = (
            self.supabase.table("pertencer")
            .select("fk_usuario_id,score")
            .eq("fk_casa_id", str(id_casa))
            .execute()
        ).data
        ids = [str(vinculo["fk_usuario_id"]) for vinculo in vinculos]
        usuarios = []
        if ids:
            usuarios = (
                self.supabase.table("usuario")
                .select("id,nome")
                .in_("id", ids)
                .execute()
            ).data
        nomes = {str(usuario["id"]): usuario["nome"] for usuario in usuarios}

        agora_utc = self._instante_utc(agora)
        hoje = agora_utc.astimezone(fuso).date()
        primeiro_dia_semana = hoje - timedelta(days=(hoje.weekday() + 1) % 7)
        primeiro_dia_mes = hoje.replace(day=1)
        primeiro_dia_ano = hoje.replace(month=1, day=1)
        limites = {
            "semanal": self._meia_noite_utc(primeiro_dia_semana, fuso),
            "mensal": self._meia_noite_utc(primeiro_dia_mes, fuso),
            "anual": self._meia_noite_utc(primeiro_dia_ano, fuso),
        }

        totais = {
            id_usuario: {"semanal": 0, "mensal": 0, "anual": 0, "acumulado": 0}
            for id_usuario in ids
        }
        eventos_sem_vinculo = {}
        for evento in self._eventos_da_casa(id_casa):
            id_usuario = str(evento["fk_usuario_id"])
            pontos = int(evento["pontuacao"])
            if id_usuario not in totais:
                eventos_sem_vinculo[id_usuario] = (
                    eventos_sem_vinculo.get(id_usuario, 0) + pontos
                )
                continue
            totais[id_usuario]["acumulado"] += pontos
            if evento["criado_em"] is None:
                raise HTTPException(status_code=500, detail="Evento de score sem data.")
            instante = self._instante_utc(evento["criado_em"])
            if instante <= agora_utc:
                for periodo, inicio in limites.items():
                    if instante >= inicio:
                        totais[id_usuario][periodo] += pontos

        moradores = [
            {"usuario_id": id_usuario, "nome": nomes[id_usuario], **totais[id_usuario]}
            for id_usuario in ids
        ]
        moradores.sort(key=lambda morador: (morador["nome"].casefold(), morador["usuario_id"]))
        saldos = {str(vinculo["fk_usuario_id"]): vinculo["score"] for vinculo in vinculos}
        return nome_fuso, moradores, saldos, eventos_sem_vinculo

    def obter_placar(self, id_casa: UUID, agora: datetime | None = None) -> dict:
        nome_fuso, moradores, _, _ = self._dados(
            id_casa, agora or datetime.now(timezone.utc)
        )
        return {
            "casa_id": str(id_casa),
            "fuso_horario": nome_fuso,
            "moradores": moradores,
        }

    def auditar_saldos(self, id_casa: UUID) -> list[dict]:
        _, moradores, saldos, eventos_sem_vinculo = self._dados(
            id_casa, datetime.now(timezone.utc)
        )
        divergencias = [
            {
                "usuario_id": morador["usuario_id"],
                "saldo_materializado": saldos[morador["usuario_id"]],
                "acumulado_eventos": morador["acumulado"],
                "diferenca": (saldos[morador["usuario_id"]] or 0) - morador["acumulado"],
            }
            for morador in moradores
            if (saldos[morador["usuario_id"]] or 0) != morador["acumulado"]
        ]
        divergencias.extend(
            {
                "usuario_id": id_usuario,
                "saldo_materializado": None,
                "acumulado_eventos": pontos,
                "diferenca": None,
            }
            for id_usuario, pontos in sorted(eventos_sem_vinculo.items())
        )
        return divergencias
