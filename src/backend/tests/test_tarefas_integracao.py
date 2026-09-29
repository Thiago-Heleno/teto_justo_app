from datetime import datetime, time, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from core.database import get_supabase
from main import app


@pytest.fixture
def dependencias_temporarias(autenticacao_temporaria):
    supabase = get_supabase()
    marcador = uuid4().hex
    usuario_id = autenticacao_temporaria["usuario_id"]

    res_casa = (
        supabase.table("casa")
        .insert({"nome": f"Casa Teste {marcador}", "fk_usuario_id": usuario_id})
        .execute()
    )
    casa_id = res_casa.data[0]["id"]

    yield {"usuario_id": usuario_id, "casa_id": casa_id}

    # A migration 17 preserva o histórico de créditos ao impedir a exclusão da tarefa.
    supabase.table("score_event").delete().eq("fk_casa_id", casa_id).execute()
    supabase.table("tarefa").delete().eq("fk_casa_id", casa_id).execute()
    supabase.table("pertencer").delete().eq("fk_casa_id", casa_id).execute()
    supabase.table("casa").delete().eq("id", casa_id).execute()


def test_crud_tarefa_no_supabase(
    dependencias_temporarias,
    autenticacao_temporaria,
):
    usuario_id = dependencias_temporarias["usuario_id"]
    casa_id = dependencias_temporarias["casa_id"]

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente:
        # TESTE: Criar
        criada = cliente.post(
            "/tarefas/",
            json={
                "nome": "Limpar a caixa de areia",
                "descricao": "Usar a pá nova",
                "estado_atual": "pendente",
                "peso": 2,
                "atraso_maximo": 5,
                "prazo_dias": 2,
                "fk_casa_id": casa_id,
                "usuarios_atribuidos": [usuario_id],
            },
        )
        assert criada.status_code == 201, criada.text
        tarefa = criada.json()
        assert tarefa["nome"] == "Limpar a caixa de areia"
        assert tarefa["pontuacao"] == 25
        assert tarefa["fk_usuario_id"] == usuario_id
        assert datetime.fromisoformat(tarefa["data_fim"]) - datetime.fromisoformat(
            tarefa["data_inicio"]
        ) == timedelta(days=2)
        assert tarefa["fk_casa_id"] == casa_id
        assert len(tarefa["usuarios_atribuidos"]) == 1

        # TESTE: Buscar por ID
        encontrada = cliente.get(f"/tarefas/{tarefa['id']}")
        assert encontrada.status_code == 200, encontrada.text
        assert encontrada.json()["id"] == tarefa["id"]

        # TESTE: Listar por casa
        lista_casa = cliente.get(f"/tarefas/casa/{casa_id}")
        assert lista_casa.status_code == 200, lista_casa.text
        assert len(lista_casa.json()) >= 1

        # TESTE: Atualizar
        novo_nome = "Limpar toda a varanda"
        atualizada = cliente.patch(
            f"/tarefas/{tarefa['id']}",
            json={"nome": novo_nome, "estado_atual": "atrasada", "peso": 3},
        )
        assert atualizada.status_code == 200, atualizada.text
        assert atualizada.json()["nome"] == novo_nome
        assert atualizada.json()["estado_atual"] == "atrasada"
        assert atualizada.json()["peso"] == 3
        assert atualizada.json()["pontuacao"] == 50

        # TESTE: Excluir
        excluida = cliente.delete(f"/tarefas/{tarefa['id']}")
        assert excluida.status_code == 200, excluida.text
        assert excluida.json() is True

        # TESTE: Garantir que foi excluída
        inexistente = cliente.get(f"/tarefas/{tarefa['id']}")
        assert inexistente.status_code == 404


