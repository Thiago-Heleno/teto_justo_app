from uuid import UUID

from fastapi import HTTPException

from schemas.tarefa import TarefaAtualizar, TarefaCriar
from services.autorizacao import ServicoAutorizacaoCasa


class ServicoTarefa:
    def __init__(self, cliente_supabase):
        self.supabase = cliente_supabase

    def _buscar_tarefa_bruta(self, id_tarefa: UUID):
        resposta = (
            self.supabase.table("tarefa")
            .select("*")
            .eq("id", str(id_tarefa))
            .execute()
        )
        if not resposta.data:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        return resposta.data[0]

    def _buscar_usuarios_atribuidos(self, id_tarefa: UUID | str):
        resposta = (
            self.supabase.table("atribuida")
            .select("fk_usuario_id")
            .eq("fk_tarefa_id", str(id_tarefa))
            .execute()
        )
        return [registro["fk_usuario_id"] for registro in resposta.data]

    def _atribuir_usuarios(
        self,
        id_tarefa: UUID | str,
        ids_usuarios: list[UUID | str],
    ):
        ids_unicos = list(
            dict.fromkeys(str(id_usuario) for id_usuario in ids_usuarios)
        )
        if not ids_unicos:
            return

        atribuicoes = [
            {
                "fk_usuario_id": id_usuario,
                "fk_tarefa_id": str(id_tarefa),
            }
            for id_usuario in ids_unicos
        ]
        resposta = (
            self.supabase.table("atribuida")
            .insert(atribuicoes)
            .execute()
        )
        if not resposta.data:
            raise HTTPException(
                status_code=500,
                detail="Erro ao atribuir responsáveis pela tarefa.",
            )

    def _montar_resposta(self, tarefa: dict) -> dict:
        resposta = {
            "id": tarefa["id"],
            "nome": tarefa["nome"],
            "descricao": tarefa.get("descricao"),
            "estado_atual": tarefa["estado_atual"],
            "data_fim": tarefa["data_fim"],
            "fk_casa_id": tarefa["fk_casa_id"],
            "fk_usuario_id": tarefa["fk_usuario_id"],
        }
        resposta["usuarios_atribuidos"] = self._buscar_usuarios_atribuidos(
            tarefa["id"]
        )
        return resposta

    def criar_tarefa(
        self,
        dados_tarefa: TarefaCriar,
        id_usuario_atual: UUID,
    ):
        id_administrador = ServicoAutorizacaoCasa(
            self.supabase
        ).garantir_administrador_da_casa(
            dados_tarefa.fk_casa_id,
            id_usuario_atual,
        )
        ids_responsaveis = list(
            dict.fromkeys(str(id_usuario) for id_usuario in dados_tarefa.usuarios_atribuidos)
        )
        resposta_membros = (
            self.supabase.table("pertencer")
            .select("fk_usuario_id")
            .eq("fk_casa_id", str(dados_tarefa.fk_casa_id))
            .in_("fk_usuario_id", ids_responsaveis)
            .execute()
        )
        ids_membros = {
            str(registro["fk_usuario_id"]) for registro in resposta_membros.data
        }
        ids_membros.add(str(id_administrador))
        if set(ids_responsaveis) - ids_membros:
            raise HTTPException(
                status_code=422,
                detail="Todos os responsáveis devem pertencer à casa.",
            )
        dados = dados_tarefa.model_dump(mode="json")
        usuarios_atribuidos = dados.pop("usuarios_atribuidos", None)
        dados["dificuldade"] = dados.pop("peso")
        resposta = (
            self.supabase.table("tarefa")
            .insert(dados)
            .execute()
        )
        if not resposta.data:
            raise HTTPException(
                status_code=500,
                detail="Erro ao criar tarefa no banco.",
            )

        tarefa = resposta.data[0]
        if usuarios_atribuidos:
            self._atribuir_usuarios(tarefa["id"], usuarios_atribuidos)
        return self._montar_resposta(tarefa)

    def buscar_tarefa(self, id_tarefa: UUID):
        return self._montar_resposta(self._buscar_tarefa_bruta(id_tarefa))

    def listar_tarefas(self, inicio: int = 0, limite: int = 100):
        resposta = (
            self.supabase.table("tarefa")
            .select("*")
            .range(inicio, inicio + limite - 1)
            .execute()
        )
        return [self._montar_resposta(tarefa) for tarefa in resposta.data]

    def listar_tarefas_por_casa(self, id_casa: UUID):
        resposta = (
            self.supabase.table("tarefa")
            .select("*")
            .eq("fk_casa_id", str(id_casa))
            .execute()
        )
        return [self._montar_resposta(tarefa) for tarefa in resposta.data]

    def atualizar_tarefa(
        self,
        id_tarefa: UUID,
        dados_tarefa: TarefaAtualizar,
        id_usuario_atual: UUID,
    ):
        tarefa_atual = self._buscar_tarefa_bruta(id_tarefa)
        ServicoAutorizacaoCasa(
            self.supabase
        ).garantir_administrador_da_casa(
            tarefa_atual["fk_casa_id"],
            id_usuario_atual,
        )
        usuarios_foram_informados = (
            "usuarios_atribuidos" in dados_tarefa.model_fields_set
        )
        dados = dados_tarefa.model_dump(
            mode="json",
            exclude_unset=True,
            exclude_none=True,
        )
        usuarios_atribuidos = dados.pop("usuarios_atribuidos", None)
        if not dados and not usuarios_foram_informados:
            raise HTTPException(
                status_code=400,
                detail="Nenhum dado para atualização.",
            )

        if dados:
            resposta = (
                self.supabase.table("tarefa")
                .update(dados)
                .eq("id", str(id_tarefa))
                .execute()
            )
            if not resposta.data:
                raise HTTPException(
                    status_code=404,
                    detail="Tarefa não encontrada.",
                )

        if usuarios_foram_informados:
            (
                self.supabase.table("atribuida")
                .delete()
                .eq("fk_tarefa_id", str(id_tarefa))
                .execute()
            )
            if usuarios_atribuidos:
                self._atribuir_usuarios(id_tarefa, usuarios_atribuidos)

        return self.buscar_tarefa(id_tarefa)

    def excluir_tarefa(self, id_tarefa: UUID, id_usuario_atual: UUID):
        tarefa_atual = self._buscar_tarefa_bruta(id_tarefa)
        ServicoAutorizacaoCasa(
            self.supabase
        ).garantir_administrador_da_casa(
            tarefa_atual["fk_casa_id"],
            id_usuario_atual,
        )
        (
            self.supabase.table("atribuida")
            .delete()
            .eq("fk_tarefa_id", str(id_tarefa))
            .execute()
        )
        resposta = (
            self.supabase.table("tarefa")
            .delete()
            .eq("id", str(id_tarefa))
            .execute()
        )
        if not resposta.data:
            raise HTTPException(
                status_code=404,
                detail="Tarefa não encontrada.",
            )
        return True
