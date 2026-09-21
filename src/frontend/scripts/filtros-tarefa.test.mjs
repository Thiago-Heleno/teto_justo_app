import assert from "node:assert/strict";
import test from "node:test";

import { filtrarTarefas } from "../src/utils/filtros-tarefa.ts";

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
      { estado: "todos", responsavel: "ana", prazo: "atrasadas" },
      agora,
    ).map(({ id }) => id),
    ["atrasada"],
  );
});