@pytest.mark.parametrize("modo_prazo", ["intervalo", "dia_fixo"])
def test_tipo_e_modo_prazo_persistem_no_supabase(
    dependencias_temporarias, autenticacao_temporaria, modo_prazo
):
    supabase = get_supabase()
    casa_id = dependencias_temporarias["casa_id"]
    usuario_id = dependencias_temporarias["usuario_id"]
    fuso = ZoneInfo("America/Manaus")
    supabase.table("casa").update({"timezone": fuso.key}).eq("id", casa_id).execute()

    dados = {
        "nome": f"Tarefa {modo_prazo}",
        "peso": 2,
        "prazo_dias": 2,
        "atraso_maximo": 2,
        "tipo": "unitaria",
        "modo_prazo": modo_prazo,
        "fk_casa_id": casa_id,
        "usuarios_atribuidos": [usuario_id],
    }
    data_fixa = None
    if modo_prazo == "dia_fixo":
        data_fixa = datetime.now(fuso).date() + timedelta(days=10)
        dados["data_fixa"] = data_fixa.isoformat()

    with TestClient(app, headers=autenticacao_temporaria["headers"]) as cliente:
        antes = datetime.now(timezone.utc)
        criada = cliente.post("/tarefas/", json=dados)
        depois = datetime.now(timezone.utc)
        assert criada.status_code == 201, criada.text
        tarefa_id = criada.json()["id"]

        encontrada = cliente.get(f"/tarefas/{tarefa_id}")
        assert encontrada.status_code == 200, encontrada.text
        for resposta in (criada.json(), encontrada.json()):
            assert resposta["tipo"] == "unitaria"
            assert resposta["modo_prazo"] == modo_prazo
            assert resposta["data_fixa"] == (data_fixa.isoformat() if data_fixa else None)

        for campo, valor in (("tipo", "rotativa"), ("modo_prazo", "dia_fixo")):
            rejeitada = cliente.patch(f"/tarefas/{tarefa_id}", json={campo: valor})
            assert rejeitada.status_code == 422, rejeitada.text

    registro = (
        supabase.table("tarefa")
        .select("tipo,modo_prazo,prazo_dias,data_inicio,data_fim,timezone")
        .eq("id", tarefa_id)
        .single()
        .execute()
        .data
    )
    assert registro["tipo"] == "unitaria"
    assert registro["modo_prazo"] == modo_prazo
    assert registro["prazo_dias"] == 2
    # As colunas TIMESTAMP da tarefa armazenam datas em UTC sem indicador de fuso.
    inicio = datetime.fromisoformat(registro["data_inicio"]).replace(tzinfo=timezone.utc)
    fim = datetime.fromisoformat(registro["data_fim"]).replace(tzinfo=timezone.utc)
    assert fim - inicio == timedelta(days=2)
    if modo_prazo == "dia_fixo":
        assert registro["timezone"] == fuso.key
        assert fim == datetime.combine(data_fixa, time.max, tzinfo=fuso).astimezone(
            timezone.utc
        )
    else:
        assert antes <= inicio <= depois


