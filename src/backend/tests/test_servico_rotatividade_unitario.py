from uuid import uuid4

import pytest

from services.rotatividade import TarefaDistribuicao, ServicoRotatividade


@pytest.fixture
def usuarios():
    return tuple(uuid4() for _ in range(3))


def tarefa(pontos, elegiveis):
    return TarefaDistribuicao(uuid4(), pontos, tuple(elegiveis))


def test_distribui_pontos_equivalentemente_respeitando_elegibilidade(usuarios):
    ana, bruna, caio = usuarios
    tarefas = [
        tarefa(50, [ana, bruna, caio]),
        tarefa(25, [ana, bruna]),
        tarefa(25, [bruna, caio]),
    ]

    resultado = ServicoRotatividade().distribuir_tarefas(tarefas, usuarios)

    assert resultado.pontuacao_por_usuario == {ana: 50, bruna: 25, caio: 25}
    assert all(
        atribuicao.usuario_id in tarefa_atual.usuarios_elegiveis
        for atribuicao, tarefa_atual in zip(resultado.atribuicoes, tarefas)
    )


def test_desempate_e_ordem_de_saida_sao_deterministicos(usuarios):
    tarefas = [tarefa(10, usuarios), tarefa(10, usuarios), tarefa(10, usuarios)]

    resultado = ServicoRotatividade().distribuir_tarefas(tarefas, usuarios)

    assert [item.usuario_id for item in resultado.atribuicoes] == list(usuarios)


def test_considera_pontuacao_anterior_no_balanceamento(usuarios):
    ana, bruna, caio = usuarios
    resultado = ServicoRotatividade().distribuir_tarefas(
        [tarefa(25, usuarios)],
        usuarios,
        pontuacao_inicial={ana: 25, bruna: 0, caio: 0},
    )

    assert resultado.atribuicoes[0].usuario_id == bruna
    assert resultado.pontuacao_por_usuario == {ana: 25, bruna: 25, caio: 0}


def test_rejeita_tarefa_sem_elegibilidade():
    usuario = uuid4()
    with pytest.raises(ValueError):
        TarefaDistribuicao(uuid4(), 10, ())

    with pytest.raises(ValueError):
        ServicoRotatividade().distribuir_tarefas(
            [tarefa(10, [usuario])],
            [uuid4()],
        )


def test_rejeita_pontuacao_inicial_invalida(usuarios):
    with pytest.raises(ValueError):
        ServicoRotatividade().distribuir_tarefas(
            [tarefa(10, usuarios)],
            usuarios,
            pontuacao_inicial={usuarios[0]: -1},
        )
