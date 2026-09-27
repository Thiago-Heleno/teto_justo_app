import assert from "node:assert/strict";
import test from "node:test";
import { prepararTarefa } from "../src/utils/criacao-tarefa.ts";

const moradores = [{ id: "ana" }, { id: "bruno" }, { id: "carla" }];
const formulario = {
  nome: "  Limpar cozinha  ",
  descricao: "  Limpar bancada  ",
  peso: 2,
  dias: 3,
  atrasoMaximo: 2,
  modoPrazo: "intervalo",
  dataFixa: "",
  responsavel: "ana",
  rotativa: false,
  participantes: [],
  diasSemana: [],
  semanas: 1,
};
const preparar = (alteracoes = {}) =>
  prepararTarefa({ ...formulario, ...alteracoes }, moradores);

test("tarefa comum mantém um responsável e descarta campos ocultos do rodízio", () => {
  const { tarefa, erros } = preparar({
    participantes: ["bruno", "carla"],
    diasSemana: [1],
  });
  assert.deepEqual(erros, {});
  assert.equal(tarefa.nome, "Limpar cozinha");
  assert.equal(tarefa.descricao, "Limpar bancada");
  assert.equal(tarefa.atraso_maximo, 2);
  assert.equal(tarefa.modo_prazo, "intervalo");
  assert.deepEqual(tarefa.usuarios_atribuidos, ["ana"]);
  assert.equal(tarefa.rotatividade, null);
});

test("rodízio preserva a ordem dos moradores e guarda dias semanais separados do prazo", () => {
  const participantes = ["carla", "ana", "bruno"];
  const { tarefa, erros } = preparar({
    rotativa: true,
    participantes,
    diasSemana: [1],
    responsavel: null,
  });
  assert.deepEqual(erros, {});
  assert.equal(tarefa.prazo_dias, 3);
  assert.deepEqual(tarefa.usuarios_atribuidos, ["carla"]);
  assert.deepEqual(tarefa.rotatividade, {
    participantes: ["carla", "ana", "bruno"],
    dias_semana: [1],
    intervalo_semanas: 1,
  });
  participantes.reverse();
  assert.deepEqual(tarefa.rotatividade.participantes, [
    "carla",
    "ana",
    "bruno",
  ]);
});

test("rodízio exige dois moradores diferentes da casa", () => {
  for (const participantes of [
    [],
    ["ana"],
    ["ana", "ana"],
    ["ana", "externo"],
  ]) {
    const resultado = preparar({
      rotativa: true,
      participantes,
      diasSemana: [1],
    });
    assert.ok(resultado.erros.participantes);
    assert.equal(resultado.tarefa, undefined);
  }
});

test("recorrência exige ao menos um dia válido e rejeita dias repetidos", () => {
  for (const diasSemana of [[], [0], [8], [-1], [1.5], ["1"], [1, 1], [NaN]]) {
    const resultado = preparar({
      rotativa: true,
      participantes: ["ana", "bruno"],
      diasSemana,
    });
    assert.ok(resultado.erros.diasSemana);
    assert.equal(resultado.tarefa, undefined);
  }
});

test("recorrência aceita um ou vários dias e os organiza de segunda a domingo", () => {
  const diasSemana = [7, 4, 1];
  const resultado = preparar({
    rotativa: true,
    participantes: ["ana", "bruno"],
    diasSemana,
  });
  assert.deepEqual(resultado.erros, {});
  assert.deepEqual(resultado.tarefa.rotatividade.dias_semana, [1, 4, 7]);
  assert.deepEqual(diasSemana, [7, 4, 1]);
  diasSemana.push(2);
  assert.deepEqual(resultado.tarefa.rotatividade.dias_semana, [1, 4, 7]);
  for (const dia of [1, 2, 3, 4, 5, 6, 7]) {
    assert.deepEqual(
      preparar({
        rotativa: true,
        participantes: ["ana", "bruno"],
        diasSemana: [dia],
      }).tarefa.rotatividade.dias_semana,
      [dia],
    );
  }
});

test("erros obrigatórios não produzem tarefa nem alteram os valores do formulário", () => {
  const entrada = {
    ...formulario,
    nome: "  ",
    peso: null,
    dias: null,
    responsavel: null,
  };
  const copia = structuredClone(entrada);
  const resultado = prepararTarefa(entrada, moradores);
  assert.deepEqual(Object.keys(resultado.erros).sort(), [
    "nome",
    "peso",
    "prazo",
    "responsavel",
  ]);
  assert.equal(resultado.tarefa, undefined);
  assert.deepEqual(entrada, copia);
});

test("trocar para comum exige responsável próprio e moradores válidos", () => {
  assert.ok(
    preparar({
      responsavel: null,
      participantes: ["ana", "bruno"],
      diasSemana: [1],
    }).erros.responsavel,
  );
  assert.ok(preparar({ responsavel: "externo" }).erros.responsavel);
  assert.ok(prepararTarefa(formulario, []).erros.responsavel);
});

test("repetição aceita de 1 a 4 semanas sem alterar os dias nem os participantes", () => {
  for (const semanas of [1, 2, 3, 4]) {
    const { tarefa, erros } = preparar({
      rotativa: true,
      participantes: ["bruno", "ana"],
      diasSemana: [4, 1],
      semanas,
    });
    assert.deepEqual(erros, {});
    assert.deepEqual(tarefa.rotatividade, {
      participantes: ["bruno", "ana"],
      dias_semana: [1, 4],
      intervalo_semanas: semanas,
    });
    assert.equal(tarefa.prazo_dias, 3);
  }
  for (const semanas of [0, -1, 5, 1.5, "2", null, undefined, NaN]) {
    const resultado = preparar({
      rotativa: true,
      participantes: ["ana", "bruno"],
      diasSemana: [1],
      semanas,
    });
    assert.ok(resultado.erros.semanas);
    assert.equal(resultado.tarefa, undefined);
  }
  assert.equal(preparar({ semanas: 0 }).tarefa.rotatividade, null);
});

test("dia fixo unitário exige data válida e não altera agendamento de rodízio", () => {
  assert.ok(preparar({ modoPrazo: "dia_fixo", dataFixa: "2026-02-30" }).erros.dataFixa);
  assert.equal(preparar({ modoPrazo: "dia_fixo", dataFixa: "2026-10-05" }).tarefa.data_fixa, "2026-10-05");
  const rotativa = preparar({ rotativa: true, responsavel: null, participantes: ["ana", "bruno"], diasSemana: [1], modoPrazo: "dia_fixo" });
  assert.deepEqual(rotativa.erros, {});
  assert.equal(rotativa.tarefa.data_fixa, undefined);
});

test("tolerância fora do intervalo 1 a 5 impede criação", () => {
  for (const atrasoMaximo of [null, 0, 6, 1.5]) {
    const resultado = preparar({ atrasoMaximo });
    assert.ok(resultado.erros.atrasoMaximo);
    assert.equal(resultado.tarefa, undefined);
  }
});
