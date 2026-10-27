"""Envio manual com banco somente de leitura e Expo simulado."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from schemas.notificacao import NotificacaoTesteEntrada
from services.notificacao import ServicoNotificacao
from services.notificacao_teste import enviar_notificacao_teste


class BancoLeitura:
    def __init__(self, registros):
        self.registros = registros

    def table(self, tabela):
        return ConsultaLeitura(self.registros[tabela])


class ConsultaLeitura:
    def __init__(self, registros):
        self.registros = deepcopy(registros)

    def select(self, _campos):
        return self

    def eq(self, campo, valor):
        self.registros = [r for r in self.registros if r[campo] == valor]
        return self

    def limit(self, limite):
        self.registros = self.registros[:limite]
        return self

    def execute(self):
        return SimpleNamespace(data=self.registros)


@pytest.fixture
def ambiente(monkeypatch):
    usuario, tarefa, casa = uuid4(), uuid4(), uuid4()
    registros = {
        "tarefa": [{"id": str(tarefa), "fk_casa_id": str(casa)}],
        "casa": [{"id": str(casa), "fk_usuario_id": str(usuario)}],
        "atribuida": [{"fk_tarefa_id": str(tarefa), "fk_usuario_id": str(usuario)}],
        "pertencer": [],
    }
    envio = Mock(return_value={"aceitos": [{"ticket_id": "teste"}], "invalidos": [], "falhas": []})
    monkeypatch.setattr(ServicoNotificacao, "enviar_push", envio)
    return SimpleNamespace(
        usuario=usuario, tarefa=tarefa, casa=casa,
        banco=BancoLeitura(registros), envio=envio,
    )


@pytest.mark.parametrize("tipo", ["tarefa_atribuida", "tarefa_vence_hoje", "tarefa_atrasada"])
def test_aviso_manual_envia_so_ao_solicitante_sem_consultar_horario_ou_gravar(ambiente, tipo):
    resultado = enviar_notificacao_teste(ambiente.banco, ambiente.usuario, NotificacaoTesteEntrada(
        tipo=tipo, tarefa_id=ambiente.tarefa,
    ))
    assert resultado == {"aceitos": 1, "falhas": 0, "invalidos": 0}
    usuarios, titulo, mensagem, payload = ambiente.envio.call_args.args
    assert usuarios == [ambiente.usuario]
    assert titulo.startswith("Teste:")
    assert mensagem
    assert payload == {
        "tipo": tipo, "tarefa_id": str(ambiente.tarefa), "casa_id": str(ambiente.casa),
    }


def test_tarefa_inexistente_nao_dispara_push(ambiente):
    with pytest.raises(HTTPException) as erro:
        enviar_notificacao_teste(ambiente.banco, ambiente.usuario, NotificacaoTesteEntrada(
            tipo="tarefa_atribuida", tarefa_id=uuid4(),
        ))
    assert erro.value.status_code == 404
    ambiente.envio.assert_not_called()


def test_casa_inacessivel_nao_dispara_push_mesmo_com_atribuicao_antiga(ambiente):
    ambiente.banco.registros["casa"][0]["fk_usuario_id"] = str(uuid4())
    with pytest.raises(HTTPException) as erro:
        enviar_notificacao_teste(ambiente.banco, ambiente.usuario, NotificacaoTesteEntrada(
            tipo="tarefa_atribuida", tarefa_id=ambiente.tarefa,
        ))
    assert erro.value.status_code == 403
    ambiente.envio.assert_not_called()


def test_tarefa_de_outro_responsavel_nao_dispara_push(ambiente):
    ambiente.banco.registros["atribuida"][0]["fk_usuario_id"] = str(uuid4())
    with pytest.raises(HTTPException) as erro:
        enviar_notificacao_teste(ambiente.banco, ambiente.usuario, NotificacaoTesteEntrada(
            tipo="tarefa_atrasada", tarefa_id=ambiente.tarefa,
        ))
    assert erro.value.status_code == 403
    ambiente.envio.assert_not_called()


@pytest.mark.parametrize("invalidos", [[], ["aparelho-invalido"]])
def test_sem_aparelho_valido_orienta_ativar_notificacoes(ambiente, invalidos):
    ambiente.envio.return_value = {"aceitos": [], "invalidos": invalidos, "falhas": []}
    with pytest.raises(HTTPException) as erro:
        enviar_notificacao_teste(ambiente.banco, ambiente.usuario, NotificacaoTesteEntrada(
            tipo="tarefa_atribuida", tarefa_id=ambiente.tarefa,
        ))
    assert erro.value.status_code == 409
    assert "Ative as notificações" in erro.value.detail


def test_falha_total_de_envio_nao_informa_sucesso(ambiente):
    ambiente.envio.return_value = {
        "aceitos": [], "invalidos": [], "falhas": [{"erro": "EnvioRecusado"}],
    }
    with pytest.raises(HTTPException) as erro:
        enviar_notificacao_teste(ambiente.banco, ambiente.usuario, NotificacaoTesteEntrada(
            tipo="tarefa_vence_hoje", tarefa_id=ambiente.tarefa,
        ))
    assert erro.value.status_code == 502


def test_sucesso_parcial_retorna_contagens_sem_identificadores_de_aparelhos(ambiente):
    ambiente.envio.return_value = {
        "aceitos": [{"ticket_id": "teste"}], "invalidos": ["aparelho"],
        "falhas": [{"erro": "EnvioRecusado"}],
    }
    assert enviar_notificacao_teste(ambiente.banco, ambiente.usuario, NotificacaoTesteEntrada(
        tipo="tarefa_atribuida", tarefa_id=ambiente.tarefa,
    )) == {"aceitos": 1, "invalidos": 1, "falhas": 1}


@pytest.mark.parametrize("alteracao", [
    {"tipo": "desconhecido"}, {"tarefa_id": "invalido"}, {"usuario_id": str(uuid4())},
])
def test_entrada_rejeita_tipo_id_invalido_e_destinatario_arbitrario(alteracao):
    with pytest.raises(ValidationError):
        NotificacaoTesteEntrada.model_validate({
            "tipo": "tarefa_atribuida", "tarefa_id": str(uuid4()), **alteracao,
        })
