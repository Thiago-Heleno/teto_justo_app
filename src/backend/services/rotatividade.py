"""Agenda semanal e distribuição de pontos possíveis das tarefas rotativas."""

import logging
from datetime import date, datetime, time, timedelta, timezone
from threading import Event
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from postgrest.exceptions import APIError

from schemas.rotatividade import RotatividadeCriar
from services.autorizacao import ServicoAutorizacaoCasa
from services.score import ServicoScore
from services.tarefa import ServicoTarefa


log = logging.getLogger(__name__)


def _utc(valor: str | datetime) -> datetime:
    if isinstance(valor, str):
        valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    if valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(timezone.utc)


def _inicio_semana(dia: date) -> date:
    return dia - timedelta(days=dia.weekday())


def semana_ancora(
    dias_semana: list[int], modo_prazo: str, prazo_dias: int,
    fuso: ZoneInfo, agora: datetime,
) -> date:
    semana = _inicio_semana(agora.astimezone(fuso).date())
    for dia_semana in dias_semana:
        dia = semana + timedelta(days=dia_semana - 1)
        if modo_prazo == "dia_fixo":
            _, slot = ServicoTarefa.janela_dia_fixo(dia, prazo_dias, fuso)
        else:
            slot = datetime.combine(dia, time.min, tzinfo=fuso).astimezone(timezone.utc)
        if slot >= agora:
            return semana
    return semana + timedelta(weeks=1)


def _mes_local(ocorrencia: datetime, fuso: ZoneInfo) -> tuple[datetime, datetime]:
    local = ocorrencia.astimezone(fuso)
    inicio = datetime(local.year, local.month, 1, tzinfo=fuso)
    if local.month == 12:
        fim = datetime(local.year + 1, 1, 1, tzinfo=fuso)
    else:
        fim = datetime(local.year, local.month + 1, 1, tzinfo=fuso)
    return inicio.astimezone(timezone.utc), fim.astimezone(timezone.utc)


def escolher_responsavel(participantes: list[dict], potenciais: dict[str, int]) -> str:
    """Escolhe o menor potencial mensal; a ordem configurada decide empates."""
    if not participantes:
        raise ValueError("O rodízio precisa de participantes.")
    escolhido = min(
        participantes,
        key=lambda item: (potenciais.get(str(item["fk_usuario_id"]), 0), item["ordem"]),
    )
    return str(escolhido["fk_usuario_id"])


def gerar_janelas(configuracao: dict, fuso: ZoneInfo, agora: datetime):
    """Produz slots abertos, incluindo slots perdidos durante uma parada do worker."""
    criado_em = _utc(configuracao["criado_em"])
    ancora = _inicio_semana(date.fromisoformat(configuracao["semana_ancora"]))
    horizonte = agora.astimezone(fuso).date()
    if configuracao["modo_prazo"] == "dia_fixo":
        horizonte += timedelta(days=configuracao["prazo_dias"] + 1)
    semana = ancora
    while semana <= horizonte:
        for dia_semana in sorted(configuracao["dias_semana"]):
            data_slot = semana + timedelta(days=dia_semana - 1)
            if data_slot > horizonte:
                continue
            if configuracao["modo_prazo"] == "dia_fixo":
                inicio, vencimento = ServicoTarefa.janela_dia_fixo(
                    data_slot, configuracao["prazo_dias"], fuso
                )
                slot = vencimento
            else:
                inicio = datetime.combine(data_slot, time.min, tzinfo=fuso).astimezone(timezone.utc)
                vencimento = inicio + timedelta(days=configuracao["prazo_dias"])
                slot = inicio
            if slot >= criado_em and inicio <= agora:
                yield slot, inicio, vencimento
        semana += timedelta(weeks=configuracao["intervalo_semanas"])


