from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from schemas.rotatividade import RotatividadeCriar
from services.rotatividade_agendamento import (
    ServicoAgendamentoRotatividade,
    data_local_ocorrencia,
    datas_ocorrencias,
)


def test_datas_ocorrencias_respeitam_dia_inicial_e_intervalo_de_semanas():
    configuracao = {
        "semana_ancora": "2026-09-30",
        "dias_semana": [1, 3, 5],
        "intervalo_semanas": 2,
    }

    assert datas_ocorrencias(configuracao, date(2026, 10, 14)) == [
        date(2026, 9, 30),
        date(2026, 10, 2),
        date(2026, 10, 12),
        date(2026, 10, 14),
    ]


def test_data_de_ocorrencia_sem_fuso_e_interpretada_como_utc():
    assert data_local_ocorrencia(
        "2026-10-01T02:00:00",
        ZoneInfo("America/Sao_Paulo"),
    ) == date(2026, 9, 30)


def test_cria_configuracao_e_participantes_com_escritas_diretas(monkeypatch):
    id_casa = uuid4()
    id_admin = uuid4()
    participantes = [uuid4(), uuid4()]
    configuracao = {
        "id": str(uuid4()),
        "fk_casa_id": str(id_casa),
        "nome": "Limpar cozinha",
        "ativa": True,
    }
    consulta = MagicMock()
    consulta.select.return_value = consulta
    consulta.eq.return_value = consulta
    consulta.insert.return_value = consulta
    consulta.execute.side_effect = [
        SimpleNamespace(data=[{"timezone": "UTC"}]),
        SimpleNamespace(data=[configuracao]),
        SimpleNamespace(data=[{}, {}]),
    ]
    banco = MagicMock()
    banco.table.return_value = consulta

    class AutorizacaoFalsa:
        def __init__(self, _supabase):
            pass

        def garantir_administrador_da_casa(self, *_args):
            return id_admin

        def garantir_responsaveis_da_casa(self, *_args):
            return None

    monkeypatch.setattr(
        "services.rotatividade_agendamento.ServicoAutorizacaoCasa",
        AutorizacaoFalsa,
    )
    dados = RotatividadeCriar(
        fk_casa_id=id_casa,
        nome="Limpar cozinha",
        peso=2,
        prazo_dias=3,
        atraso_maximo=2,
        participantes=participantes,
        dias_semana=[1],
        intervalo_semanas=1,
    )

    resultado = ServicoAgendamentoRotatividade(banco).criar_rotatividade(
        dados,
        id_admin,
    )

    assert resultado == configuracao
    configuracao_gravada = consulta.insert.call_args_list[0].args[0]
    participantes_gravados = consulta.insert.call_args_list[1].args[0]
    assert configuracao_gravada["fk_usuario_id"] == str(id_admin)
    assert configuracao_gravada["timezone"] == "UTC"
    assert participantes_gravados == [
        {
            "fk_rotatividade_id": configuracao["id"],
            "fk_usuario_id": str(usuario_id),
            "ordem": ordem,
        }
        for ordem, usuario_id in enumerate(participantes, start=1)
    ]
    banco.rpc.assert_not_called()


class ConsultaFalsa:
    def __init__(self, banco, tabela):
        self.banco = banco
        self.tabela = tabela
        self.filtros = {}
        self.dados_insercao = None

    def select(self, _campos):
        return self

    def eq(self, campo, valor):
        self.filtros[campo] = valor
        return self

    def in_(self, campo, valores):
        self.filtros[campo] = set(valores)
        return self

    def order(self, _campo):
        return self

    def range(self, _inicio, _fim):
        return self

    def insert(self, dados):
        self.dados_insercao = dados
        return self

    def execute(self):
        registros = self.banco.registros[self.tabela]
        if self.dados_insercao is not None:
            dados = self.dados_insercao
            if isinstance(dados, dict):
                dados = [dados]
            inseridos = []
            for entrada in dados:
                registro = dict(entrada)
                registro.setdefault("id", str(uuid4()))
                registros.append(registro)
                inseridos.append(registro)
            return SimpleNamespace(data=inseridos)
        encontrados = [
            registro
            for registro in registros
            if all(
                registro.get(campo) in valor
                if isinstance(valor, set)
                else str(registro.get(campo)) == str(valor)
                for campo, valor in self.filtros.items()
            )
        ]
        return SimpleNamespace(data=encontrados)


class BancoFalso:
    def __init__(self):
        self.registros = {"tarefa": [], "atribuida": []}

    def table(self, tabela):
        return ConsultaFalsa(self, tabela)

    def rpc(self, *_args, **_kwargs):
        raise AssertionError("O serviço não deve chamar funções do banco.")


def test_registra_ocorrencia_com_responsavel_escolhido_pelo_balanceador():
    banco = BancoFalso()
    servico = ServicoAgendamentoRotatividade(banco)
    membros = (uuid4(), uuid4())
    configuracao = {
        "id": str(uuid4()),
        "fk_casa_id": str(uuid4()),
        "fk_usuario_id": str(uuid4()),
        "timezone": "UTC",
        "nome": "Limpar cozinha",
        "descricao": None,
        "dificuldade": 2,
        "pontuacao": 25,
        "prazo_dias": 3,
        "atraso_maximo": 2,
        "modo_prazo": "intervalo",
    }

    servico._registrar_ocorrencia(configuracao, date(2026, 10, 1), membros)

    tarefa = banco.registros["tarefa"][0]
    atribuicao = banco.registros["atribuida"][0]
    assert tarefa["tipo"] == "rotativa"
    assert tarefa["rotatividade_id"] == configuracao["id"]
    assert tarefa["data_inicio"] == "2026-10-01T00:00:00+00:00"
    assert atribuicao["fk_tarefa_id"] == tarefa["id"]
    assert UUID(atribuicao["fk_usuario_id"]) == membros[0]
