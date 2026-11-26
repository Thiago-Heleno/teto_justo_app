import assert from "node:assert/strict";
import test, { mock } from "node:test";
import {
  escalaPontos,
  posicaoDia,
  proporcaoPontos,
  resumirDia,
  rotuloDia,
  temSerieDiaria,
} from "../src/utils/grafico-desempenho.ts";

mock.module("../src/services/sessao-store.ts", {
  namedExports: {
    sessao: {
      getState: () => ({
        casaAtiva: { id: "casa-123" },
        token: "sessao-de-teste",
      }),
    },
    encerrarSessao: async () => {},
  },
});
const { carregarDesempenho } = await import("../src/services/tarefas-api.ts");

const moradores = [
  {
    usuario_id: "a",
    nome: "Ana",
    total: 5,
    serie: [
      { data: "2026-11-22", pontos: 10, acumulado: 10 },
      { data: "2026-11-23", pontos: -5, acumulado: 5 },
    ],
  },
  {
    usuario_id: "b",
    nome: "Beto",
    total: -3,
    serie: [
      { data: "2026-11-22", pontos: 0, acumulado: 0 },
      { data: "2026-11-23", pontos: -3, acumulado: -3 },
    ],
  },
];

test("preserva os filtros existentes e usa séries só nos períodos suportados", () => {
  assert.equal(temSerieDiaria("semanal"), true);
  assert.equal(temSerieDiaria("mensal"), true);
  assert.equal(temSerieDiaria("anual"), false);
  assert.equal(temSerieDiaria("acumulado"), false);
});

test("seleção de dia usa os acumulados reais, incluindo estornos e zeros", () => {
  const primeiro = resumirDia(moradores, "2026-11-22");
  assert.equal(primeiro.indice, 0);
  assert.deepEqual(
    primeiro.totais.map((m) => m.pontos),
    [10, 0],
  );
  const ultimo = resumirDia(moradores);
  assert.equal(ultimo.indice, 1);
  assert.deepEqual(
    ultimo.totais.map((m) => m.pontos),
    [5, -3],
  );
  assert.deepEqual(resumirDia(moradores, "2026-10-01"), ultimo);
  assert.deepEqual(resumirDia([]), { datas: [], indice: -1, totais: [] });
});

test("escala comum mantém zero e barras negativas proporcionais", () => {
  const escala = escalaPontos([-10, 0, 30]);
  assert.equal(proporcaoPontos(-10, escala), 0);
  assert.equal(proporcaoPontos(0, escala), 0.25);
  assert.equal(proporcaoPontos(30, escala), 1);
  assert.equal(proporcaoPontos(0, escalaPontos([-10, -5])), 1);
  assert.equal(proporcaoPontos(0, escalaPontos([5, 10])), 0);
  assert.equal(proporcaoPontos(0, escalaPontos([0, 0])), 0);
  assert.equal(proporcaoPontos(0, escalaPontos([])), 0);
});

test("eixo de um único dia é centralizado e datas mantêm o dia civil", () => {
  assert.equal(posicaoDia(0, 1), 0.5);
  assert.equal(posicaoDia(0, 7), 0);
  assert.equal(posicaoDia(6, 7), 1);
  assert.equal(rotuloDia("2026-11-22"), "22/11");
});

test("consulta desempenho da casa ativa com período, sessão e cancelamento", async (t) => {
  const anterior = process.env.EXPO_PUBLIC_API_URL;
  process.env.EXPO_PUBLIC_API_URL = "http://api.test";
  t.after(() => {
    if (anterior === undefined) delete process.env.EXPO_PUBLIC_API_URL;
    else process.env.EXPO_PUBLIC_API_URL = anterior;
  });
  const controlador = new AbortController();
  const fetch = t.mock.method(globalThis, "fetch", async () =>
    Response.json({ moradores }),
  );
  for (const periodo of ["semanal", "mensal", "semestral"]) {
    assert.deepEqual(await carregarDesempenho(periodo, controlador.signal), {
      moradores,
    });
    const [url, opcoes] = fetch.mock.calls.at(-1).arguments;
    assert.equal(
      url,
      `http://api.test/casas/casa-123/desempenho?periodo=${periodo}`,
    );
    assert.equal(opcoes.method, "GET");
    assert.equal(opcoes.headers.Authorization, "Bearer sessao-de-teste");
    assert.equal(opcoes.signal, controlador.signal);
  }
});
