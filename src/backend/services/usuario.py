from passlib.context import CryptContext
from fastapi import HTTPException
from schemas.usuario import UsuarioCriar, UsuarioAtualizar

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class ServicoUsuario:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def criar_usuario(self, dados: UsuarioCriar):
        # Mudado de "Usuario" para "usuario"
        busca = self.supabase.table("usuario").select(
            "id").eq("email", dados.email).execute()
        if len(busca.data) > 0:
            raise HTTPException(
                status_code=400, detail="E-mail já cadastrado.")

        senha_criptografada = pwd_context.hash(dados.senha)

        novo_usuario = {
            "nome": dados.nome,
            "email": dados.email,
            "telefone": dados.telefone,
            "senha_hash": senha_criptografada
        }

        # Mudado de "Usuario" para "usuario"
        resposta = self.supabase.table(
            "usuario").insert(novo_usuario).execute()

        if not resposta.data:
            raise HTTPException(
                status_code=500, detail="Erro ao criar usuário no banco.")

        return resposta.data[0]

    def buscar_usuario(self, id_usuario: int):
        # Mudado de "Usuario" para "usuario"
        busca = self.supabase.table("usuario").select(
            "*").eq("id", id_usuario).execute()
        if not busca.data:
            raise HTTPException(
                status_code=404, detail="Usuário não encontrado.")
        return busca.data[0]

    def atualizar_usuario(self, id_usuario: int, dados: UsuarioAtualizar):
        dados_limpos = {k: v for k, v in dados.dict(
            exclude_unset=True).items() if v is not None}

        if not dados_limpos:
            raise HTTPException(
                status_code=400, detail="Nenhum dado para atualização.")

        # Mudado de "Usuario" para "usuario"
        atualizacao = self.supabase.table("usuario").update(
            dados_limpos).eq("id", id_usuario).execute()

        if not atualizacao.data:
            raise HTTPException(
                status_code=404, detail="Usuário não encontrado.")
        return atualizacao.data[0]
