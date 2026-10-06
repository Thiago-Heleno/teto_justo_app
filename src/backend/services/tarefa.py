from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from postgrest.exceptions import APIError

from schemas.tarefa import EstadoTarefa, TarefaAtualizar, TarefaCriar
from services.autorizacao import ServicoAutorizacaoCasa
from services.score import ServicoScore

_ESTADOS_FINAIS = ("finalizado", "nao_feito")
_FILTROS_PRAZO = ("todos", "hoje", "sete_dias", "atrasadas")
_MAX_TENTATIVAS_CAS = 5


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

    @staticmethod
    def janela_dia_fixo(
        data_fixa: date, prazo_dias: int, fuso: ZoneInfo
    ) -> tuple[datetime, datetime]:
        vencimento = datetime.combine(data_fixa, time.max, tzinfo=fuso).astimezone(timezone.utc)
        return vencimento - timedelta(days=prazo_dias), vencimento

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

    def _sincronizar_estado_por_atraso(self, tarefa: dict) -> dict:
        if tarefa["estado_atual"] in _ESTADOS_FINAIS:
            return tarefa

        data_fim = self._data_fim_com_fuso(tarefa["data_fim"])
        agora = datetime.now(timezone.utc)
        dias_atraso = ServicoScore.calcular_dias_atraso(data_fim, agora)

        if dias_atraso <= tarefa["atraso_maximo"]:
            return tarefa

        resposta = (
            self.supabase.table("tarefa")
            .update({"estado_atual": "nao_feito"})
            .eq("id", str(tarefa["id"]))
            .in_("estado_atual", ["pendente", "atrasada"])
            .eq("data_fim", tarefa["data_fim"])
            .eq("atraso_maximo", tarefa["atraso_maximo"])
            .execute()
        )
        return resposta.data[0] if resposta.data else self._buscar_tarefa_bruta(UUID(tarefa["id"]))

    def _montar_resposta(self, tarefa: dict) -> dict:
        tarefa = self._sincronizar_estado_por_atraso(tarefa)
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
                self._data_fim_com_fuso(tarefa["data_fim"])
                .astimezone(self._fuso_tarefa(tarefa))
                .date()
                .isoformat()
                if modo_prazo == "dia_fixo" else None
            ),
            "concluida_em": self._data_fim_com_fuso(concluida).isoformat() if concluida else None,
            "resultado_pontuacao": tarefa.get("resultado_pontuacao"),
            "referencia_inicio": tarefa.get("referencia_inicio", "criacao"),
            "prazo_dias": tarefa.get("prazo_dias"),
            "data_inicio": self._data_fim_com_fuso(inicio).isoformat() if inicio else None,
            "proxima_ocorrencia": tarefa.get("proxima_ocorrencia"),
            "atraso_maximo": tarefa["atraso_maximo"],
            "data_fim": self._data_fim_com_fuso(tarefa["data_fim"]).isoformat(),
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
            inicio, vencimento = self.janela_dia_fixo(
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
        return self._montar_resposta(tarefa)

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

    @staticmethod
    def _data_fim_com_fuso(data_fim: str | datetime) -> datetime:
        if isinstance(data_fim, datetime):
            valor = data_fim
        else:
            valor = datetime.fromisoformat(data_fim.replace("Z", "+00:00"))
        return (
            valor.replace(tzinfo=timezone.utc)
            if valor.tzinfo is None
            else valor.astimezone(timezone.utc)
        )

    @classmethod
    def _corresponde_prazo(
        cls,
        tarefa: dict,
        filtro_prazo: str | None,
        agora: datetime,
    ) -> bool:
        if not filtro_prazo or filtro_prazo == "todos":
            return True

        data_fim = cls._data_fim_com_fuso(tarefa["data_fim"])
        agora = agora.astimezone(timezone.utc)
        if filtro_prazo == "atrasadas":
            return data_fim < agora and tarefa["estado_atual"] != "finalizado"

        if filtro_prazo == "hoje":
            fim_de_hoje = datetime.combine(
                agora.date(), time.max, tzinfo=timezone.utc
            )
            return agora <= data_fim <= fim_de_hoje

        if filtro_prazo == "sete_dias":
            return agora <= data_fim <= agora + timedelta(days=7)

        return False

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
        for tarefa in resposta.data:
            tarefa_resposta = self._montar_resposta(tarefa)
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
            if not self._corresponde_prazo(tarefa_resposta, prazo, agora):
                continue
            tarefas.append(tarefa_resposta)
        return tarefas

    def _finalizar_tarefa(self, tarefa: dict, responsaveis: list[str]) -> dict:
        if len(responsaveis) != 1:
            raise HTTPException(
                status_code=409,
                detail="A tarefa precisa ter exatamente um responsável antes da conclusão.",
            )
        concluida_em = datetime.now(timezone.utc)
        resultado = ServicoScore().calcular_score(
            peso=tarefa["dificuldade"],
            atraso_maximo=tarefa["atraso_maximo"],
            data_fim=self._data_fim_com_fuso(tarefa["data_fim"]),
            concluida_em=concluida_em,
            usuarios_atribuidos=[UUID(responsaveis[0])],
        )
        if resultado.dias_atraso > tarefa["atraso_maximo"]:
            raise HTTPException(status_code=409, detail="A tolerância de atraso foi ultrapassada.")

        tarefa_finalizada = self._creditar_e_finalizar(
            tarefa, resultado.usuario_id, resultado.pontos_finais, concluida_em
        )
        resposta = self._montar_resposta(tarefa_finalizada)
        resposta["resultado_pontuacao"] = {
            "pontos_possiveis": tarefa["pontuacao"],
            "pontos_ganhos": resultado.pontos_finais,
            "saldo_atual": self._buscar_saldo(str(resultado.usuario_id), str(tarefa["fk_casa_id"])),
        }
        return resposta

    def _concluir_tarefa(self, tarefa: dict, id_usuario_atual: UUID):
        responsaveis = self._buscar_usuarios_atribuidos(tarefa["id"])
        if str(id_usuario_atual) not in responsaveis:
            raise HTTPException(
                status_code=403,
                detail="Apenas um responsável pode finalizar esta tarefa.",
            )
        tarefa = self._sincronizar_estado_por_atraso(tarefa)
        inicio = tarefa.get("data_inicio")
        if inicio and self._data_fim_com_fuso(inicio) > datetime.now(timezone.utc):
            raise HTTPException(status_code=409, detail="Esta ocorrência ainda não começou.")
        if tarefa["estado_atual"] in _ESTADOS_FINAIS:
            raise HTTPException(
                status_code=409,
                detail="Uma tarefa encerrada não pode ser alterada ou finalizada novamente.",
            )
        return self._finalizar_tarefa(tarefa, responsaveis)

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
        if tarefa_atual["estado_atual"] in _ESTADOS_FINAIS:
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
        data_fixa = dados.pop("data_fixa", None)
        modo_prazo = tarefa_atual.get("modo_prazo") or "intervalo"
        if data_fixa is not None and modo_prazo != "dia_fixo":
            raise HTTPException(status_code=422, detail="Esta tarefa não usa dia fixo.")
        if modo_prazo == "dia_fixo" and ("prazo_dias" in dados or data_fixa is not None):
            fuso = self._fuso_tarefa(tarefa_atual)
            data_fixa_atual = (
                self._data_fim_com_fuso(tarefa_atual["data_fim"]).astimezone(fuso).date()
            )
            prazo = dados.get("prazo_dias", tarefa_atual.get("prazo_dias"))
            if prazo is None:
                raise HTTPException(
                    status_code=409,
                    detail="Defina prazo_dias para editar o vencimento desta tarefa legada.",
                )
            inicio, vencimento = self.janela_dia_fixo(
                date.fromisoformat(data_fixa) if data_fixa else data_fixa_atual,
                prazo,
                fuso,
            )
            if vencimento <= datetime.now(timezone.utc):
                raise HTTPException(status_code=422, detail="A data fixa deve estar no futuro.")
            dados["data_inicio"] = inicio.isoformat()
            dados["data_fim"] = vencimento.isoformat()
            if not tarefa_atual.get("timezone"):
                dados["timezone"] = fuso.key
        elif "prazo_dias" in dados:
            inicio = tarefa_atual.get("data_inicio") or tarefa_atual.get("criado_em")
            if inicio is None:
                raise HTTPException(
                    status_code=409,
                    detail="A tarefa legada não possui referência de início do prazo.",
                )
            data_fim = self._data_fim_com_fuso(inicio) + timedelta(days=dados["prazo_dias"])
            if data_fim <= datetime.now(timezone.utc):
                raise HTTPException(status_code=422, detail="O novo prazo deve estar no futuro.")
            dados["data_fim"] = data_fim.isoformat()
        if {"prazo_dias", "atraso_maximo", "data_fim"} & dados.keys():
            proxima = tarefa_atual.get("proxima_ocorrencia")
            if proxima:
                fim = self._data_fim_com_fuso(dados.get("data_fim", tarefa_atual["data_fim"]))
                tolerancia = dados.get("atraso_maximo", tarefa_atual["atraso_maximo"])
                janela = (self._data_fim_com_fuso(proxima) - fim).total_seconds()
                if tolerancia * 86400 >= janela:
                    raise HTTPException(
                        status_code=422,
                        detail="O prazo e a tolerância devem terminar antes da próxima ocorrência.",
                    )
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

        return self.buscar_tarefa(id_tarefa)

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

    def _creditar_pertencer(self, id_usuario: str, id_casa: str, pontos: int) -> int:
        for _ in range(_MAX_TENTATIVAS_CAS):
            atual = (
                self.supabase.table("pertencer")
                .select("score")
                .eq("fk_usuario_id", id_usuario)
                .eq("fk_casa_id", id_casa)
                .eq("ativo", True)
                .execute()
            )
            if not atual.data:
                raise HTTPException(
                    status_code=409,
                    detail="O responsável precisa ter vínculo de morador na casa.",
                )
            score_atual = atual.data[0]["score"]
            novo_score = score_atual + pontos
            resposta = (
                self.supabase.table("pertencer")
                .update({"score": novo_score})
                .eq("fk_usuario_id", id_usuario)
                .eq("fk_casa_id", id_casa)
                .eq("ativo", True)
                .eq("score", score_atual)  # CAS: só escreve se ninguém mexeu nesse meio-tempo
                .execute()
            )
            if resposta.data:
                return novo_score
        raise HTTPException(status_code=409, detail="Conflito ao creditar pontos, tente novamente.")

    def _finalizar_estado_tarefa(self, tarefa: dict, concluida_em: datetime) -> dict | None:
        resposta = (
            self.supabase.table("tarefa")
            .update({
                "estado_atual": "finalizado",
                "concluida_em": concluida_em.isoformat(),
            })
            .eq("id", str(tarefa["id"]))
            .in_("estado_atual", ["pendente", "atrasada"])
            .eq("dificuldade", tarefa["dificuldade"])
            .eq("atraso_maximo", tarefa["atraso_maximo"])
            .eq("data_fim", tarefa["data_fim"])
            .eq("data_inicio", tarefa.get("data_inicio"))
            .eq("fk_casa_id", tarefa["fk_casa_id"])
            .execute()
        )
        return resposta.data[0] if resposta.data else None

    def _creditar_e_finalizar(
        self, tarefa: dict, id_usuario: UUID, pontos: int, concluida_em: datetime,
    ) -> dict:
        id_usuario_str, id_casa_str = str(id_usuario), str(tarefa["fk_casa_id"])

        vinculo = (
            self.supabase.table("pertencer")
            .select("fk_usuario_id")
            .eq("fk_usuario_id", id_usuario_str)
            .eq("fk_casa_id", id_casa_str)
            .eq("ativo", True)
            .execute()
        )
        if not vinculo.data:
            raise HTTPException(
                status_code=409,
                detail="O responsável precisa ter vínculo de morador na casa.",
            )

        ja_creditado = False
        try:
            self.supabase.table("score_event").insert({
                "fk_usuario_id": id_usuario_str,
                "fk_casa_id": id_casa_str,
                "fk_tarefa_id": str(tarefa["id"]),
                "pontuacao": pontos,
                "criado_em": concluida_em.isoformat(),
                "ciclo": tarefa.get("reaberturas") or 0,
            }).execute()
        except APIError as erro:
            if erro.code != "23505":  # não é violação de UNIQUE — outro tipo de erro real
                raise
            ja_creditado = True

        if not ja_creditado:
            self._creditar_pertencer(id_usuario_str, id_casa_str, pontos)

        tarefa_finalizada = self._finalizar_estado_tarefa(tarefa, concluida_em)
        if tarefa_finalizada is None:
            raise HTTPException(
                status_code=409, detail="A tarefa mudou. Atualize antes de concluir."
            )
        return tarefa_finalizada

    def reabrir_tarefa(self, id_tarefa: UUID, id_usuario_atual: UUID):
        tarefa = self._buscar_tarefa_bruta(id_tarefa)
        responsaveis = self._buscar_usuarios_atribuidos(tarefa["id"])
        if str(id_usuario_atual) not in responsaveis:
            ServicoAutorizacaoCasa(self.supabase).garantir_administrador_da_casa(
                tarefa["fk_casa_id"], id_usuario_atual
            )
        if tarefa["estado_atual"] != "finalizado":
            raise HTTPException(
                status_code=409, detail="Só é possível reabrir uma tarefa finalizada."
            )
        if len(responsaveis) != 1:
            raise HTTPException(
                status_code=409,
                detail="A tarefa precisa ter exatamente um responsável para ser reaberta.",
            )
        vinculo = (
            self.supabase.table("pertencer")
            .select("fk_usuario_id")
            .eq("fk_usuario_id", responsaveis[0])
            .eq("fk_casa_id", str(tarefa["fk_casa_id"]))
            .eq("ativo", True)
            .execute()
        )
        if not vinculo.data:
            raise HTTPException(
                status_code=409,
                detail="Reative o vínculo do responsável antes de reabrir a tarefa.",
            )
        return self._estornar_e_reabrir(tarefa, responsaveis[0])

    def _estornar_e_reabrir(self, tarefa: dict, id_usuario: str) -> dict:
        id_casa = str(tarefa["fk_casa_id"])
        ciclo = tarefa.get("reaberturas") or 0
        credito = (
            self.supabase.table("score_event")
            .select("pontuacao")
            .eq("fk_usuario_id", id_usuario)
            .eq("fk_tarefa_id", str(tarefa["id"]))
            .eq("tipo", "credito")
            .eq("ciclo", ciclo)
            .execute()
        )
        if not credito.data:
            raise HTTPException(
                status_code=409, detail="A tarefa não tem crédito a estornar."
            )
        pontos = credito.data[0]["pontuacao"]

        ja_estornado = False
        try:
            self.supabase.table("score_event").insert({
                "fk_usuario_id": id_usuario,
                "fk_casa_id": id_casa,
                "fk_tarefa_id": str(tarefa["id"]),
                "pontuacao": -pontos,
                "tipo": "reversal",
                "ciclo": ciclo,
                "criado_em": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except APIError as erro:
            if erro.code != "23505":
                raise
            ja_estornado = True

        if not ja_estornado:
            self._creditar_pertencer(id_usuario, id_casa, -pontos)

        reaberta = self._reabrir_estado_tarefa(tarefa, ciclo)
        if reaberta is None:
            # Outra requisição reabriu a tarefa no meio-tempo: o resultado é o mesmo.
            atual = self._buscar_tarefa_bruta(UUID(tarefa["id"]))
            if (atual.get("reaberturas") or 0) <= ciclo:
                raise HTTPException(
                    status_code=409, detail="A tarefa mudou. Atualize antes de reabrir."
                )
            reaberta = atual
        return self._montar_resposta(reaberta)

    def _reabrir_estado_tarefa(self, tarefa: dict, ciclo: int) -> dict | None:
        agora = datetime.now(timezone.utc)
        data_fim = self._data_fim_com_fuso(tarefa["data_fim"])
        dias_atraso = ServicoScore.calcular_dias_atraso(data_fim, agora)
        if dias_atraso > tarefa["atraso_maximo"]:
            estado = "nao_feito"
        elif dias_atraso > 0:
            estado = "atrasada"
        else:
            estado = "pendente"
        resposta = (
            self.supabase.table("tarefa")
            .update({
                "estado_atual": estado,
                "concluida_em": None,
                "reaberturas": ciclo + 1,
            })
            .eq("id", str(tarefa["id"]))
            .eq("estado_atual", "finalizado")
            .eq("reaberturas", ciclo)
            .execute()
        )
        return resposta.data[0] if resposta.data else None

    def _buscar_saldo(self, id_usuario: str, id_casa: str) -> int:
        resposta = (
            self.supabase.table("pertencer")
            .select("score")
            .eq("fk_usuario_id", id_usuario)
            .eq("fk_casa_id", id_casa)
            .execute()
        )
        return resposta.data[0]["score"] if resposta.data else 0

