import assert from "node:assert/strict";
import test from "node:test";

import {
  agruparTarefasAtivas,
  dataNoFuso,
  diasDoMes,
  mudarMes,
} from "../src/utils/calendario-tarefas.ts";

const fuso = "America/Sao_Paulo";

test("calendário alinha domingos e inclui todos os dias em meses de quatro a seis semanas", () => {
  const fevereiro = diasDoMes("2026-02");
  assert.equal(fevereiro.length, 28);
  assert.equal(fevereiro[0], "2026-02-01");
  assert.equal(fevereiro.at(-1), "2026-02-28");

  const bissexto = diasDoMes("2024-02");
  assert.equal(bissexto.length, 35);
  assert.deepEqual(bissexto.slice(0, 4), [null, null, null, null]);
  assert.equal(bissexto[32], "2024-02-29");
  assert.deepEqual(bissexto.slice(33), [null, null]);

  const agosto = diasDoMes("2026-08");
  assert.equal(agosto.length, 42);
  assert.equal(agosto[6], "2026-08-01");
  assert.equal(agosto[36], "2026-08-31");
  assert.equal(agosto.filter(Boolean).length, 31);
});

test("navegação atravessa anos e fevereiro sem pular meses", () => {
  assert.equal(mudarMes("2026-12", 1), "2027-01");
  assert.equal(mudarMes("2026-01", -1), "2025-12");
  assert.equal(mudarMes("2024-01", 1), "2024-02");
  assert.equal(mudarMes("2024-03", -1), "2024-02");
});

test("hoje e prazos usam o dia da casa, inclusive perto da meia-noite e em horário de verão", () => {
  const instante = "2027-01-01T01:30:00Z";
  assert.equal(dataNoFuso(instante, fuso), "2026-12-31");
  assert.equal(dataNoFuso(instante, "Asia/Tokyo"), "2027-01-01");
  assert.equal(dataNoFuso(new Date(instante), fuso), "2026-12-31");
  assert.equal(
    dataNoFuso("2026-07-01T04:30:00Z", "America/New_York"),
    "2026-07-01",
  );
  assert.equal(
    dataNoFuso("2026-01-01T04:30:00Z", "America/New_York"),
    "2025-12-31",
  );
});

test("agrupa somente pendentes e atrasadas pelo prazo e mantém todos os responsáveis", () => {
  const tarefas = [
    {
      id: "tarde",
      estado_atual: "pendente",
      data_fim: "2026-10-18T20:00:00Z",
      usuarios_atribuidos: ["ana"],
    },
    {
      id: "concluida",
      estado_atual: "finalizado",
      data_fim: "2026-10-18T12:00:00Z",
      usuarios_atribuidos: ["ana"],
    },
    {
      id: "nao-feita",
      estado_atual: "nao_feito",
      data_fim: "2026-10-18T12:00:00Z",
      usuarios_atribuidos: ["bruno"],
    },
    {
      id: "cedo",
      estado_atual: "atrasada",
      data_fim: "2026-10-18T10:00:00Z",
      usuarios_atribuidos: ["bruno"],
    },
    {
      id: "outro-mes",
      estado_atual: "pendente",
      data_fim: "2026-11-02T20:00:00Z",
      usuarios_atribuidos: [],
    },
  ];
  const original = structuredClone(tarefas);
  const grupos = agruparTarefasAtivas(tarefas, fuso);

  assert.deepEqual([...grupos.keys()], ["2026-10-18", "2026-11-02"]);
  assert.deepEqual(
    grupos.get("2026-10-18").map(({ id }) => id),
    ["cedo", "tarde"],
  );
  assert.deepEqual(
    grupos
      .get("2026-10-18")
      .map(({ usuarios_atribuidos }) => usuarios_atribuidos),
    [["bruno"], ["ana"]],
  );
  assert.deepEqual(tarefas, original);
});

test("respeita data fixa e agrupa intervalo pelo vencimento, sem expandir duração ou rodízios", () => {
  const grupos = agruparTarefasAtivas(
    [
      {
        id: "fixa",
        estado_atual: "pendente",
        data_fixa: "2026-10-02",
        data_fim: "2026-10-03T02:59:59Z",
      },
      {
        id: "intervalo",
        estado_atual: "pendente",
        data_fixa: null,
        data_inicio: "2026-09-28T00:00:00Z",
        data_fim: "2026-10-03T02:30:00Z",
        tipo: "rotativa",
      },
    ],
    fuso,
  );

  assert.deepEqual([...grupos.keys()], ["2026-10-02"]);
  assert.deepEqual(
    grupos.get("2026-10-02").map(({ id }) => id),
    ["intervalo", "fixa"],
  );
  assert.equal(
    agruparTarefasAtivas(
      [
        {
          estado_atual: "pendente",
          data_fixa: "2026-10-02",
          data_fim: "2026-10-03T02:59:59Z",
        },
      ],
      "Asia/Tokyo",
    ).has("2026-10-02"),
    true,
  );
});

test("casa sem tarefas ativas produz agenda vazia", () => {
  assert.equal(agruparTarefasAtivas([], fuso).size, 0);
  assert.equal(
    agruparTarefasAtivas(
      [
        { estado_atual: "finalizado", data_fim: "2026-10-18T12:00:00Z" },
        { estado_atual: "nao_feito", data_fim: "2026-10-18T12:00:00Z" },
      ],
      fuso,
    ).size,
    0,
  );
});
