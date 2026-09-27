from datetime import date, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


EstadoTarefa = Literal["pendente", "atrasada", "finalizado", "nao_feito"]
PesoTarefa = Annotated[int, Field(strict=True, ge=1, le=3)]
PrazoDias = Annotated[int, Field(strict=True, ge=1, le=5)]
AtrasoMaximo = Annotated[int, Field(strict=True, ge=1, le=5)]
AtrasoMaximoLegado = Annotated[int, Field(strict=True, gt=0)]
ReferenciaInicio = Literal["criacao", "ocorrencia"]
EstrategiaPenalidade = Literal["proporcional"]
TipoTarefa = Literal["unitaria", "rotativa"]
ModoPrazo = Literal["dia_fixo", "intervalo"]


class TarefaCriar(BaseModel):
    nome: str = Field(min_length=1)
    descricao: str | None = None
    estado_atual: Literal["pendente"] = "pendente"
    peso: PesoTarefa
    prazo_dias: PrazoDias
    atraso_maximo: AtrasoMaximo
    estrategia_penalidade: EstrategiaPenalidade = "proporcional"
    tipo: Literal["unitaria"] = "unitaria"
    modo_prazo: ModoPrazo = "intervalo"
    data_fixa: date | None = None
    fk_casa_id: UUID
    usuarios_atribuidos: list[UUID] = Field(min_length=1, max_length=1)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def validar_modo_prazo(self):
        if self.modo_prazo == "dia_fixo" and self.data_fixa is None:
            raise ValueError("Informe data_fixa para a tarefa de dia fixo.")
        if self.modo_prazo == "intervalo" and self.data_fixa is not None:
            raise ValueError("data_fixa só é permitida no modo dia_fixo.")
        return self


class TarefaAtualizar(BaseModel):
    nome: str | None = Field(default=None, min_length=1)
    descricao: str | None = None
    estado_atual: EstadoTarefa | None = None
    peso: PesoTarefa | None = None
    prazo_dias: PrazoDias | None = None
    atraso_maximo: AtrasoMaximo | None = None
    data_fixa: date | None = None
    usuarios_atribuidos: list[UUID] | None = Field(default=None, min_length=1, max_length=1)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @model_validator(mode="after")
    def rejeitar_nulos(self):
        for campo in self.model_fields_set - {"descricao"}:
            if getattr(self, campo) is None:
                raise ValueError(f"{campo} não pode ser nulo.")
        return self


class TarefaResposta(BaseModel):
    id: UUID
    nome: str
    descricao: str | None = None
    estado_atual: EstadoTarefa
    peso: PesoTarefa
    pontuacao: int = Field(ge=0, description="Pontos-base calculados pela dificuldade.")
    estrategia_penalidade: EstrategiaPenalidade = "proporcional"
    tipo: TipoTarefa = "unitaria"
    modo_prazo: ModoPrazo = "intervalo"
    data_fixa: date | None = None
    rotatividade_id: UUID | None = None
    ocorrencia_em: datetime | None = None
    concluida_em: datetime | None = None
    resultado_pontuacao: "ResultadoPontuacao | None" = None
    atraso_maximo: AtrasoMaximoLegado
    referencia_inicio: ReferenciaInicio
    # Registros legados podem não ter a duração e o início cadastrados.
    prazo_dias: PrazoDias | None
    data_inicio: datetime | None
    proxima_ocorrencia: datetime | None
    data_fim: datetime
    fk_casa_id: UUID
    usuarios_atribuidos: list[UUID] = Field(default_factory=list)
    fk_usuario_id: UUID


class ResultadoPontuacao(BaseModel):
    pontos_possiveis: int = Field(ge=0)
    pontos_ganhos: int = Field(ge=0)
    saldo_atual: int
