from uuid import UUID
import bcrypt
from fastapi import HTTPException
from postgrest.exceptions import APIError
from schemas.usuario import UsuarioCriar, UsuarioAtualizar
from services.autorizacao import ServicoAutorizacaoCasa
from services.pertencer import ServicoPertencer


class ServicoUsuario:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def criar_usuario(self, dados: UsuarioCriar):
        busca = self.supabase.table("usuario").select(
            "id").eq("email", dados.email).execute()

        if len(busca.data) > 0:
            raise HTTPException(
                status_code=400, detail="E-mail já cadastrado.")

        senha_criptografada = bcrypt.hashpw(
            dados.senha.encode("utf-8"),
            bcrypt.gensalt(rounds=12),
        ).decode("utf-8")

        novo_usuario = {
            "nome": dados.nome,
            "email": dados.email,
            "telefone": dados.telefone,
            "senha_hash": senha_criptografada,
            "foto": dados.foto,
            "usuario_tipo": dados.usuario_tipo
        }

        resposta = self.supabase.table(
            "usuario").insert(novo_usuario).execute()

        if not resposta.data:
            raise HTTPException(
                status_code=500, detail="Erro ao criar usuário no banco.")
        return resposta.data[0]

    def buscar_usuario(self, id_usuario: UUID):  # Voltou UUID
        busca = self.supabase.table("usuario").select(
            "*").eq("id", str(id_usuario)).execute()  # Uso de str()

        if not busca.data:
            raise HTTPException(
                status_code=404, detail="Usuário não encontrado.")
        return busca.data[0]

    def atualizar_usuario(self, id_usuario: UUID, dados: UsuarioAtualizar):  # Voltou UUID
        dados_limpos = {k: v for k, v in dados.model_dump(
            exclude_unset=True).items() if v is not None}

        if not dados_limpos:
            raise HTTPException(
                status_code=400, detail="Nenhum dado para atualização.")

        if "email" in dados_limpos:
            duplicado = self.supabase.table("usuario").select("id").eq(
                "email", dados_limpos["email"]).neq("id", str(id_usuario)).execute()
            if duplicado.data:
                raise HTTPException(
                    status_code=400, detail="E-mail já cadastrado.")

        atualizacao = self.supabase.table("usuario").update(
            dados_limpos).eq("id", str(id_usuario)).execute()  # Uso de str()

        if not atualizacao.data:
            raise HTTPException(
                status_code=404, detail="Usuário não encontrado.")
        return atualizacao.data[0]

    def deletar_usuario(self, id_usuario: UUID):  # Voltou UUID
        casa_propria = self.supabase.table("casa").select("id").eq(
            "fk_usuario_id", str(id_usuario)).limit(1).execute()
        if casa_propria.data:
            raise HTTPException(
                status_code=409,
                detail="Você é proprietário de uma casa e não pode excluir a conta. "
                       "Exclua a casa antes de excluir a conta.")

        try:
            delecao = self.supabase.table("usuario").delete().eq(
                "id", str(id_usuario)).execute()  # Uso de str()
        except APIError as erro:
            if erro.code != "23503":
                raise
            return self._anonimizar_usuario(id_usuario)

        if not delecao.data:
            raise HTTPException(
                status_code=404, detail="Usuário não encontrado ou já deletado.")
        return True

    # shortcut: as FKs para usuario são RESTRICT; quem tem histórico não é apagado,
    # só anonimizado. Apagar de verdade exige migration (ou transferir o histórico).
    def _anonimizar_usuario(self, id_usuario: UUID):
        id_str = str(id_usuario)
        ids_tarefas = [
            r["fk_tarefa_id"] for r in self.supabase.table("atribuida")
            .select("fk_tarefa_id").eq("fk_usuario_id", id_str).execute().data
        ]
        if ids_tarefas and self.supabase.table("tarefa").select("id").in_(
                "id", ids_tarefas).in_(
                "estado_atual", ["pendente", "atrasada"]).execute().data:
            raise HTTPException(
                status_code=409,
                detail="Você possui tarefas abertas. Conclua ou reatribua "
                       "as tarefas antes de excluir a conta.")

        vinculos = self.supabase.table("pertencer").select("fk_casa_id").eq(
            "fk_usuario_id", id_str).eq("ativo", True).execute().data
        for vinculo in vinculos:
            ServicoPertencer(self.supabase).deletar_pertencer(
                id_usuario, vinculo["fk_casa_id"])

        # Antes do update: se ele falhar, o usuário refaz o login e tenta de novo.
        self.supabase.table("sessao").delete().eq(
            "fk_usuario_id", id_str).execute()
        anonimizado = self.supabase.table("usuario").update({
            "nome": "Usuário removido",
            "email": f"removido-{id_str}@example.com",
            "telefone": None,
            "foto": None,
            "senha_hash": None,  # o login recusa conta sem hash
        }).eq("id", id_str).execute()
        if not anonimizado.data:
            raise HTTPException(
                status_code=404, detail="Usuário não encontrado ou já deletado.")
        return True

    def listar_usuarios(self, inicio: int = 0, limite: int = 100):
        resposta = (
            self.supabase.table("usuario")
            .select("*")
            .range(inicio, inicio + limite - 1)
            .execute()
        )
        return resposta.data

    def listar_usuarios_visiveis(
        self, id_usuario: UUID, inicio: int = 0, limite: int = 100
    ):
        autorizacao = ServicoAutorizacaoCasa(self.supabase)
        ids = autorizacao.ids_usuarios_visiveis(id_usuario)
        pagina = ids[inicio:inicio + limite]
        return autorizacao.registros_por_ids(
            "usuario", "id", pagina,
            "id,nome,email,telefone,foto,usuario_tipo,data_criacao", ("id",),
        )
