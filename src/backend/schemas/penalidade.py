from pydantic import BaseModel, ConfigDict, Field


class ProcessamentoPenalidadesResposta(BaseModel):
    tarefas_analisadas: int = Field(ge=0)
    marcadas_atrasadas: int = Field(ge=0)
    marcadas_nao_feitas: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")
