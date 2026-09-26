from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


EstadoTarefa = Literal["pendente", "atrasada", "finalizado", "nao_feito"]
PesoTarefa = Annotated[int, Field(strict=True, ge=1, le=3)]
PrazoDias = Annotated[int, Field(strict=True, ge=1, le=5)]
AtrasoMaximo = Annotated[int, Field(strict=True, gt=0)]
ReferenciaInicio = Literal["criacao", "ocorrencia"]
EstrategiaPenalidade = Literal["proporcional"]


class TarefaCriar(BaseModel):
    nome: str = Field(min_length=1)
    descricao: str | None = None
    estado_atual: Literal["pendente"] = "pendente"
    peso: PesoTarefa
    prazo_dias: PrazoDias
    atraso_maximo: AtrasoMaximo
    estrategia_penalidade: EstrategiaPenalidade = "proporcional"
    referencia_inicio: ReferenciaInicio = "criacao"
    data_inicio: AwareDatetime | None = None
    proxima_ocorrencia: AwareDatetime | None = None
    fk_casa_id: UUID
    usuarios_atribuidos: list[UUID] = Field(min_length=1, max_length=1)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("data_inicio", "proxima_ocorrencia")
    @classmethod
    def normalizar_data(cls, valor: datetime | None) -> datetime | None:
        return valor.astimezone(timezone.utc) if valor is not None else None

    @model_validator(mode="after")
    def validar_referencia_inicio(self):
        if self.referencia_inicio == "criacao":
            if self.data_inicio is not None or self.proxima_ocorrencia is not None:
                raise ValueError("Na tarefa unitária, o servidor define o início na criação.")
        else:
            if self.data_inicio is None or self.proxima_ocorrencia is None:
                raise ValueError("Informe o início desta ocorrência e o início da próxima.")
            if self.data_inicio < datetime.now(timezone.utc):
                raise ValueError("O início da ocorrência não pode estar no passado.")
            janela = (self.proxima_ocorrencia - self.data_inicio).total_seconds()
            if (self.prazo_dias + self.atraso_maximo) * 86400 >= janela:
                raise ValueError(
                    "O prazo e a tolerância devem terminar antes da próxima ocorrência."
                )
        return self


class TarefaAtualizar(BaseModel):
    nome: str | None = Field(default=None, min_length=1)
    descricao: str | None = None
    estado_atual: EstadoTarefa | None = None
    peso: PesoTarefa | None = None
    prazo_dias: PrazoDias | None = None
    atraso_maximo: AtrasoMaximo | None = None
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
    atraso_maximo: AtrasoMaximo
    referencia_inicio: ReferenciaInicio
    # Registros legados podem não ter a duração e o início cadastrados.
    prazo_dias: PrazoDias | None
    data_inicio: datetime | None
    proxima_ocorrencia: datetime | None
    data_fim: datetime
    fk_casa_id: UUID
    usuarios_atribuidos: list[UUID] = Field(default_factory=list)
    fk_usuario_id: UUID
