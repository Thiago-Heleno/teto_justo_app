"""Autorização real dos serviços com respostas de banco simuladas."""
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from schemas.rotatividade import RotatividadeAtualizar
from services.rotatividade_agendamento import ServicoAgendamentoRotatividade


def consulta_com_respostas(respostas):
    banco = MagicMock()
    consulta = banco.table.return_value
    for metodo in ("select", "eq", "limit", "order", "range"):
        getattr(consulta, metodo).return_value = consulta
    consulta.execute.side_effect = [SimpleNamespace(data=dados) for dados in respostas]
    return banco


@pytest.mark.parametrize("admin", [True, False])
def test_lista_regras_para_admin_e_morador_ativo(admin):
    usuario, casa = uuid4(), uuid4()
    dono = usuario if admin else uuid4()
    regra = {"id": str(uuid4()), "fk_casa_id": str(casa)}
    respostas = [[{"fk_usuario_id": str(dono)}]]
    if not admin:
        respostas.append([{"fk_usuario_id": str(usuario)}])
    respostas.append([regra])
    banco = consulta_com_respostas(respostas)
    assert ServicoAgendamentoRotatividade(banco).listar_rotatividades(casa, usuario) == [regra]
    banco.table.return_value.eq.assert_any_call("fk_casa_id", str(casa))
    if not admin:
        banco.table.return_value.eq.assert_any_call("ativo", True)


def test_nao_morador_nao_consegue_listar_regras():
    banco = consulta_com_respostas([[{"fk_usuario_id": str(uuid4())}], []])
    with pytest.raises(HTTPException) as erro:
        ServicoAgendamentoRotatividade(banco).listar_rotatividades(uuid4(), uuid4())
    assert erro.value.status_code == 403
    assert "rotatividade" not in [c.args[0] for c in banco.table.call_args_list]


@pytest.mark.parametrize("acao", ["editar", "remover"])
def test_morador_nao_consegue_alterar_regras(acao):
    casa, dono, usuario, regra_id = uuid4(), uuid4(), uuid4(), uuid4()
    banco = consulta_com_respostas([
        [{"id": str(regra_id), "fk_casa_id": str(casa)}],
        [{"fk_usuario_id": str(dono)}],
    ])
    servico = ServicoAgendamentoRotatividade(banco)
    with pytest.raises(HTTPException) as erro:
        if acao == "editar":
            servico.atualizar_rotatividade(regra_id, RotatividadeAtualizar(nome="Novo nome"), usuario)
        else:
            servico.excluir_rotatividade(regra_id, usuario)
    assert erro.value.status_code == 403
    banco.table.return_value.update.assert_not_called()
    banco.table.return_value.delete.assert_not_called()