def test_morador_nao_pode_criar_atualizar_ou_excluir_tarefa(
    dependencias_temporarias,
    autenticacao_temporaria,
    criar_autenticacao_temporaria,
):
    supabase = get_supabase()
    casa_id = dependencias_temporarias["casa_id"]
    administrador_id = autenticacao_temporaria["usuario_id"]
    morador = criar_autenticacao_temporaria()

    vinculo = (
        supabase.table("pertencer")
        .insert(
            {
                "fk_usuario_id": morador["usuario_id"],
                "fk_casa_id": casa_id,
                "score": 0,
            }
        )
        .execute()
    )
    assert vinculo.data

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=morador["headers"],
    ) as cliente_morador:
        proibida = cliente_morador.post(
            "/tarefas/",
            json={
                "nome": "Tarefa que o morador não pode criar",
                "estado_atual": "pendente",
                "peso": 1,
                "atraso_maximo": 5,
                "prazo_dias": 2,
                "fk_casa_id": casa_id,
                "usuarios_atribuidos": [morador["usuario_id"]],
            },
        )
        assert proibida.status_code == 403, proibida.text

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente_admin:
        criada = cliente_admin.post(
            "/tarefas/",
            json={
                "nome": "Tarefa protegida",
                "estado_atual": "pendente",
                "peso": 1,
                "atraso_maximo": 5,
                "prazo_dias": 2,
                "fk_casa_id": casa_id,
                "usuarios_atribuidos": [administrador_id],
            },
        )
        assert criada.status_code == 201, criada.text
        tarefa = criada.json()

        troca_de_casa = cliente_admin.patch(
            f"/tarefas/{tarefa['id']}",
            json={"fk_casa_id": str(uuid4())},
        )
        assert troca_de_casa.status_code == 422, troca_de_casa.text

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=morador["headers"],
    ) as cliente_morador:
        atualizada = cliente_morador.patch(
            f"/tarefas/{tarefa['id']}",
            json={"nome": "Alteração proibida"},
        )
        assert atualizada.status_code == 403, atualizada.text

        excluida = cliente_morador.delete(f"/tarefas/{tarefa['id']}")
        assert excluida.status_code == 403, excluida.text

        preservada = cliente_morador.get(f"/tarefas/{tarefa['id']}")
        assert preservada.status_code == 200, preservada.text
        assert preservada.json()["nome"] == "Tarefa protegida"

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente_admin:
        excluida = cliente_admin.delete(f"/tarefas/{tarefa['id']}")
        assert excluida.status_code == 200, excluida.text


def test_criar_tarefa_rejeita_responsaveis_invalidos(
    dependencias_temporarias,
    autenticacao_temporaria,
    criar_autenticacao_temporaria,
):
    casa_id = dependencias_temporarias["casa_id"]
    administrador_id = autenticacao_temporaria["usuario_id"]
    morador_de_outra_casa = criar_autenticacao_temporaria()

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente_admin:
        # Cada ocorrência deve ter exatamente um responsável.
        duplicado = cliente_admin.post(
            "/tarefas/",
            json={
                "nome": "Tarefa nascendo com responsável duplicado",
                "estado_atual": "pendente",
                "peso": 1,
                "atraso_maximo": 5,
                "prazo_dias": 2,
                "fk_casa_id": casa_id,
                "usuarios_atribuidos": [administrador_id, administrador_id],
            },
        )
        assert duplicado.status_code == 422, duplicado.text

        # Responsável que não pertence a esta casa
        de_outra_casa = cliente_admin.post(
            "/tarefas/",
            json={
                "nome": "Tarefa nascendo com responsável de outra casa",
                "estado_atual": "pendente",
                "peso": 1,
                "atraso_maximo": 5,
                "prazo_dias": 2,
                "fk_casa_id": casa_id,
                "usuarios_atribuidos": [morador_de_outra_casa["usuario_id"]],
            },
        )
        assert de_outra_casa.status_code == 422, de_outra_casa.text

        # Responsável válido (o próprio dono da casa) passa normalmente
        valida = cliente_admin.post(
            "/tarefas/",
            json={
                "nome": "Tarefa nascendo com responsável válido",
                "estado_atual": "pendente",
                "peso": 1,
                "atraso_maximo": 5,
                "prazo_dias": 2,
                "fk_casa_id": casa_id,
                "usuarios_atribuidos": [administrador_id],
            },
        )
        assert valida.status_code == 201, valida.text
        assert valida.json()["usuarios_atribuidos"] == [administrador_id]


