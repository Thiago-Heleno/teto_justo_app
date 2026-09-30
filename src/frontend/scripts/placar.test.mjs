import assert from "node:assert/strict";
import test from "node:test";
import { resumirPlacar } from "../src/utils/placar.ts";

const placar = {
  casa_id: "casa",
  fuso_horario: "America/Sao_Paulo",
  moradores: [
    {
      usuario_id: "b",
      nome: "Bruna",
      semanal: 20,
      mensal: -10,
      anual: 80,
      acumulado: 120,
    },
    {
      usuario_id: "a",
      nome: "Ana",
      semanal: 20,
      mensal: 30,
      anual: 50,
      acumulado: 90,
    },
    {
      usuario_id: "c",
      nome: "Carlos",
      semanal: 0,
      mensal: 10,
      anual: 90,
      acumulado: 100,
    },
  ],
};

test("ordena pontos com empate, soma a casa e preserva resposta da API", () => {
  const original = structuredClone(placar);
  const resumo = resumirPlacar(placar, "semanal");
  assert.deepEqual(
    resumo.moradores.map((m) => [m.nome, m.posicao]),
    [
      ["Ana", 1],
      ["Bruna", 1],
      ["Carlos", 3],
    ],
  );
  assert.equal(resumo.total, 40);
  assert.deepEqual(placar, original);
});

test("usa o perÃ­odo escolhido, preservando pontos negativos e saldo acumulado", () => {
  const resumo = resumirPlacar(placar, "mensal");
  assert.deepEqual(
    resumo.moradores.map((m) => [m.nome, m.pontos]),
    [
      ["Ana", 30],
      ["Carlos", 10],
      ["Bruna", -10],
    ],
  );
  assert.equal(resumo.total, 30);
  assert.equal(resumo.moradores[2].acumulado, 120);
  assert.equal(resumirPlacar(placar, "anual").total, 220);
  assert.equal(resumirPlacar(placar, "acumulado").total, 310);
});

test("casa vazia e moradores sem pontos nÃ£o produzem dados fictÃ­cios", () => {
  assert.deepEqual(resumirPlacar({ ...placar, moradores: [] }, "semanal"), {
    moradores: [],
    total: 0,
  });
  const zeros = resumirPlacar(
    {
      ...placar,
      moradores: placar.moradores.map((m) => ({ ...m, semanal: 0 })),
    },
    "semanal",
  );
  assert.equal(zeros.total, 0);
  assert.deepEqual(
    zeros.moradores.map((m) => m.posicao),
    [1, 1, 1],
  );
});