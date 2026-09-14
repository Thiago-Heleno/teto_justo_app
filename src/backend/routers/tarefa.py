from uuid import UUID

from fastapi import APIRouter, Depends

from core.database import get_supabase
from schemas.tarefa import TarefaAtualizar, TarefaCriar, TarefaResposta
from services.tarefa import ServicoTarefa

router = APIRouter(prefix="/tarefas", tags=["Tarefas"])


@router.post("/", response_model=TarefaResposta, status_code=201)
def criar_tarefa(tarefa: TarefaCriar, supabase=Depends(get_supabase)):
    servico = ServicoTarefa(supabase)
    return servico.criar_tarefa(tarefa)


@router.get("/", response_model=list[TarefaResposta])
def listar_tarefas(
    inicio: int = 0,
    limite: int = 100,
    supabase=Depends(get_supabase),
):
    servico = ServicoTarefa(supabase)
    return servico.listar_tarefas(inicio, limite)


@router.get("/casa/{id_casa}", response_model=list[TarefaResposta])
def listar_tarefas_por_casa(
    id_casa: UUID,
    supabase=Depends(get_supabase),
):
    servico = ServicoTarefa(supabase)
    return servico.listar_tarefas_por_casa(id_casa)


@router.get("/{id_tarefa}", response_model=TarefaResposta)
def buscar_tarefa(id_tarefa: UUID, supabase=Depends(get_supabase)):
    servico = ServicoTarefa(supabase)
    return servico.buscar_tarefa(id_tarefa)


@router.patch("/{id_tarefa}", response_model=TarefaResposta)
def atualizar_tarefa(
    id_tarefa: UUID,
    tarefa: TarefaAtualizar,
    supabase=Depends(get_supabase),
):
    servico = ServicoTarefa(supabase)
    return servico.atualizar_tarefa(id_tarefa, tarefa)


@router.delete("/{id_tarefa}", response_model=bool)
def excluir_tarefa(id_tarefa: UUID, supabase=Depends(get_supabase)):
    servico = ServicoTarefa(supabase)
    return servico.excluir_tarefa(id_tarefa)
