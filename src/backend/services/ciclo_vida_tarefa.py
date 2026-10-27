from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from postgrest.exceptions import APIError

from services.score import ServicoScore

ESTADOS_ABERTOS = ("pendente", "atrasada")
ESTADOS_FINAIS = ("finalizado", "nao_feito")
_MAX_TENTATIVAS_CAS = 5


def instante_utc(valor: str | datetime) -> datetime:
    instante = datetime.fromisoformat(valor) if isinstance(valor, str) else valor
    if instante.tzinfo is None or instante.utcoffset() is None:
        return instante.replace(tzinfo=timezone.utc)
    return instante.astimezone(timezone.utc)


def estado_no_prazo(tarefa: dict, agora: datetime) -> str:
    dias_atraso = ServicoScore.calcular_dias_atraso(
        instante_utc(tarefa["data_fim"]), instante_utc(agora),
    )
    if dias_atraso > tarefa["atraso_maximo"]:
        return "nao_feito"
    return "atrasada" if dias_atraso else "pendente"


def janela_dia_fixo(
    data_fixa: date, prazo_dias: int, fuso: ZoneInfo,
) -> tuple[datetime, datetime]:
    vencimento = datetime.combine(data_fixa, time.max, tzinfo=fuso).astimezone(timezone.utc)
    return vencimento - timedelta(days=prazo_dias), vencimento


def corresponde_prazo(
    tarefa: dict, filtro: str | None, agora: datetime, fuso: ZoneInfo | None,
) -> bool:
    if not filtro or filtro == "todos":
        return True
    vencimento = instante_utc(tarefa["data_fim"])
    agora = instante_utc(agora)
    if filtro == "atrasadas":
        return vencimento < agora and tarefa["estado_atual"] != "finalizado"
    dia_prazo = vencimento.astimezone(fuso).date()
    hoje = agora.astimezone(fuso).date()
    if filtro == "antigas":
        return dia_prazo < hoje
    if dia_prazo < hoje and tarefa["estado_atual"] in ESTADOS_ABERTOS:
        return filtro in ("hoje", "sete_dias")
    if filtro == "hoje":
        return dia_prazo == hoje
    return filtro == "sete_dias" and hoje <= dia_prazo <= hoje + timedelta(days=6)


def atualizar_prazo(
    tarefa: dict, dados: dict, fuso: ZoneInfo | None, agora: datetime,
) -> dict:
    dados = dict(dados)
    data_fixa = dados.pop("data_fixa", None)
    modo = tarefa.get("modo_prazo") or "intervalo"
    if data_fixa is not None and modo != "dia_fixo":
        raise HTTPException(status_code=422, detail="Esta tarefa não usa dia fixo.")
    if modo == "dia_fixo" and ("prazo_dias" in dados or data_fixa is not None):
        dia = (
            date.fromisoformat(data_fixa) if data_fixa
            else instante_utc(tarefa["data_fim"]).astimezone(fuso).date()
        )
        prazo = dados.get("prazo_dias", tarefa.get("prazo_dias"))
        if prazo is None:
            raise HTTPException(
                status_code=409,
                detail="Defina prazo_dias para editar o vencimento desta tarefa legada.",
            )
        inicio, vencimento = janela_dia_fixo(dia, prazo, fuso)
        if vencimento <= instante_utc(agora):
            raise HTTPException(status_code=422, detail="A data fixa deve estar no futuro.")
        dados.update(data_inicio=inicio.isoformat(), data_fim=vencimento.isoformat())
        if not tarefa.get("timezone"):
            dados["timezone"] = fuso.key
    elif "prazo_dias" in dados:
        inicio = tarefa.get("data_inicio") or tarefa.get("criado_em")
        if inicio is None:
            raise HTTPException(
                status_code=409,
                detail="A tarefa legada não possui referência de início do prazo.",
            )
        vencimento = instante_utc(inicio) + timedelta(days=dados["prazo_dias"])
        if vencimento <= instante_utc(agora):
            raise HTTPException(status_code=422, detail="O novo prazo deve estar no futuro.")
        dados["data_fim"] = vencimento.isoformat()
    if {"prazo_dias", "atraso_maximo", "data_fim"} & dados.keys():
        proxima = tarefa.get("proxima_ocorrencia")
        if proxima:
            fim = instante_utc(dados.get("data_fim", tarefa["data_fim"]))
            tolerancia = dados.get("atraso_maximo", tarefa["atraso_maximo"])
            if fim + timedelta(days=tolerancia) >= instante_utc(proxima):
                raise HTTPException(
                    status_code=422,
                    detail="O prazo e a tolerância devem terminar antes da próxima ocorrência.",
                )
    return dados


