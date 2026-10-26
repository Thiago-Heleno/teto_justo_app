import assert from "node:assert/strict";
import test from "node:test";

import { filtrarTarefas, formatarPrazo } from "../src/utils/filtros-tarefa.ts";

const agora = new Date("2026-09-20T12:00:00-03:00");
const tarefas = [
  {
    id: "hoje",
    estado_atual: "pendente",
    data_fim: "2026-09-20T18:00:00-03:00",
    usuarios_atribuidos: ["ana"],
  },
  {
    id: "semana",
    estado_atual: "pendente",
    data_fim: "2026-09-24T12:00:00-03:00",
    usuarios_atribuidos: ["bruno"],
  },
  {
    id: "atrasada",
    estado_atual: "atrasada",
    data_fim: "2026-09-19T12:00:00-03:00",
    usuarios_atribuidos: ["ana"],
  },
];

test("combina filtros de status, responsável e prazo", () => {
  assert.deepEqual(
    filtrarTarefas(
      tarefas,
      { estado: "pendente", responsavel: "ana", prazo: "hoje" },
      agora,
    ).map(({ id }) => id),
    ["hoje"],
  );
  assert.deepEqual(
    filtrarTarefas(
      tarefas,
      { estado: "todos", responsavel: "todos", prazo: "sete_dias" },
      agora,
    ).map(({ id }) => id),
    ["hoje", "semana"],
  );
  assert.deepEqual(
    filtrarTarefas(
      tarefas,
      { estado: "todos", responsavel: "ana", prazo: "antigas" },
      agora,
    ).map(({ id }) => id),
    ["atrasada"],
  );
});

test("dia fixo mostra a data da casa sem depender do fuso do aparelho", () => {
  assert.equal(
    formatarPrazo("2026-10-03T02:59:59Z", "2026-10-02"),
    "02 out. 2026, 23:59",
  );
});

test("prazo por intervalo usa o mesmo formato de data e inclui o ano", () => {
  assert.equal(formatarPrazo("2026-10-15T12:30:00"), "15 out. 2026, 12:30");
});

const limites = [
  ["ontem", "2026-10-31T23:59:59.999", "finalizado"],
  ["inicio-hoje", "2026-11-01T00:00:00", "atrasada"],
  ["fim-hoje", "2026-11-01T23:59:59.999", "pendente"],
  ["fim-setimo-dia", "2026-11-07T23:59:59.999", "pendente"],
  ["oitavo-dia", "2026-11-08T00:00:00", "pendente"],
].map(([id, data_fim, estado_atual]) => ({
  id,
  data_fim,
  estado_atual,
  usuarios_atribuidos: [],
}));

for (const [prazo, esperadas] of [
  ["antigas", ["ontem"]],
  ["hoje", ["inicio-hoje", "fim-hoje"]],
  ["sete_dias", ["inicio-hoje", "fim-hoje", "fim-setimo-dia"]],
  ["todos", limites.map(({ id }) => id)],
]) {
  test(`${prazo} filtra por dias completos, independentemente do estado`, () => {
    assert.deepEqual(
      filtrarTarefas(
        limites,
        { estado: "todos", responsavel: "todos", prazo },
        new Date("2026-11-01T12:00:00"),
      ).map(({ id }) => id),
      esperadas,
    );
  });
}
