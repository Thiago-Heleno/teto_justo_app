from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import BackgroundTasks, HTTPException
from postgrest.exceptions import APIError

from schemas.tarefa import EstadoTarefa, TarefaAtualizar, TarefaCriar
from services.autorizacao import ServicoAutorizacaoCasa
from services.ciclo_vida_tarefa import (
    ESTADOS_FINAIS,
    ServicoCicloVidaTarefa,
    atualizar_prazo,
    corresponde_prazo,
    instante_utc,
    janela_dia_fixo,
)
from services.score import ServicoScore
from services.notificacao import ServicoNotificacao

_FILTROS_PRAZO = ("todos", "hoje", "sete_dias", "antigas", "atrasadas")


class ServicoTarefa:
    def __init__(self, cliente_supabase, tarefas_fundo: BackgroundTasks | None = None):
        self.supabase = cliente_supabase
        self.notificacoes = ServicoNotificacao(cliente_supabase, tarefas_fundo)
        self.ciclo_vida = ServicoCicloVidaTarefa(cliente_supabase, self.notificacoes)

    def _buscar_tarefa_bruta(self, id_tarefa: UUID):
        resposta = (
            self.supabase.table("tarefa")
            .select("*")
            .eq("id", str(id_tarefa))
            .execute()
        )
        if not resposta.data:
            raise HTTPException(
                status_code=404, detail="Tarefa não encontrada.")
        return resposta.data[0]

    def _buscar_usuarios_atribuidos(self, id_tarefa: UUID | str):
        resposta = (
            self.supabase.table("atribuida")
            .select("fk_usuario_id")
            .eq("fk_tarefa_id", str(id_tarefa))
            .execute()
        )
        return [registro["fk_usuario_id"] for registro in resposta.data]

    def _fuso_casa(self, id_casa: UUID | str) -> ZoneInfo:
        resposta = (
            self.supabase.table("casa")
            .select("timezone")
            .eq("id", str(id_casa))
            .execute()
        )
        if not resposta.data:
            raise HTTPException(status_code=404, detail="Casa não encontrada.")
        return ZoneInfo(resposta.data[0].get("timezone") or "America/Sao_Paulo")

    def _fuso_tarefa(self, tarefa: dict) -> ZoneInfo:
        if tarefa.get("timezone"):
            return ZoneInfo(tarefa["timezone"])
        return self._fuso_casa(tarefa["fk_casa_id"])

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

    def _sincronizar_estado_por_atraso(
        self, tarefa: dict, agora: datetime | None = None,
    ) -> dict:
        atualizada = self.ciclo_vida.sincronizar_estado(tarefa, agora or datetime.now(timezone.utc))
        if atualizada is None:
            return self._buscar_tarefa_bruta(UUID(tarefa["id"]))
        return atualizada

    def _montar_resposta(self, tarefa: dict, agora: datetime | None = None) -> dict:
        tarefa = self._sincronizar_estado_por_atraso(tarefa, agora)
        modo_prazo = tarefa.get("modo_prazo") or "intervalo"
        inicio = tarefa.get("data_inicio") or tarefa.get("criado_em")
        concluida = tarefa.get("concluida_em")
        resposta = {
            "id": tarefa["id"],
            "nome": tarefa["nome"],
            "descricao": tarefa.get("descricao"),
            "estado_atual": tarefa["estado_atual"],
            "peso": tarefa["dificuldade"],
            "pontuacao": ServicoScore.pontos_por_peso(tarefa["dificuldade"]),
            "estrategia_penalidade": "proporcional",
            "tipo": tarefa.get("tipo") or "unitaria",
            "modo_prazo": modo_prazo,
            "data_fixa": (
                instante_utc(tarefa["data_fim"])
                .astimezone(self._fuso_tarefa(tarefa))
                .date()
                .isoformat()
                if modo_prazo == "dia_fixo" else None
            ),
            "concluida_em": instante_utc(concluida).isoformat() if concluida else None,
            "resultado_pontuacao": tarefa.get("resultado_pontuacao"),
            "referencia_inicio": tarefa.get("referencia_inicio", "criacao"),
            "prazo_dias": tarefa.get("prazo_dias"),
            "data_inicio": instante_utc(inicio).isoformat() if inicio else None,
            "proxima_ocorrencia": tarefa.get("proxima_ocorrencia"),
            "atraso_maximo": tarefa["atraso_maximo"],
            "data_fim": instante_utc(tarefa["data_fim"]).isoformat(),
            "fk_casa_id": tarefa["fk_casa_id"],
            "fk_usuario_id": tarefa["fk_usuario_id"],
        }
        resposta["usuarios_atribuidos"] = self._buscar_usuarios_atribuidos(tarefa["id"])
        return resposta

    def criar_tarefa(
        self,
        dados_tarefa: TarefaCriar,
        id_usuario_atual: UUID,
    ):
        autorizacao = ServicoAutorizacaoCasa(self.supabase)
        autorizacao.garantir_administrador_da_casa(
            dados_tarefa.fk_casa_id,
            id_usuario_atual,
        )
        autorizacao.garantir_responsaveis_da_casa(
            dados_tarefa.fk_casa_id,
            dados_tarefa.usuarios_atribuidos,
        )
        dados = dados_tarefa.model_dump(mode="json")
        usuarios_atribuidos = dados.pop("usuarios_atribuidos", None)
        dados["dificuldade"] = dados.pop("peso")
        dados["pontuacao"] = ServicoScore.pontos_por_peso(dados["dificuldade"])
        dados["fk_usuario_id"] = str(id_usuario_atual)
        dados.pop("estrategia_penalidade")
        dados.pop("data_fixa")
        if dados_tarefa.modo_prazo == "dia_fixo":
            fuso = self._fuso_casa(dados_tarefa.fk_casa_id)
            inicio, vencimento = janela_dia_fixo(
                dados_tarefa.data_fixa,
                dados_tarefa.prazo_dias,
                fuso,
            )
            if vencimento <= datetime.now(timezone.utc):
                raise HTTPException(status_code=422, detail="A data fixa deve estar no futuro.")
            dados["timezone"] = fuso.key
        else:
            inicio = datetime.now(timezone.utc)
            vencimento = inicio + timedelta(days=dados_tarefa.prazo_dias)
        dados["data_inicio"] = inicio.isoformat()
        dados["data_fim"] = vencimento.isoformat()
        resposta = self.supabase.table("tarefa").insert(dados).execute()
        if not resposta.data:
            raise HTTPException(
                status_code=500,
                detail="Erro ao criar tarefa no banco.",
            )

        tarefa = resposta.data[0]
        if usuarios_atribuidos:
            self._atribuir_usuarios(tarefa["id"], usuarios_atribuidos)
        resultado = self._montar_resposta(tarefa)
        if resultado["estado_atual"] not in ESTADOS_FINAIS:
            self.notificacoes.notificar_tarefa(
                "tarefa_atribuida", resultado, resultado["usuarios_atribuidos"]
            )
        return resultado

    def buscar_tarefa(self, id_tarefa: UUID):
        return self._montar_resposta(self._buscar_tarefa_bruta(id_tarefa))

    def buscar_tarefa_autorizada(self, id_tarefa: UUID, id_usuario: UUID):
        tarefa = self._buscar_tarefa_bruta(id_tarefa)
        ServicoAutorizacaoCasa(self.supabase).garantir_acesso(
            tarefa["fk_casa_id"], id_usuario
        )
        return self._montar_resposta(tarefa)

    def listar_tarefas_acessiveis(
        self, id_usuario: UUID, inicio: int = 0, limite: int = 100
    ):
        autorizacao = ServicoAutorizacaoCasa(self.supabase)
        ids_casas = autorizacao.ids_casas_acessiveis(id_usuario)
        registros = autorizacao.registros_por_ids(
            "tarefa", "fk_casa_id", ids_casas, "*", ("id",)
        )
        pagina = sorted(registros, key=lambda tarefa: str(tarefa["id"]))[
            inicio:inicio + limite
        ]
        return [self._montar_resposta(tarefa) for tarefa in pagina]

    def listar_tarefas(self, inicio: int = 0, limite: int = 100):
        resposta = (
            self.supabase.table("tarefa")
            .select("*")
            .range(inicio, inicio + limite - 1)
            .execute()
        )
        return [self._montar_resposta(tarefa) for tarefa in resposta.data]

    def listar_tarefas_por_casa(
        self,
        id_casa: UUID,
        estado: EstadoTarefa | None = None,
        responsavel: UUID | None = None,
        prazo: str | None = None,
    ):
        if prazo is not None and prazo not in _FILTROS_PRAZO:
            raise HTTPException(
                status_code=422,
                detail="Filtro de prazo inválido.",
            )

        resposta = (
            self.supabase.table("tarefa")
            .select("*")
            .eq("fk_casa_id", str(id_casa))
            .execute()
        )
        tarefas = []
        agora = datetime.now(timezone.utc)
        fuso = (
            self._fuso_casa(id_casa)
            if prazo in ("antigas", "hoje", "sete_dias") else None
        )
        for tarefa in resposta.data:
            tarefa_resposta = self._montar_resposta(tarefa, agora)
            if (
                estado
                and estado != "todos"
                and tarefa_resposta["estado_atual"] != estado
            ):
                continue
            if (
                responsavel
                and str(responsavel) not in tarefa_resposta["usuarios_atribuidos"]
            ):
                continue
            if not corresponde_prazo(tarefa_resposta, prazo, agora, fuso):
                continue
            tarefas.append(tarefa_resposta)
        return tarefas

    def _concluir_tarefa(self, tarefa: dict, id_usuario_atual: UUID):
        responsaveis = self._buscar_usuarios_atribuidos(tarefa["id"])
        if str(id_usuario_atual) not in responsaveis:
            raise HTTPException(
                status_code=403,
                detail="Apenas um responsável pode finalizar esta tarefa.",
            )
        agora = datetime.now(timezone.utc)
        tarefa = self._sincronizar_estado_por_atraso(tarefa, agora)
        finalizada = self.ciclo_vida.concluir(tarefa, responsaveis, agora)
        return self._montar_resposta(finalizada, agora)

    def concluir_tarefa(self, id_tarefa: UUID, id_usuario_atual: UUID):
        tarefa = self._buscar_tarefa_bruta(id_tarefa)
        return self._concluir_tarefa(tarefa, id_usuario_atual)

    def atualizar_tarefa(
        self,
        id_tarefa: UUID,
        dados_tarefa: TarefaAtualizar,
        id_usuario_atual: UUID,
    ):
        tarefa_atual = self._buscar_tarefa_bruta(id_tarefa)
        finalizacao_pelo_responsavel = dados_tarefa.estado_atual == "finalizado"
        if finalizacao_pelo_responsavel:
            if dados_tarefa.model_fields_set != {"estado_atual"}:
                raise HTTPException(
                    status_code=422,
                    detail="Finalize a tarefa sem alterar suas regras na mesma requisição.",
                )
            return self._concluir_tarefa(tarefa_atual, id_usuario_atual)
        else:
            ServicoAutorizacaoCasa(self.supabase).garantir_administrador_da_casa(
                tarefa_atual["fk_casa_id"],
                id_usuario_atual,
            )
        if tarefa_atual["estado_atual"] in ESTADOS_FINAIS:
            raise HTTPException(
                status_code=409,
                detail="Uma tarefa encerrada não pode ser alterada ou finalizada novamente.",
            )
        usuarios_foram_informados = "usuarios_atribuidos" in dados_tarefa.model_fields_set
        dados = dados_tarefa.model_dump(
            mode="json",
            exclude_unset=True,
            exclude_none=True,
        )
        if "peso" in dados:
            dados["dificuldade"] = dados.pop("peso")
            dados["pontuacao"] = ServicoScore.pontos_por_peso(dados["dificuldade"])
        editar_dia_fixo = (
            tarefa_atual.get("modo_prazo") == "dia_fixo"
            and bool({"prazo_dias", "data_fixa"} & dados.keys())
        )
        fuso = self._fuso_tarefa(tarefa_atual) if editar_dia_fixo else None
        dados = atualizar_prazo(tarefa_atual, dados, fuso, datetime.now(timezone.utc))
        usuarios_atribuidos = dados.pop("usuarios_atribuidos", None)
        if not dados and not usuarios_foram_informados:
            raise HTTPException(
                status_code=400,
                detail="Nenhum dado para atualização.",
            )

        if usuarios_foram_informados:
            ServicoAutorizacaoCasa(self.supabase).garantir_responsaveis_da_casa(
                tarefa_atual["fk_casa_id"], usuarios_atribuidos
            )

        usuarios_anteriores = (
            set(self._buscar_usuarios_atribuidos(id_tarefa)) if usuarios_foram_informados else None
        )
        novos_usuarios = {str(usuario) for usuario in (usuarios_atribuidos or [])}
        mudou_responsavel = (
            usuarios_anteriores is not None and usuarios_anteriores != novos_usuarios
        )
        mudou_prazo = instante_utc(
            dados.get("data_fim", tarefa_atual["data_fim"])
        ) != instante_utc(tarefa_atual["data_fim"])
        mudou_inicio = "data_inicio" in dados and (
            not tarefa_atual.get("data_inicio") or instante_utc(dados["data_inicio"])
            != instante_utc(tarefa_atual["data_inicio"])
        )
        if (
            dados.get("data_fim", tarefa_atual["data_fim"]) != tarefa_atual["data_fim"]
            or usuarios_foram_informados
        ):
            dados["aviso_enviado_em"] = None
            if "aviso_atraso_enviado_em" in tarefa_atual:
                dados["aviso_atraso_enviado_em"] = None

        if dados:
            resposta = (
                self.supabase.table("tarefa").update(dados).eq("id", str(id_tarefa)).execute()
            )
            if not resposta.data:
                raise HTTPException(
                    status_code=404,
                    detail="Tarefa não encontrada.",
                )

        if usuarios_foram_informados:
            (self.supabase.table("atribuida").delete().eq("fk_tarefa_id", str(id_tarefa)).execute())
            if usuarios_atribuidos:
                self._atribuir_usuarios(id_tarefa, usuarios_atribuidos)

        resultado = self.buscar_tarefa(id_tarefa)
        if mudou_inicio or mudou_responsavel:
            self.notificacoes.reiniciar_aviso_inicio(resultado)
        atuais = set(resultado["usuarios_atribuidos"])
        if mudou_responsavel:
            self.notificacoes.notificar_tarefa(
                "tarefa_atribuida", resultado, sorted(atuais - usuarios_anteriores)
            )
            self.notificacoes.notificar_tarefa(
                "atribuicao_removida", resultado, sorted(usuarios_anteriores - atuais)
            )
        if mudou_prazo:
            destinatarios = atuais if usuarios_anteriores is None else atuais & usuarios_anteriores
            self.notificacoes.notificar_tarefa("prazo_alterado", resultado, sorted(destinatarios))
        return resultado

    def excluir_tarefa(self, id_tarefa: UUID, id_usuario_atual: UUID):
        tarefa_atual = self._buscar_tarefa_bruta(id_tarefa)
        ServicoAutorizacaoCasa(
            self.supabase
        ).garantir_administrador_da_casa(
            tarefa_atual["fk_casa_id"],
            id_usuario_atual,
        )
        if(
            tarefa_atual["estado_atual"] == "finalizado"
            or tarefa_atual.get("rotatividade_id") is not None
        ):
            raise HTTPException(
                status_code=409,
                detail="Tarefa com crédito registrado não pode ser excluída.",
            )
        try:
            resposta = self.supabase.table("tarefa").delete().eq("id", str(id_tarefa)).execute()
        except APIError as erro:
            if erro.code == "23503":
                raise HTTPException(
                    status_code=409,
                    detail="Tarefa com crédito registrado não pode ser excluída.",
                ) from erro
            raise
        if not resposta.data:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        return True

    def reabrir_tarefa(self, id_tarefa: UUID, id_usuario_atual: UUID):
        tarefa = self._buscar_tarefa_bruta(id_tarefa)
        responsaveis = self._buscar_usuarios_atribuidos(tarefa["id"])
        if str(id_usuario_atual) not in responsaveis:
            ServicoAutorizacaoCasa(self.supabase).garantir_administrador_da_casa(
                tarefa["fk_casa_id"], id_usuario_atual
            )
        agora = datetime.now(timezone.utc)
        reaberta = self.ciclo_vida.reabrir(tarefa, responsaveis, agora)
        return self._montar_resposta(reaberta, agora)
