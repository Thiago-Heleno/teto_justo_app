from uuid import UUID
from fastapi import APIRouter, Depends, status
from core.database import get_supabase
from schemas.usuario import UsuarioCriar, UsuarioResposta, UsuarioAtualizar
from services.usuario import ServicoUsuario

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post("/", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario: UsuarioCriar, supabase=Depends(get_supabase)):
    servico = ServicoUsuario(supabase)
    return servico.criar_usuario(usuario)

@router.get("/", response_model=list[UsuarioResposta])
def listar_usuarios(
    inicio: int = 0,
    limite: int = 100,
    supabase=Depends(get_supabase),
):
    servico = ServicoUsuario(supabase)
    return servico.listar_usuarios(inicio, limite)


@router.get("/{id_usuario}", response_model=UsuarioResposta)
def buscar_usuario(id_usuario: UUID, supabase=Depends(get_supabase)):  # Voltou UUID
    servico = ServicoUsuario(supabase)
    return servico.buscar_usuario(id_usuario)


@router.patch("/{id_usuario}", response_model=UsuarioResposta)
def atualizar_usuario(id_usuario: UUID, dados: UsuarioAtualizar, supabase=Depends(get_supabase)):
    # Voltou UUID
    servico = ServicoUsuario(supabase)
    return servico.atualizar_usuario(id_usuario, dados)


@router.delete("/{id_usuario}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_usuario(id_usuario: UUID, supabase=Depends(get_supabase)):  # Voltou UUID
    servico = ServicoUsuario(supabase)
    servico.deletar_usuario(id_usuario)
    return
