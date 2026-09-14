from uuid import UUID
from fastapi import APIRouter, Depends
from core.database import get_supabase
from schemas.usuario import UsuarioCriar, UsuarioResposta, UsuarioAtualizar
from services.usuario import ServicoUsuario

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post("/", response_model=UsuarioResposta, status_code=201)
def registrar_usuario(usuario: UsuarioCriar, supabase=Depends(get_supabase)):
    servico = ServicoUsuario(supabase)
    return servico.criar_usuario(usuario)


@router.get("/{id_usuario}", response_model=UsuarioResposta)
def buscar_usuario(id_usuario: UUID, supabase=Depends(get_supabase)):
    servico = ServicoUsuario(supabase)
    return servico.buscar_usuario(id_usuario)


@router.patch("/{id_usuario}", response_model=UsuarioResposta)
def atualizar_usuario(id_usuario: UUID, dados: UsuarioAtualizar, supabase=Depends(get_supabase)):
    servico = ServicoUsuario(supabase)
    return servico.atualizar_usuario(id_usuario, dados)
