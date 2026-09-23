import assert from "node:assert/strict";
import test from "node:test";

import { carregarTarefas } from "../src/services/tarefas-api.ts";

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