class ServicoCicloVidaTarefa:
    def __init__(self, supabase, notificacoes):
        self.supabase = supabase
        self.notificacoes = notificacoes

    def sincronizar_estado(self, tarefa: dict, agora: datetime) -> dict | None:
        if tarefa["estado_atual"] in ESTADOS_FINAIS:
            return tarefa
        estado = estado_no_prazo(tarefa, agora)
        if estado == tarefa["estado_atual"]:
            return tarefa
        resposta = (
            self.supabase.table("tarefa")
            .update({"estado_atual": estado})
            .eq("id", str(tarefa["id"]))
            .eq("estado_atual", tarefa["estado_atual"])
            .eq("data_fim", tarefa["data_fim"])
            .eq("atraso_maximo", tarefa["atraso_maximo"])
            .execute()
        )
        if not resposta.data:
            return None
        atualizada = resposta.data[0]
        if estado == "nao_feito":
            self.notificacoes.notificar_tarefa("prazo_encerrado", atualizada)
        return atualizada

    def concluir(self, tarefa: dict, responsaveis: list[str], agora: datetime) -> dict:
        inicio = tarefa.get("data_inicio")
        if inicio and instante_utc(inicio) > instante_utc(agora):
            raise HTTPException(status_code=409, detail="Esta ocorrência ainda não começou.")
        if tarefa["estado_atual"] in ESTADOS_FINAIS:
            raise HTTPException(
                status_code=409,
                detail="Uma tarefa encerrada não pode ser alterada ou finalizada novamente.",
            )
        if len(responsaveis) != 1:
            raise HTTPException(
                status_code=409,
                detail="A tarefa precisa ter exatamente um responsável antes da conclusão.",
            )
        agora = instante_utc(agora)
        resultado = ServicoScore().calcular_score(
            peso=tarefa["dificuldade"], atraso_maximo=tarefa["atraso_maximo"],
            data_fim=instante_utc(tarefa["data_fim"]), concluida_em=agora,
            usuarios_atribuidos=[UUID(responsaveis[0])],
        )
        if resultado.dias_atraso > tarefa["atraso_maximo"]:
            raise HTTPException(status_code=409, detail="A tolerância de atraso foi ultrapassada.")
        id_usuario = str(resultado.usuario_id)
        id_casa = str(tarefa["fk_casa_id"])
        self._garantir_vinculo(
            id_usuario, id_casa, "O responsável precisa ter vínculo de morador na casa.",
        )
        self._registrar_movimentacao(tarefa, id_usuario, resultado.pontos_finais, "credito", agora)
        resposta = (
            self.supabase.table("tarefa")
            .update({"estado_atual": "finalizado", "concluida_em": agora.isoformat()})
            .eq("id", str(tarefa["id"]))
            .in_("estado_atual", ESTADOS_ABERTOS)
            .eq("dificuldade", tarefa["dificuldade"])
            .eq("atraso_maximo", tarefa["atraso_maximo"])
            .eq("data_fim", tarefa["data_fim"])
            .eq("data_inicio", tarefa.get("data_inicio"))
            .eq("fk_casa_id", tarefa["fk_casa_id"])
            .eq("reaberturas", tarefa.get("reaberturas") or 0)
            .execute()
        )
        if not resposta.data:
            raise HTTPException(
                status_code=409, detail="A tarefa mudou. Atualize antes de concluir.",
            )
        saldo = (
            self.supabase.table("pertencer").select("score")
            .eq("fk_usuario_id", id_usuario).eq("fk_casa_id", id_casa).execute()
        ).data
        return {
            **resposta.data[0],
            "resultado_pontuacao": {
                "pontos_possiveis": tarefa["pontuacao"],
                "pontos_ganhos": resultado.pontos_finais,
                "saldo_atual": saldo[0]["score"] if saldo else 0,
            },
        }

    def reabrir(self, tarefa: dict, responsaveis: list[str], agora: datetime) -> dict:
        if tarefa["estado_atual"] != "finalizado":
            raise HTTPException(
                status_code=409, detail="Só é possível reabrir uma tarefa finalizada.",
            )
        if len(responsaveis) != 1:
            raise HTTPException(
                status_code=409,
                detail="A tarefa precisa ter exatamente um responsável para ser reaberta.",
            )
        id_usuario, id_casa = responsaveis[0], str(tarefa["fk_casa_id"])
        self._garantir_vinculo(
            id_usuario, id_casa, "Reative o vínculo do responsável antes de reabrir a tarefa.",
        )
        ciclo = tarefa.get("reaberturas") or 0
        credito = (
            self.supabase.table("score_event").select("pontuacao")
            .eq("fk_usuario_id", id_usuario).eq("fk_tarefa_id", str(tarefa["id"]))
            .eq("tipo", "credito").eq("ciclo", ciclo).execute()
        ).data
        if not credito:
            raise HTTPException(status_code=409, detail="A tarefa não tem crédito a estornar.")
        self._registrar_movimentacao(
            tarefa, id_usuario, -credito[0]["pontuacao"], "reversal", agora,
        )
        resposta = (
            self.supabase.table("tarefa")
            .update({
                "estado_atual": estado_no_prazo(tarefa, agora),
                "concluida_em": None, "reaberturas": ciclo + 1,
            })
            .eq("id", str(tarefa["id"]))
            .eq("estado_atual", "finalizado").eq("reaberturas", ciclo).execute()
        )
        if resposta.data:
            return resposta.data[0]
        atual = (
            self.supabase.table("tarefa").select("*").eq("id", str(tarefa["id"])).execute()
        ).data
        if not atual:
            raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
        if (atual[0].get("reaberturas") or 0) <= ciclo:
            raise HTTPException(
                status_code=409, detail="A tarefa mudou. Atualize antes de reabrir.",
            )
        return atual[0]

    def _garantir_vinculo(self, id_usuario: str, id_casa: str, mensagem: str) -> None:
        vinculo = (
            self.supabase.table("pertencer").select("fk_usuario_id")
            .eq("fk_usuario_id", id_usuario).eq("fk_casa_id", id_casa)
            .eq("ativo", True).execute()
        ).data
        if not vinculo:
            raise HTTPException(status_code=409, detail=mensagem)

    def _registrar_movimentacao(
        self, tarefa: dict, id_usuario: str, pontos: int, tipo: str, agora: datetime,
    ) -> None:
        # shortcut: evento e saldo usam escritas separadas; retomada após queda exige atomicidade.
        try:
            self.supabase.table("score_event").insert({
                "fk_usuario_id": id_usuario, "fk_casa_id": str(tarefa["fk_casa_id"]),
                "fk_tarefa_id": str(tarefa["id"]), "pontuacao": pontos, "tipo": tipo,
                "criado_em": instante_utc(agora).isoformat(),
                "ciclo": tarefa.get("reaberturas") or 0,
            }).execute()
        except APIError as erro:
            if erro.code != "23505":
                raise
            return
        self._ajustar_saldo(id_usuario, str(tarefa["fk_casa_id"]), pontos)

    def _ajustar_saldo(self, id_usuario: str, id_casa: str, pontos: int) -> None:
        for _ in range(_MAX_TENTATIVAS_CAS):
            atual = (
                self.supabase.table("pertencer").select("score")
                .eq("fk_usuario_id", id_usuario).eq("fk_casa_id", id_casa)
                .eq("ativo", True).execute()
            ).data
            if not atual:
                raise HTTPException(
                    status_code=409,
                    detail="O responsável precisa ter vínculo de morador na casa.",
                )
            saldo = atual[0]["score"]
            resposta = (
                self.supabase.table("pertencer").update({"score": saldo + pontos})
                .eq("fk_usuario_id", id_usuario).eq("fk_casa_id", id_casa)
                .eq("ativo", True).eq("score", saldo).execute()
            )
            if resposta.data:
                return
        raise HTTPException(status_code=409, detail="Conflito ao creditar pontos, tente novamente.")
