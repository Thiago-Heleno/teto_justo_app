from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from core.autenticacao import UsuarioAtual
from core.database import get_supabase
from schemas.usuario import (
    RecuperarSenhaEntrada,
    RedefinirSenhaEntrada,
    UsuarioAtualizar,
    UsuarioCadastro,
    UsuarioCriar,
    UsuarioResposta,
    VerificacaoEmailResposta,
)
from schemas.notificacao import (
    DispositivoPushRegistrar,
    DispositivoPushRemover,
    DispositivoPushResposta,
)
from services.usuario import ServicoUsuario
from services.autorizacao import ServicoAutorizacaoCasa
from services.envio_email import ServicoEmail
from services.limite_login import (
    LimitadorLogin,
    get_limitador_recuperacao,
    get_limitador_verificacao,
)
from services.notificacao import ServicoNotificacao
from services.verificacao_email import ServicoVerificacaoEmail

router = APIRouter(prefix="/usuarios", tags=["Usuários"])


def _ip_cliente(request: Request) -> str:
    if not request.client or not request.client.host:
        raise HTTPException(status_code=503, detail="Cadastro temporariamente indisponível.")
    return request.client.host


@router.post("/codigo-verificacao", response_model=VerificacaoEmailResposta)
def solicitar_codigo_verificacao(
    usuario: UsuarioCriar,
    request: Request,
    supabase=Depends(get_supabase),
    limitador: LimitadorLogin = Depends(get_limitador_verificacao),
):
    email, ip = str(usuario.email), _ip_cliente(request)
    limitador.reservar_tentativa("envio:" + email, "envio:" + ip)
    ServicoUsuario(supabase).garantir_email_disponivel(email)
    emitido = ServicoVerificacaoEmail().emitir(email)
    try:
        ServicoEmail().enviar(
            email,
            "Seu código de verificação | Teto Justo",
            ServicoVerificacaoEmail.montar_html(emitido["codigo"]),
        )
    except Exception:
        limitador.cancelar_tentativa("envio:" + email, "envio:" + ip)
        raise
    return emitido


@router.post("/", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def registrar_usuario(
    usuario: UsuarioCadastro,
    request: Request,
    supabase=Depends(get_supabase),
    limitador: LimitadorLogin = Depends(get_limitador_verificacao),
):
    email, ip = str(usuario.email), _ip_cliente(request)
    limitador.reservar_tentativa("codigo:" + email, "codigo:" + ip)
    try:
        ServicoVerificacaoEmail().verificar(email, usuario.codigo, usuario.token_verificacao)
    except HTTPException as erro:
        if erro.status_code == 400:
            limitador.registrar_falha("codigo:" + email, "codigo:" + ip)
        else:
            limitador.cancelar_tentativa("codigo:" + email, "codigo:" + ip)
        raise
    limitador.confirmar_sucesso("codigo:" + email, "codigo:" + ip)
    return ServicoUsuario(supabase).criar_usuario(usuario)

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


@router.post("/eu/dispositivos", response_model=DispositivoPushResposta)
def registrar_dispositivo(
    dados: DispositivoPushRegistrar,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    return ServicoNotificacao(supabase).registrar_dispositivo(usuario_atual.id, dados)


@router.delete("/eu/dispositivos", status_code=status.HTTP_204_NO_CONTENT)
def remover_dispositivo(
    dados: DispositivoPushRemover,
    usuario_atual: UsuarioAtual,
    supabase=Depends(get_supabase),
):
    ServicoNotificacao(supabase).remover_dispositivo(usuario_atual.id, dados.token)


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


@router.post("/recuperar-senha", response_model=VerificacaoEmailResposta)
def solicitar_recuperacao_senha(
    dados: RecuperarSenhaEntrada,
    request: Request,
    supabase=Depends(get_supabase),
    limitador: LimitadorLogin = Depends(get_limitador_recuperacao),
):
    email, ip = str(dados.email), _ip_cliente(request)
    limitador.reservar_tentativa("envio:" + email, "envio:" + ip)
    hash_atual = ServicoUsuario(supabase).obter_hash_senha(email)
    # Emite sempre: a resposta é igual exista a conta ou não; só o e-mail muda.
    emitido = ServicoVerificacaoEmail().emitir(email, "redefinicao", hash_atual or "")
    if hash_atual:
        try:
            ServicoEmail().enviar(
                email,
                "Redefinição de senha | Teto Justo",
                ServicoVerificacaoEmail.montar_html(
                    emitido["codigo"],
                    "Redefina sua senha",
                    "Use o código abaixo para criar uma nova senha.",
                ),
            )
        except Exception:
            limitador.cancelar_tentativa("envio:" + email, "envio:" + ip)
            raise
    return emitido


@router.post("/redefinir-senha", status_code=status.HTTP_204_NO_CONTENT)
def redefinir_senha(
    dados: RedefinirSenhaEntrada,
    request: Request,
    supabase=Depends(get_supabase),
    limitador: LimitadorLogin = Depends(get_limitador_recuperacao),
):
    email, ip = str(dados.email), _ip_cliente(request)
    limitador.reservar_tentativa("codigo:" + email, "codigo:" + ip)
    servico = ServicoUsuario(supabase)
    try:
        hash_atual = servico.obter_hash_senha(email)
        ServicoVerificacaoEmail().verificar(
            email, dados.codigo, dados.token_verificacao, "redefinicao", hash_atual or ""
        )
        servico.redefinir_senha(email, dados.nova_senha, hash_atual)
    except HTTPException as erro:
        if erro.status_code == 400:
            limitador.registrar_falha("codigo:" + email, "codigo:" + ip)
        else:
            limitador.cancelar_tentativa("codigo:" + email, "codigo:" + ip)
        raise
    limitador.confirmar_sucesso("codigo:" + email, "codigo:" + ip)


