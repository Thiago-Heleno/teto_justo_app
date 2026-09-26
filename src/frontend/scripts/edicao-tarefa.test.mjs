import assert from "node:assert/strict";
import test from "node:test";

import {
  dataTarefaParaCampo,
  prepararEdicaoTarefa,
} from "../src/utils/edicao-tarefa.ts";

const tarefa = {
  id: "tarefa-1",
  nome: "Lavar louça",
  descricao: "Louça do jantar",
  estado_atual: "pendente",
  peso: 1,
  data_fim: "2026-10-01T12:00:00Z",
  usuarios_atribuidos: ["morador-1"],
};
const moradores = [{ id: "morador-1" }, { id: "morador-2" }];

test("prepara os campos aceitos pelo PATCH de tarefa", () => {
  const resultado = prepararEdicaoTarefa(
    {
      nome: "  Lavar e secar a louça  ",
      descricao: "  Louça do jantar e panelas  ",
      peso: 3,
      dataFim: "2026-10-03",
      responsavel: "morador-2",
    },
    tarefa,
    moradores,
    new Date("2026-09-26T12:00:00Z"),
  );

  assert.deepEqual(resultado.erros, {});
  assert.deepEqual(resultado.dados, {
    nome: "Lavar e secar a louça",
    descricao: "Louça do jantar e panelas",
    peso: 3,
    data_fim: "2026-10-03T23:59:59.999Z",
    usuarios_atribuidos: ["morador-2"],
  });
});

test("preserva o instante original quando a data não muda", () => {
  const resultado = prepararEdicaoTarefa(
    {
      nome: tarefa.nome,
      descricao: tarefa.descricao,
      peso: 1,
      dataFim: dataTarefaParaCampo(tarefa.data_fim),
      responsavel: "morador-1",
    },
    tarefa,
    moradores,
    new Date("2026-10-02T12:00:00Z"),
  );

  assert.equal(resultado.dados?.data_fim, tarefa.data_fim);
});

test("rejeita nome vazio, data inválida e responsável de outra casa", () => {
  const resultado = prepararEdicaoTarefa(
    {
      nome: "   ",
      descricao: "",
      peso: 2,
      dataFim: "2026-02-30",
      responsavel: "desconhecido",
    },
    tarefa,
    moradores,
  );

  assert.equal(resultado.dados, undefined);
  assert.match(resultado.erros.nome, /nome/);
  assert.match(resultado.erros.dataFim, /data válida/);
  assert.match(resultado.erros.responsavel, /desta casa/);
});