def test_atualizar_tarefa_rejeita_responsaveis_invalidos(
    dependencias_temporarias,
    autenticacao_temporaria,
    criar_autenticacao_temporaria,
):
    supabase = get_supabase()
    casa_id = dependencias_temporarias["casa_id"]
    administrador_id = autenticacao_temporaria["usuario_id"]
    morador_da_casa = criar_autenticacao_temporaria()
    morador_de_outra_casa = criar_autenticacao_temporaria()

    vinculo = (
        supabase.table("pertencer")
        .insert(
            {
                "fk_usuario_id": morador_da_casa["usuario_id"],
                "fk_casa_id": casa_id,
                "score": 0,
            }
        )
        .execute()
    )
    assert vinculo.data

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente_admin:
        criada = cliente_admin.post(
            "/tarefas/",
            json={
                "nome": "Tarefa com responsáveis a validar",
                "estado_atual": "pendente",
                "peso": 1,
                "atraso_maximo": 5,
                "prazo_dias": 2,
                "fk_casa_id": casa_id,
                "usuarios_atribuidos": [administrador_id],
            },
        )
        assert criada.status_code == 201, criada.text
        tarefa = criada.json()

        # Responsável duplicado na mesma lista
        duplicado = cliente_admin.patch(
            f"/tarefas/{tarefa['id']}",
            json={
                "usuarios_atribuidos": [
                    morador_da_casa["usuario_id"],
                    morador_da_casa["usuario_id"],
                ]
            },
        )
        assert duplicado.status_code == 422, duplicado.text

        # Responsável que não pertence a esta casa
        de_outra_casa = cliente_admin.patch(
            f"/tarefas/{tarefa['id']}",
            json={"usuarios_atribuidos": [morador_de_outra_casa["usuario_id"]]},
        )
        assert de_outra_casa.status_code == 400, de_outra_casa.text

        # Troca para um morador vinculado à casa
        validos = cliente_admin.patch(
            f"/tarefas/{tarefa['id']}",
            json={
                "usuarios_atribuidos": [
                    morador_da_casa["usuario_id"],
                ]
            },
        )
        assert validos.status_code == 200, validos.text
        assert set(validos.json()["usuarios_atribuidos"]) == {
            morador_da_casa["usuario_id"],
        }


def test_tarefa_expirada_vira_nao_feito_ao_ser_consultada(
    dependencias_temporarias,
    autenticacao_temporaria,
):
    supabase = get_supabase()
    casa_id = dependencias_temporarias["casa_id"]
    usuario_id = dependencias_temporarias["usuario_id"]

    with TestClient(
        app,
        raise_server_exceptions=False,
        headers=autenticacao_temporaria["headers"],
    ) as cliente:
        # A API exige prazo futuro na criação, então a tarefa nasce válida e
        # o prazo é atrasado direto no banco para simular o tempo passando.
        criada = cliente.post(
            "/tarefas/",
            json={
                "nome": "Tarefa vencida",
                "estado_atual": "pendente",
                "peso": 1,
                "atraso_maximo": 2,
                "prazo_dias": 2,
                "fk_casa_id": casa_id,
                "usuarios_atribuidos": [usuario_id],
            },
        )
        assert criada.status_code == 201, criada.text
        tarefa = criada.json()

        # data_fim já passou há mais dias do que o atraso_maximo (2): a
        # tarefa nunca foi finalizada manualmente e deve virar 'nao_feito'
        # sozinha na primeira consulta, sem nenhum job/cron envolvido.
        data_fim_passada = datetime.now(timezone.utc) - timedelta(days=10)
        supabase.table("tarefa").update(
            {
                "data_fim": data_fim_passada.isoformat(),
                "data_inicio": (data_fim_passada - timedelta(days=2)).isoformat(),
            }
        ).eq("id", tarefa["id"]).execute()

        consultada = cliente.get(f"/tarefas/{tarefa['id']}")
        assert consultada.status_code == 200, consultada.text
        assert consultada.json()["estado_atual"] == "nao_feito"