class ServicoRotatividade:
    def __init__(self, cliente_supabase):
        self.supabase = cliente_supabase

    @staticmethod
    def _listar_paginas(montar_consulta) -> list[dict]:
        registros = []
        inicio = 0
        while True:
            lote = montar_consulta().range(inicio, inicio + 499).execute().data
            registros.extend(lote)
            if len(lote) < 500:
                return registros
            inicio += 500

    def _casa(self, id_casa: UUID | str) -> dict:
        resposta = (
            self.supabase.table("casa")
            .select("id,fk_usuario_id,timezone,rotacao_versao")
            .eq("id", str(id_casa))
            .execute()
        )
        if not resposta.data:
            raise HTTPException(status_code=404, detail="Casa não encontrada.")
        return resposta.data[0]

    def _garantir_acesso(self, casa: dict, id_usuario: UUID | str):
        if str(casa["fk_usuario_id"]) == str(id_usuario):
            return
        vinculo = (
            self.supabase.table("pertencer")
            .select("fk_usuario_id")
            .eq("fk_casa_id", casa["id"])
            .eq("fk_usuario_id", str(id_usuario))
            .execute()
        )
        if not vinculo.data:
            raise HTTPException(status_code=403, detail="Acesso à casa negado.")

    def criar(self, dados: RotatividadeCriar, id_usuario: UUID) -> dict:
        ServicoAutorizacaoCasa(self.supabase).garantir_administrador_da_casa(
            dados.fk_casa_id, id_usuario
        )
        ServicoAutorizacaoCasa(self.supabase).garantir_responsaveis_da_casa(
            dados.fk_casa_id, dados.participantes
        )
        for _ in range(3):
            casa = self._casa(dados.fk_casa_id)
            fuso = ZoneInfo(casa["timezone"])
            agora = datetime.now(timezone.utc)
            config = dados.model_dump(mode="json", exclude={"participantes", "peso"})
            config.update({
                "fk_usuario_id": str(id_usuario),
                "dificuldade": dados.peso,
                "pontuacao": ServicoScore.pontos_por_peso(dados.peso),
                "timezone_esperado": casa["timezone"],
                "semana_ancora": semana_ancora(
                    dados.dias_semana, dados.modo_prazo, dados.prazo_dias, fuso, agora
                ).isoformat(),
            })
            try:
                resposta = self.supabase.rpc("criar_rotatividade", {
                    "p_config": config,
                    "p_participantes": [str(participante) for participante in dados.participantes],
                }).execute()
            except APIError as erro:
                if erro.code == "PT409" and "fuso" in erro.message.lower():
                    continue
                if erro.code == "PT409":
                    raise HTTPException(status_code=409, detail=erro.message) from erro
                raise
            if not resposta.data:
                raise HTTPException(status_code=500, detail="Não foi possível criar o rodízio.")
            return self._montar_resposta(resposta.data, dados.participantes)
        raise HTTPException(status_code=409, detail="O fuso da casa mudou; tente novamente.")

    @staticmethod
    def _montar_resposta(configuracao: dict, participantes: list[UUID | str]) -> dict:
        return {
            "id": configuracao["id"],
            "fk_casa_id": configuracao["fk_casa_id"],
            "nome": configuracao["nome"],
            "descricao": configuracao.get("descricao"),
            "peso": configuracao["dificuldade"],
            "pontuacao": configuracao["pontuacao"],
            "prazo_dias": configuracao["prazo_dias"],
            "atraso_maximo": configuracao["atraso_maximo"],
            "modo_prazo": configuracao["modo_prazo"],
            "participantes": participantes,
            "dias_semana": configuracao["dias_semana"],
            "intervalo_semanas": configuracao["intervalo_semanas"],
            "semana_ancora": configuracao["semana_ancora"],
            "ativa": configuracao["ativa"],
            "criado_em": configuracao["criado_em"],
        }

    def _buscar(self, id_rotatividade: UUID) -> dict:
        resposta = (
            self.supabase.table("rotatividade")
            .select("*")
            .eq("id", str(id_rotatividade))
            .execute()
        )
        if not resposta.data:
            raise HTTPException(status_code=404, detail="Rodízio não encontrado.")
        return resposta.data[0]

    def listar_ocorrencias(self, id_rotatividade: UUID, id_usuario: UUID) -> list[dict]:
        config = self._buscar(id_rotatividade)
        self._garantir_acesso(self._casa(config["fk_casa_id"]), id_usuario)
        tarefas = self._listar_paginas(
            lambda: self.supabase.table("tarefa")
            .select("*")
            .eq("rotatividade_id", str(id_rotatividade))
            .order("ocorrencia_em")
        )
        servico_tarefa = ServicoTarefa(self.supabase)
        return [servico_tarefa._montar_resposta(tarefa) for tarefa in tarefas]

    def _potenciais_mes(
        self, casa: dict, slot: datetime, participantes: list[dict]
    ) -> dict[str, int]:
        inicio, fim = _mes_local(slot, ZoneInfo(casa["timezone"]))
        tarefas = self._listar_paginas(
            lambda: self.supabase.table("tarefa")
            .select("id,pontuacao")
            .eq("fk_casa_id", casa["id"])
            .not_.is_("rotatividade_id", "null")
            .gte("ocorrencia_em", inicio.isoformat())
            .lt("ocorrencia_em", fim.isoformat())
            .order("ocorrencia_em")
            .order("id")
        )
        pontos = {str(tarefa["id"]): tarefa["pontuacao"] for tarefa in tarefas}
        potenciais = {str(item["fk_usuario_id"]): 0 for item in participantes}
        ids = list(pontos)
        for indice in range(0, len(ids), 100):
            atribuicoes = (
                self.supabase.table("atribuida")
                .select("fk_tarefa_id,fk_usuario_id")
                .in_("fk_tarefa_id", ids[indice:indice + 100])
                .execute()
            ).data
            for atribuicao in atribuicoes:
                usuario = str(atribuicao["fk_usuario_id"])
                if usuario in potenciais:
                    potenciais[usuario] += pontos[str(atribuicao["fk_tarefa_id"])]
        return potenciais

    def _registrar(self, config: dict, participantes: list[dict], slot: datetime,
                   inicio: datetime, vencimento: datetime) -> dict:
        for _ in range(5):
            casa = self._casa(config["fk_casa_id"])
            potenciais = self._potenciais_mes(casa, slot, participantes)
            escolhido = escolher_responsavel(participantes, potenciais)
            try:
                resposta = self.supabase.rpc("registrar_ocorrencia_rotativa", {
                    "p_id_rotatividade": config["id"],
                    "p_ocorrencia_em": slot.isoformat(),
                    "p_data_inicio": inicio.isoformat(),
                    "p_data_fim": vencimento.isoformat(),
                    "p_id_usuario": escolhido,
                    "p_versao_casa": casa["rotacao_versao"],
                }).execute()
            except APIError as erro:
                if erro.code == "PT409" and "Recalcule" in erro.message:
                    continue
                if erro.code == "PT409":
                    raise HTTPException(status_code=409, detail=erro.message) from erro
                raise
            if not resposta.data:
                raise HTTPException(
                    status_code=500, detail="Não foi possível registrar ocorrência."
                )
            return resposta.data
        raise HTTPException(status_code=409, detail="Rodízio ocupado; tente processar novamente.")

    def processar_pendentes(
        self, agora: datetime | None = None, id_rotatividade: UUID | str | None = None
    ) -> int:
        agora = agora or datetime.now(timezone.utc)
        def consulta_configuracoes():
            consulta = self.supabase.table("rotatividade").select("*").eq("ativa", True)
            if id_rotatividade is not None:
                consulta = consulta.eq("id", str(id_rotatividade))
            return consulta.order("id")

        configuracoes = self._listar_paginas(
            consulta_configuracoes
        )
        criadas = 0
        janelas_pendentes = []
        for config in configuracoes:
            fuso = ZoneInfo(config["timezone"])
            participantes = self._listar_paginas(
                lambda: self.supabase.table("rotatividade_participante")
                .select("fk_usuario_id,ordem")
                .eq("fk_rotatividade_id", config["id"])
                .order("ordem")
            )
            moradores = {
                str(item["fk_usuario_id"])
                for item in self._listar_paginas(
                    lambda: self.supabase.table("pertencer")
                    .select("fk_usuario_id")
                    .eq("fk_casa_id", config["fk_casa_id"])
                    .order("fk_usuario_id")
                )
            }
            participantes = [
                item for item in participantes
                if str(item["fk_usuario_id"]) in moradores
            ]
            if not participantes:
                log.warning("Rodízio %s sem participantes elegíveis", config["id"])
                continue
            existentes = {
                _utc(item["ocorrencia_em"])
                for item in self._listar_paginas(
                    lambda: self.supabase.table("tarefa")
                    .select("ocorrencia_em")
                    .eq("rotatividade_id", config["id"])
                    .order("ocorrencia_em")
                )
            }
            for slot, inicio, vencimento in gerar_janelas(config, fuso, agora):
                if slot in existentes:
                    continue
                janelas_pendentes.append(
                    (slot, config["id"], config, participantes, inicio, vencimento)
                )
        servico_tarefa = ServicoTarefa(self.supabase)
        for slot, _, config, participantes, inicio, vencimento in sorted(janelas_pendentes):
            tarefa = self._registrar(config, participantes, slot, inicio, vencimento)
            criadas += 1
            servico_tarefa._sincronizar_estado_por_atraso(tarefa)
        def consulta_pendentes():
            consulta = (
                self.supabase.table("tarefa")
                .select("*")
                .not_.is_("rotatividade_id", "null")
                .in_("estado_atual", ["pendente", "atrasada"])
            )
            if id_rotatividade is not None:
                consulta = consulta.eq("rotatividade_id", str(id_rotatividade))
            return consulta.order("id")

        pendentes = self._listar_paginas(consulta_pendentes)
        for tarefa in pendentes:
            servico_tarefa._sincronizar_estado_por_atraso(tarefa)
        return criadas


def executar_worker(intervalo_segundos: int = 60) -> None:
    from core.database import get_supabase

    parada = Event()
    servico = ServicoRotatividade(get_supabase())
    while not parada.is_set():
        try:
            servico.processar_pendentes()
        except Exception:
            log.exception("Falha ao processar ocorrências rotativas")
        parada.wait(intervalo_segundos)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executar_worker()
