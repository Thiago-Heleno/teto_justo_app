from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from services.penalidade import ServicoPenalidade


class Consulta:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.filtros = []
        self.estados = None
        self.atualizacao = None

    def select(self, _campos):
        return self

    def in_(self, campo, valores):
        self.estados = (campo, set(valores))
        return self

    def order(self, _campo):
        return self

    def range(self, inicio, fim):
        self.intervalo = (inicio, fim)
        return self

    def update(self, dados):
        self.atualizacao = dados
        return self

    def eq(self, campo, valor):
        self.filtros.append((campo, valor))
        return self

    def execute(self):
        if self.atualizacao is None:
            tarefas = [
                tarefa for tarefa in self.banco.tarefas
                if self.estados is None or tarefa[self.estados[0]] in self.estados[1]
            ]
            inicio, fim = self.intervalo
            return SimpleNamespace(data=tarefas[inicio : fim + 1])

        tarefa_atual = next(
            (
                tarefa for tarefa in self.banco.tarefas
                if all(str(tarefa.get(campo)) == str(valor) for campo, valor in self.filtros)
            ),
            None,
        )
        if self.banco.antes_de_atualizar:
            self.banco.antes_de_atualizar(tarefa_atual)
        if tarefa_atual is None or any(
            str(tarefa_atual.get(campo)) != str(valor) for campo, valor in self.filtros
        ):
            return SimpleNamespace(data=[])
        tarefa_atual.update(self.atualizacao)
        return SimpleNamespace(data=[tarefa_atual])


class Banco:
    def __init__(self, tarefas, antes_de_atualizar=None):
        self.tarefas = tarefas
        self.antes_de_atualizar = antes_de_atualizar
        self.tabelas_consultadas = []

    def table(self, nome):
        self.tabelas_consultadas.append(nome)
        if nome != "tarefa":
            raise AssertionError(f"Tabela inesperada: {nome}")
        return Consulta(self, nome)


@pytest.fixture
def agora():
    return datetime(2026, 9, 29, 12, tzinfo=timezone.utc)


def tarefa(estado, data_fim, atraso_maximo=2):
    return {
        "id": str(uuid4()),
        "estado_atual": estado,
        "data_fim": data_fim.isoformat(),
        "atraso_maximo": atraso_maximo,
    }


def test_processa_prazo_atraso_e_limite_da_penalidade(agora):
    no_prazo = tarefa("pendente", agora)
    atrasada = tarefa("pendente", agora - timedelta(days=2))
    tolerancia_excedida = tarefa("atrasada", agora - timedelta(days=3))
    banco = Banco([no_prazo, atrasada, tolerancia_excedida])

    resultado = ServicoPenalidade(banco).processar_tarefas(agora)

    assert no_prazo["estado_atual"] == "pendente"
    assert atrasada["estado_atual"] == "atrasada"
    assert tolerancia_excedida["estado_atual"] == "nao_feito"
    assert resultado == {
        "tarefas_analisadas": 3,
        "marcadas_atrasadas": 1,
        "marcadas_nao_feitas": 1,
    }
    assert banco.tabelas_consultadas == ["tarefa"] * 3


def test_processamento_repetido_nao_repete_transicoes_ou_eventos(agora):
    tarefa_atrasada = tarefa("pendente", agora - timedelta(days=1), atraso_maximo=5)
    banco = Banco([tarefa_atrasada])
    servico = ServicoPenalidade(banco)

    primeira = servico.processar_tarefas(agora)
    segunda = servico.processar_tarefas(agora)

    assert primeira["marcadas_atrasadas"] == 1
    assert segunda["marcadas_atrasadas"] == 0
    assert tarefa_atrasada["estado_atual"] == "atrasada"
    assert "score_event" not in banco.tabelas_consultadas


def test_transicao_condicional_nao_sobrescreve_tarefa_alterada(agora):
    registro = tarefa("pendente", agora - timedelta(days=1))
    banco = Banco(
        [registro],
        antes_de_atualizar=lambda tarefa_atual: tarefa_atual.update(
            {"estado_atual": "finalizado"}
        ),
    )
    servico = ServicoPenalidade(banco)

    resultado = servico.processar_tarefas(agora)

    assert resultado["marcadas_atrasadas"] == 0
    assert registro["estado_atual"] == "finalizado"
