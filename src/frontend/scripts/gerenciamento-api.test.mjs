import assert from "node:assert/strict";
import { mock, test, afterEach } from "node:test";

const chamadas = [];
let falha;
mock.module("../src/services/api.ts", {
  namedExports: {
    requisitar: async (...args) => {
      chamadas.push(args);
      if (falha) throw falha;
      return { id: "regra" };
    },
  },
});
const casas = await import("../src/services/casas-api.ts");
const regras = await import("../src/services/rotatividade-api.ts");
afterEach(() => {
  chamadas.length = 0;
  falha = undefined;
});

test("consulta regras exclusivamente da casa informada e preserva cancelamento", async () => {
  const signal = new AbortController().signal;
  await regras.listarRotatividades("casa a", signal);
  assert.deepEqual(chamadas, [["/rotatividades/?fk_casa_id=casa+a", signal]]);
});

test("cria, edita e remove regras pelo contrato existente", async () => {
  const dados = {
    fk_casa_id: "casa",
    nome: "Louça",
    peso: 2,
    prazo_dias: 2,
    atraso_maximo: 1,
    modo_prazo: "intervalo",
    participantes: ["a", "b"],
    dias_semana: [1, 3],
    intervalo_semanas: 2,
  };
  await regras.criarRotatividade(dados);
  await regras.atualizarRotatividade("r", {
    nome: "Novo",
    descricao: "",
    ativa: false,
  });
  await regras.excluirRotatividade("r");
  assert.deepEqual(chamadas, [
    ["/rotatividades/", undefined, { method: "POST", body: dados }],
    [
      "/rotatividades/r",
      undefined,
      { method: "PATCH", body: { nome: "Novo", descricao: "", ativa: false } },
    ],
    ["/rotatividades/r", undefined, { method: "DELETE" }],
  ]);
});

test("edita casa sem enviar dono e remove vínculo sem excluir usuário", async () => {
  await casas.atualizarCasa("c", {
    nome: " Casa ",
    endereco: " Rua ",
    timezone: " UTC ",
  });
  await casas.removerMoradorCasa("c", "u");
  await casas.excluirCasa("c");
  assert.deepEqual(chamadas, [
    [
      "/casas/c",
      undefined,
      {
        method: "PATCH",
        body: { nome: "Casa", endereco: "Rua", timezone: "UTC" },
      },
    ],
    ["/pertencer/u/c", undefined, { method: "DELETE" }],
    ["/casas/c", undefined, { method: "DELETE" }],
  ]);
});

for (const status of [401, 403, 409, 422])
  test(`preserva erro ${status} do backend para exibição`, async () => {
    falha = Object.assign(new Error("Validação do backend"), {
      status,
      validacoes: [{ loc: ["body", "nome"], msg: "Nome inválido" }],
    });
    await assert.rejects(
      regras.atualizarRotatividade("r", {
        nome: "",
        descricao: "",
        ativa: true,
      }),
      (erro) => erro === falha,
    );
    await assert.rejects(casas.excluirCasa("c"), (erro) => erro === falha);
  });