@pytest.mark.parametrize(
    "horas_atraso,pontos,status",
    [
        (-1, 50, 200),
        (12, 33, 200),
        (36, 17, 200),
        (60, 0, 409),
    ],
)
def test_credito_real_respeita_tolerancia_e_nao_duplica(
    dependencias_temporarias, autenticacao_temporaria, horas_atraso, pontos, status
):
    supabase = get_supabase()
    usuario = dependencias_temporarias["usuario_id"]
    casa = dependencias_temporarias["casa_id"]
    supabase.table("pertencer").insert(
        {
            "fk_usuario_id": usuario,
            "fk_casa_id": casa,
            "score": 0,
        }
    ).execute()
    with TestClient(app, headers=autenticacao_temporaria["headers"]) as cliente:
        criada = cliente.post(
            "/tarefas/",
            json={
                "nome": "Crédito proporcional",
                "peso": 3,
                "prazo_dias": 3,
                "atraso_maximo": 2,
                "fk_casa_id": casa,
                "usuarios_atribuidos": [usuario],
            },
        )
        assert criada.status_code == 201, criada.text
        tarefa_id = criada.json()["id"]
        fim = datetime.now(timezone.utc) - timedelta(hours=horas_atraso)
        supabase.table("tarefa").update(
            {
                "data_inicio": (fim - timedelta(days=3)).isoformat(),
                "data_fim": fim.isoformat(),
            }
        ).eq("id", tarefa_id).execute()
        concluida = cliente.post(f"/tarefas/{tarefa_id}/conclusoes")
        assert concluida.status_code == status, concluida.text
        if status == 200:
            assert concluida.json()["resultado_pontuacao"] == {
                "pontos_possiveis": 50,
                "pontos_ganhos": pontos,
                "saldo_atual": pontos,
            }
            assert concluida.json()["concluida_em"] is not None
            preservada = cliente.delete(f"/tarefas/{tarefa_id}")
            assert preservada.status_code == 409, preservada.text
        repetida = cliente.post(f"/tarefas/{tarefa_id}/conclusoes")
        assert repetida.status_code == 409, repetida.text
    eventos = (
    supabase.table("score_event")
    .select("tipo,pontuacao")
    .eq("fk_tarefa_id", tarefa_id)
    .execute()
    )
    assert {(evento["tipo"], evento["pontuacao"]) for evento in eventos.data} == (
        {("credito", pontos)} if status == 200 else set()
    )
    saldo = (
        supabase.table("pertencer")
        .select("score")
        .eq("fk_casa_id", casa)
        .eq("fk_usuario_id", usuario)
        .execute()
    )
    assert saldo.data[0]["score"] == pontos
    with TestClient(app, headers=autenticacao_temporaria["headers"]) as cliente:
        placar = cliente.get(f"/casas/{casa}/placar")
        assert placar.status_code == 200, placar.text
        assert placar.json()["moradores"][0]["acumulado"] == pontos
        auditoria = cliente.get(f"/casas/{casa}/auditoria-score")
        assert auditoria.status_code == 200, auditoria.text
        assert auditoria.json()["divergencias"] == []


def test_atualizar_estado_diretamente_no_banco_nao_calcula_pontos(
    dependencias_temporarias, autenticacao_temporaria
):
    supabase = get_supabase()
    usuario = dependencias_temporarias["usuario_id"]
    casa = dependencias_temporarias["casa_id"]
    supabase.table("pertencer").insert(
        {
            "fk_usuario_id": usuario,
            "fk_casa_id": casa,
            "score": 0,
        }
    ).execute()
    with TestClient(app, headers=autenticacao_temporaria["headers"]) as cliente:
        criada = cliente.post(
            "/tarefas/",
            json={
                "nome": "Sem trigger de cálculo",
                "peso": 3,
                "prazo_dias": 3,
                "atraso_maximo": 2,
                "fk_casa_id": casa,
                "usuarios_atribuidos": [usuario],
            },
        )
        assert criada.status_code == 201, criada.text
    tarefa_id = criada.json()["id"]
    atualizada = (
        supabase.table("tarefa")
        .update({"estado_atual": "finalizado"})
        .eq("id", tarefa_id)
        .execute()
    )
    assert atualizada.data[0]["concluida_em"] is None
    eventos = supabase.table("score_event").select("id").eq("fk_tarefa_id", tarefa_id).execute()
    assert eventos.data == []
    saldo = supabase.table("pertencer").select("score").eq("fk_casa_id", casa).execute()
    assert saldo.data[0]["score"] == 0


