from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from core.autenticacao import UsuarioAtual
from core.database import get_supabase
from schemas.usuario import UsuarioCriar, UsuarioResposta, UsuarioAtualizar
from services.usuario import ServicoUsuario
from services.autorizacao import ServicoAutorizacaoCasa

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


@router.post("/", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario: UsuarioCriar, supabase=Depends(get_supabase)):
    servico = ServicoUsuario(supabase)
    return servico.criar_usuario(usuario)

@router.get("/", response_model=list[UsuarioResposta])
def listar_usuarios(
    usuario_atual: UsuarioAtual,
    inicio: int = Query(0, ge=0),
    limite: int = Query(100, ge=1),
    supabase=Depends(get_supabase),
):
    servico = ServicoUsuario(supabase)
    return servico.listar_usuarios_visiveis(usuario_atual.id, inicio, limite)


@router.get("/eu", response_model=UsuarioResposta)
def buscar_usuario_atual(usuario_atual: UsuarioAtual):
    return usuario_atual


@router.get("/{id_usuario}", response_model=UsuarioResposta)
def buscar_usuario(
    id_usuario: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):  # Voltou UUID
    ServicoAutorizacaoCasa(supabase).garantir_usuario_visivel(
        id_usuario, usuario_atual.id
    )
    servico = ServicoUsuario(supabase)
    return servico.buscar_usuario(id_usuario)


@router.patch("/{id_usuario}", response_model=UsuarioResposta)
def atualizar_usuario(
    id_usuario: UUID,
    dados: UsuarioAtualizar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    if id_usuario != usuario_atual.id:
        raise HTTPException(status_code=403, detail="Somente a própria conta pode ser alterada.")
    servico = ServicoUsuario(supabase)
    return servico.atualizar_usuario(id_usuario, dados)


@router.delete("/{id_usuario}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_usuario(
    id_usuario: UUID,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):  # Voltou UUID
    if id_usuario != usuario_atual.id:
        raise HTTPException(status_code=403, detail="Somente a própria conta pode ser excluída.")
    servico = ServicoUsuario(supabase)
    servico.deletar_usuario(id_usuario)
    return
