import assert from "node:assert/strict";
import test from "node:test";

import {
  carregarTarefas,
  carregarContextoTarefas,
  carregarUsuarioAtual,
  finalizarTarefa,
  temConfiguracaoTarefas,
} from "../src/services/tarefas-api.ts";

test("envia filtros e credencial para a lista da casa", async () => {
  process.env.EXPO_PUBLIC_API_URL = "http://api.test/";
  process.env.EXPO_PUBLIC_CASA_ID = "casa-123";
  process.env.EXPO_PUBLIC_TETO_JUSTO_TOKEN = "sessao-valida";
  const fetchOriginal = globalThis.fetch;
  let requisicao;

  globalThis.fetch = async (url, opcoes) => {
    requisicao = { url, opcoes };
    return { ok: true, json: async () => [] };
  };

  try {
    await carregarTarefas({
      estado: "pendente",
      responsavel: "morador-456",
      prazo: "sete_dias",
    });
  } finally {
    globalThis.fetch = fetchOriginal;
  }

  assert.equal(
    requisicao.url,
    "http://api.test/tarefas/casa/casa-123?estado=pendente&prazo=sete_dias&responsavel=morador-456",
  );
  assert.equal(requisicao.opcoes.headers.Authorization, "Bearer sessao-valida");
});

test("consulta casa e moradores reais para a criação sem enviar gravações", async () => {
  process.env.EXPO_PUBLIC_API_URL = "http://api.test/";
  process.env.EXPO_PUBLIC_CASA_ID = "casa-123";
  process.env.EXPO_PUBLIC_TETO_JUSTO_TOKEN = "sessao-valida";
  const original = globalThis.fetch;
  const chamadas = [];
  const casa = { id: "casa-123", nome: "Casa real" };
  const moradores = [{ id: "morador-real", nome: "Morador real", score: 0 }];
  const usuario = { id: "morador-real" };
  globalThis.fetch = async (url, opcoes) => {
    chamadas.push({ url, opcoes });
    return {
      ok: true,
      json: async () =>
        url.endsWith("/moradores")
          ? moradores
          : url.endsWith("/eu")
            ? usuario
            : casa,
    };
  };
  try {
    const sinal = new AbortController().signal;
    assert.deepEqual(await carregarContextoTarefas(sinal), [casa, moradores]);
    assert.deepEqual(await carregarUsuarioAtual(sinal), usuario);
    assert.equal(chamadas.length, 3);
    for (const chamada of chamadas) {
      assert.equal(chamada.opcoes.method, "GET");
      assert.equal(chamada.opcoes.signal, sinal);
      assert.equal(
        chamada.opcoes.headers.Authorization,
        "Bearer sessao-valida",
      );
    }
  } finally {
    globalThis.fetch = original;
  }
});

test("finaliza a tarefa pelo endpoint autenticado", async () => {
  process.env.EXPO_PUBLIC_API_URL = "http://api.test";
  process.env.EXPO_PUBLIC_CASA_ID = "casa-123";
  process.env.EXPO_PUBLIC_TETO_JUSTO_TOKEN = "sessao-valida";
  const original = globalThis.fetch;
  let requisicao;
  globalThis.fetch = async (url, opcoes) => {
    requisicao = { url, opcoes };
    return { ok: true, json: async () => ({ id: "tarefa-123" }) };
  };

  try {
    await finalizarTarefa("tarefa-123");
    assert.equal(requisicao.url, "http://api.test/tarefas/tarefa-123");
    assert.equal(requisicao.opcoes.method, "PATCH");
    assert.equal(requisicao.opcoes.body, '{"estado_atual":"finalizado"}');
    assert.equal(
      requisicao.opcoes.headers.Authorization,
      "Bearer sessao-valida",
    );
  } finally {
    globalThis.fetch = original;
  }
});

test("configuração parcial informa o erro em vez de trocar por dados fictícios", async () => {
  const nomes = [
    "EXPO_PUBLIC_API_URL",
    "EXPO_PUBLIC_CASA_ID",
    "EXPO_PUBLIC_TETO_JUSTO_TOKEN",
  ];
  const anteriores = nomes.map((nome) => process.env[nome]);
  try {
    for (const nome of nomes) delete process.env[nome];
    assert.equal(temConfiguracaoTarefas(), false);
    process.env.EXPO_PUBLIC_CASA_ID = "casa-123";
    assert.equal(temConfiguracaoTarefas(), true);
    await assert.rejects(
      carregarContextoTarefas(),
      /Configure EXPO_PUBLIC_API_URL/,
    );
  } finally {
    nomes.forEach((nome, indice) => {
      const valor = anteriores.at(indice);
      if (valor === undefined) delete process.env[nome];
      else process.env[nome] = valor;
    });
  }
});

test("configuração ausente é capturada pelos handlers da tela, sem erro síncrono ou fetch", async () => {
  const nomes = [
    "EXPO_PUBLIC_API_URL",
    "EXPO_PUBLIC_CASA_ID",
    "EXPO_PUBLIC_TETO_JUSTO_TOKEN",
  ];
  const anteriores = nomes.map((nome) => process.env[nome]);
  const originalFetch = globalThis.fetch;
  let chamadas = 0;
  globalThis.fetch = async () => {
    chamadas++;
    throw new Error("Não deveria consultar a rede");
  };
  const filtros = { estado: "todos", prazo: "todos", responsavel: "todos" };
  try {
    // Os dois efeitos de Tarefas usam estas formas de encadear as consultas.
    for (const ausente of [null, ...nomes]) {
      for (const nome of nomes) {
        if (ausente === null || nome === ausente) delete process.env[nome];
        else process.env[nome] = "valor-ficticio";
      }
      const erros = [];
      let finalizacoes = 0;
      await Promise.all([
        Promise.all([carregarContextoTarefas(), carregarTarefas(filtros)])
          .catch((erro) => erros.push(erro.message))
          .finally(() => finalizacoes++),
        carregarTarefas(filtros)
          .catch((erro) => erros.push(erro.message))
          .finally(() => finalizacoes++),
      ]);
      assert.equal(erros.length, 2);
      assert.ok(
        erros.every((erro) => erro.includes("Configure EXPO_PUBLIC_API_URL")),
      );
      assert.equal(finalizacoes, 2);
    }
    assert.equal(chamadas, 0);
  } finally {
    globalThis.fetch = originalFetch;
    nomes.forEach((nome, indice) => {
      const valor = anteriores.at(indice);
      if (valor === undefined) delete process.env[nome];
      else process.env[nome] = valor;
    });
  }
});
