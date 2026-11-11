from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from schemas.casa import PoliticaReclamacao


class FiltroPeriodoScore(BaseModel):
    data_inicio: date | None = Field(
        default=None, description="Primeiro dia incluído, no fuso horário da casa."
    )
    data_fim: date | None = Field(
        default=None, description="Primeiro dia excluído, no fuso horário da casa."
    )

    @model_validator(mode="after")
    def validar_periodo(self):
        if self.data_inicio and self.data_fim and self.data_inicio >= self.data_fim:
            raise ValueError("data_fim deve ser posterior a data_inicio.")
        return self


class FiltroExtratoScore(FiltroPeriodoScore):
    fk_usuario_id: UUID | None = None
    inicio: int = Field(default=0, ge=0)
    limite: int = Field(default=100, ge=1, le=100)


class SaldoScoreResposta(BaseModel):
    fk_casa_id: UUID
    fk_usuario_id: UUID
    saldo_atual: int


class ScoreEventResposta(BaseModel):
    id: UUID
    fk_casa_id: UUID
    fk_usuario_id: UUID
    fk_tarefa_id: UUID
    nome_tarefa: str | None = None
    reclamacoes_count: int = Field(default=0, ge=0)
    concluida_em: datetime | None = Field(
        default=None, description="Instante da conclusão vigente, apenas no crédito correspondente."
    )
    pontuacao: int
    tipo: Literal["credito", "reversal"]
    criado_em: datetime


class ExtratoScoreResposta(BaseModel):
    casa_id: UUID
    fuso_horario: str
    politica_reclamacao: PoliticaReclamacao
    fk_usuario_id: UUID | None
    data_inicio: date | None
    data_fim: date | None
    inicio: int
    limite: int
    total: int
    eventos: list[ScoreEventResposta]


class MoradorRankingResposta(BaseModel):
    posicao: int
    usuario_id: UUID
    nome: str
    pontos: int


class RankingScoreResposta(BaseModel):
    casa_id: UUID
    fuso_horario: str
    data_inicio: date | None
    data_fim: date | None
    moradores: list[MoradorRankingResposta]
