import assert from "node:assert/strict";
import test from "node:test";
import { explicarPrazoTarefa, prepararTarefa } from "../src/utils/criacao-tarefa.ts";
import { formatarDataDigitada } from "../src/utils/data-fixa.ts";
import { anguloGiroRoleta, rotulosRoleta } from "../src/utils/roleta.ts";

test("a roda preserva o primeiro nome e distingue homônimos na legenda", () => {
  const rotulos = rotulosRoleta([
    "  João-Pedro Silva",
    "Ágata Reis",
    "Ágata Luz",
  ]);
  assert.deepEqual(rotulos, [
    { primeiro: "João-Pedro", legenda: "João-Pedro" },
    { primeiro: "Ágata", legenda: "Ágata Reis" },
    { primeiro: "Ágata", legenda: "Ágata Luz" },
  ]);
  assert.equal(rotulosRoleta(["Maximiliano Silva"])[0].primeiro, "Maximiliano");
});

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

test("explicação do intervalo acompanha o prazo selecionado e concorda com um dia", () => {
  for (const dias of [1, 2, 3, 4, 5]) {
    assert.equal(
      explicarPrazoTarefa("intervalo", dias, false),
      `A tarefa abre no dia atual e vence após ${dias} ${dias === 1 ? "dia" : "dias"}.`,
    );
  }
});

test("explicação solicita o prazo quando o intervalo ainda não foi selecionado", () => {
  assert.equal(
    explicarPrazoTarefa("intervalo", null, false),
    "Selecione o prazo para saber quando a tarefa vence.",
  );
});

test("explicação do dia fixo informa abertura e vencimento no próprio dia", () => {
  for (const dias of [null, 1, 3, 5]) {
    for (const rotativa of [false, true]) {
      assert.equal(
        explicarPrazoTarefa("dia_fixo", dias, rotativa),
        "A tarefa abre à meia-noite e vence no fim do dia escolhido.",
      );
    }
  }
});

test("explicação do intervalo no rodízio conta o dia de abertura no prazo", () => {
  assert.equal(
    explicarPrazoTarefa("intervalo", 3, true),
    "A tarefa abre no dia do rodízio e vence ao final de 3 dias, contando o dia de abertura.",
  );
});

test("tarefa comum sorteia sem exigir ou enviar um responsável manual", () => {
  for (const responsavel of [null, "ana"]) {
    const { tarefa, erros } = preparar({
      modoAtribuicao: "aleatorio",
      responsavel,
    });
    assert.deepEqual(erros, {});
    assert.equal(tarefa.modo_atribuicao, "aleatorio");
    assert.equal("usuarios_atribuidos" in tarefa, false);
  }
});

test("o centro da fatia sorteada para no ponteiro depois de três voltas", () => {
  const total = 7;
  for (let indice = 0; indice < total; indice++) {
    const giro = anguloGiroRoleta(indice, total);
    assert.ok(giro >= 1080 && giro < 1440);
    const posicaoFinal = giro + (indice * 360) / total;
    assert.ok(
      Math.abs(posicaoFinal / 360 - Math.round(posicaoFinal / 360)) < 1e-10,
    );
  }
  assert.equal(anguloGiroRoleta(-1, total), undefined);
  assert.equal(anguloGiroRoleta(0, 1), undefined);
});

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
    modoAtribuicao: "aleatorio",
    participantes,
    diasSemana: [1],
    responsavel: null,
  });
  assert.deepEqual(erros, {});
  assert.equal(tarefa.prazo_dias, 3);
  assert.deepEqual(tarefa.usuarios_atribuidos, ["carla"]);
  assert.equal("modo_atribuicao" in tarefa, false);
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

test("roleta habilitada segue na configuração do rodízio", () => {
  const { tarefa, erros } = preparar({
    rotativa: true,
    usarRoleta: true,
    participantes: ["ana", "bruno"],
    diasSemana: [1],
  });
  assert.deepEqual(erros, {});
  assert.equal(tarefa.rotatividade.usar_roleta, true);
  assert.equal(preparar({ usarRoleta: true }).tarefa.rotatividade, null);
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

test("máscara de data aceita digitação, colagem e exclusão", () => {
  let valor = "";
  for (const digito of "29022028") {
    valor = formatarDataDigitada(valor + digito);
  }
  assert.equal(valor, "29-02-2028");
  assert.equal(formatarDataDigitada("29/02/2028"), valor);
  assert.equal(formatarDataDigitada("2028-02-29"), valor);
  assert.equal(formatarDataDigitada("29-02-"), "29-02");
  assert.equal(formatarDataDigitada(""), "");
});

test("dia fixo unitário exige data válida e não altera agendamento de rodízio", () => {
  for (const dataFixa of ["", "29-02-20", "31-02-2028", "29-02-2027"]) {
    assert.ok(preparar({ modoPrazo: "dia_fixo", dataFixa }).erros.dataFixa);
  }
  assert.equal(
    preparar({ modoPrazo: "dia_fixo", dataFixa: "29-02-2028" }).tarefa
      .data_fixa,
    "2028-02-29",
  );
  const rotativa = preparar({
    rotativa: true,
    responsavel: null,
    participantes: ["ana", "bruno"],
    diasSemana: [1],
    modoPrazo: "dia_fixo",
  });
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