def test_conclusao_sem_vinculo_reverte_toda_a_gravacao(
    dependencias_temporarias, autenticacao_temporaria
):
    supabase = get_supabase()
    usuario = dependencias_temporarias["usuario_id"]
    casa = dependencias_temporarias["casa_id"]
    with TestClient(app, headers=autenticacao_temporaria["headers"]) as cliente:
        criada = cliente.post(
            "/tarefas/",
            json={
                "nome": "Conclusão atômica",
                "peso": 2,
                "prazo_dias": 3,
                "atraso_maximo": 1,
                "fk_casa_id": casa,
                "usuarios_atribuidos": [usuario],
            },
        )
        assert criada.status_code == 201, criada.text
        tarefa_id = criada.json()["id"]
        falha = cliente.post(f"/tarefas/{tarefa_id}/conclusoes")
        assert falha.status_code == 409, falha.text
        tarefa = (
            supabase.table("tarefa")
            .select("estado_atual,concluida_em")
            .eq("id", tarefa_id)
            .execute()
        )
        assert tarefa.data[0] == {"estado_atual": "pendente", "concluida_em": None}
        eventos = supabase.table("score_event").select("id").eq("fk_tarefa_id", tarefa_id).execute()
        assert eventos.data == []
        supabase.table("pertencer").insert(
            {
                "fk_usuario_id": usuario,
                "fk_casa_id": casa,
                "score": 0,
            }
        ).execute()
        concluida = cliente.post(f"/tarefas/{tarefa_id}/conclusoes")
        assert concluida.status_code == 200, concluida.text
    saldo = supabase.table("pertencer").select("score").eq("fk_casa_id", casa).execute()
    assert saldo.data[0]["score"] == 25


def test_conclusoes_simultaneas_creditam_uma_unica_vez(
    dependencias_temporarias, autenticacao_temporaria
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    supabase = get_supabase()
    usuario = dependencias_temporarias["usuario_id"]
    casa = dependencias_temporarias["casa_id"]
    supabase.table("pertencer").insert(
        {
            "fk_usuario_id": usuario,
            "fk_casa_id": casa,
            "score": 0,
        }
    ).execute()
    with TestClient(app, headers=autenticacao_temporaria["headers"]) as cliente:
        criada = cliente.post(
            "/tarefas/",
            json={
                "nome": "Conclusões concorrentes",
                "peso": 3,
                "prazo_dias": 3,
                "atraso_maximo": 2,
                "fk_casa_id": casa,
                "usuarios_atribuidos": [usuario],
            },
        )
        assert criada.status_code == 201, criada.text
    tarefa_id = criada.json()["id"]
    barreira = Barrier(2, timeout=10)

    def concluir():
        with TestClient(app, headers=autenticacao_temporaria["headers"]) as cliente:
            barreira.wait()
            return cliente.post(f"/tarefas/{tarefa_id}/conclusoes")

    with ThreadPoolExecutor(max_workers=2) as executor:
        futuros = [executor.submit(concluir) for _ in range(2)]
        respostas = [futuro.result(timeout=30) for futuro in futuros]
    assert sorted(resposta.status_code for resposta in respostas) == [200, 409]
    eventos = (
        supabase.table("score_event").select("pontuacao").eq("fk_tarefa_id", tarefa_id).execute()
    )
    assert eventos.data == [{"pontuacao": 50}]
    saldo = supabase.table("pertencer").select("score").eq("fk_casa_id", casa).execute()
    assert saldo.data[0]["score"] == 50
