from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends

from core.autenticacao import UsuarioAtual
from core.database import get_supabase
from schemas.tarefa import EstadoTarefa, TarefaAtualizar, TarefaCriar, TarefaResposta
from services.tarefa import ServicoTarefa

router = APIRouter(prefix="/tarefas", tags=["Tarefas"])


@router.post("/", response_model=TarefaResposta, status_code=201)
def criar_tarefa(
    tarefa: TarefaCriar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoTarefa(supabase)
    return servico.criar_tarefa(tarefa, usuario_atual.id)


@router.get("/", response_model=list[TarefaResposta])
def listar_tarefas(
    usuario_atual: UsuarioAtual,
    inicio: int = 0,
    limite: int = 100,
    supabase=Depends(get_supabase),
):
    servico = ServicoTarefa(supabase)
    return servico.listar_tarefas(inicio, limite)


@router.get("/casa/{id_casa}", response_model=list[TarefaResposta])
def listar_tarefas_por_casa(
    id_casa: UUID,
    usuario_atual: UsuarioAtual,
    estado: EstadoTarefa | Literal["todos"] | None = None,
    responsavel: UUID | None = None,
    prazo: Literal["todos", "hoje", "sete_dias", "atrasadas"] | None = None,
    supabase=Depends(get_supabase),
):
    servico = ServicoTarefa(supabase)
    return servico.listar_tarefas_por_casa(
        id_casa, estado=estado, responsavel=responsavel, prazo=prazo
    )


@router.get("/{id_tarefa}", response_model=TarefaResposta)
def buscar_tarefa(
    id_tarefa: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoTarefa(supabase)
    return servico.buscar_tarefa(id_tarefa)


@router.post("/{id_tarefa}/conclusoes", response_model=TarefaResposta)
def concluir_tarefa(
    id_tarefa: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoTarefa(supabase)
    return servico.concluir_tarefa(id_tarefa, usuario_atual.id)


@router.patch("/{id_tarefa}", response_model=TarefaResposta)
def atualizar_tarefa(
    id_tarefa: UUID,
    tarefa: TarefaAtualizar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoTarefa(supabase)
    return servico.atualizar_tarefa(id_tarefa, tarefa, usuario_atual.id)


@router.delete("/{id_tarefa}", response_model=bool)
def excluir_tarefa(
    id_tarefa: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    servico = ServicoTarefa(supabase)
    return servico.excluir_tarefa(id_tarefa, usuario_atual.id)
