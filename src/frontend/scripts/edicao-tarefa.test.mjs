import assert from "node:assert/strict";
import test from "node:test";

import { prepararEdicaoTarefa } from "../src/utils/edicao-tarefa.ts";

const tarefa = {
  id: "tarefa-1",
  nome: "Lavar louça",
  descricao: "Louça do jantar",
  estado_atual: "pendente",
  peso: 1,
  tipo: "unitaria",
  modo_prazo: "intervalo",
  prazo_dias: 3,
  atraso_maximo: 2,
  data_fixa: null,
  data_fim: "2026-10-01T12:00:00Z",
  usuarios_atribuidos: ["morador-1"],
};
const moradores = [{ id: "morador-1" }, { id: "morador-2" }];
const formulario = {
  nome: "  Lavar e secar a louça  ",
  descricao: "  Louça do jantar e panelas  ",
  peso: 3,
  prazoDias: 5,
  atrasoMaximo: 4,
  dataFixa: "",
  responsavel: "morador-2",
};

test("PATCH usa duração e tolerância, nunca data_fim", () => {
  const resultado = prepararEdicaoTarefa(formulario, tarefa, moradores);
  assert.deepEqual(resultado.erros, {});
  assert.deepEqual(resultado.dados, {
    nome: "Lavar e secar a louça",
    descricao: "Louça do jantar e panelas",
    peso: 3,
    prazo_dias: 5,
    atraso_maximo: 4,
    usuarios_atribuidos: ["morador-2"],
  });
  assert.equal("data_fim" in resultado.dados, false);
});

test("data fixa usa data local ISO somente se for alterada", () => {
  const fixa = { ...tarefa, modo_prazo: "dia_fixo", data_fixa: "2026-10-01" };
  assert.equal(prepararEdicaoTarefa({ ...formulario, dataFixa: "2026-10-03" }, fixa, moradores).dados.data_fixa, "2026-10-03");
  assert.equal("data_fixa" in prepararEdicaoTarefa({ ...formulario, dataFixa: "2026-10-01" }, fixa, moradores).dados, false);
  assert.ok(prepararEdicaoTarefa({ ...formulario, dataFixa: "2026-02-30" }, fixa, moradores).erros.dataFixa);
});

test("rejeita nome vazio e responsável de outra casa", () => {
  const resultado = prepararEdicaoTarefa({ ...formulario, nome: " ", responsavel: "externo" }, tarefa, moradores);
  assert.equal(resultado.dados, undefined);
  assert.match(resultado.erros.nome, /nome/);
  assert.match(resultado.erros.responsavel, /desta casa/);
});
