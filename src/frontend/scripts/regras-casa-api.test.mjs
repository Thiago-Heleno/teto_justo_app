import assert from "node:assert/strict";
import { afterEach, mock, test } from "node:test";

const chamadas = [];
let erroAtual;

mock.module("../src/services/api.ts", {
  namedExports: {
    requisitar: async (...args) => {
      chamadas.push(args);
      if (erroAtual) throw erroAtual;
      return args[2]?.method === "DELETE" && !args[0].endsWith("/pagar")
        ? undefined
        : { id: "resultado" };
    },
  },
});

const regrasApi = await import("../src/services/regras-casa-api.ts");
const {
  centavosParaEntrada,
  filtrarMultas,
  formatarCentavos,
  resumirMultas,
  valorParaCentavos,
} = await import("../src/utils/regras-casa.ts");

afterEach(() => {
  chamadas.length = 0;
  erroAtual = undefined;
});

test("consulta regras e multas exclusivamente da casa informada com cancelamento", async () => {
  const sinal = new AbortController().signal;
  await regrasApi.listarRegrasCasa("casa-1", sinal);
  await regrasApi.listarMultasCasa("casa-1", sinal);
  assert.deepEqual(chamadas, [
    ["/regras-casa/casa/casa-1", sinal],
    ["/regras-casa/casa/casa-1/multas", sinal],
  ]);
});

test("cria e edita regras da casa normalizando textos", async () => {
  await regrasApi.criarRegraCasa({
    fk_casa_id: "casa-1",
    titulo: "  Silêncio após 22h  ",
    descricao: "  Evitar barulho na sala  ",
    valor_multa_centavos: 2500,
  });
  await regrasApi.criarRegraCasa({
    fk_casa_id: "casa-1",
    titulo: "  Lixo  ",
    descricao: "   ",
    valor_multa_centavos: 1000,
  });
  await regrasApi.atualizarRegraCasa("regra-1", {
    titulo: "  Silêncio após 23h ",
    descricao: "",
    valor_multa_centavos: 3000,
    ativa: false,
  });
  assert.deepEqual(chamadas, [
    [
      "/regras-casa/",
      undefined,
      {
        method: "POST",
        body: {
          fk_casa_id: "casa-1",
          titulo: "Silêncio após 22h",
          descricao: "Evitar barulho na sala",
          valor_multa_centavos: 2500,
        },
      },
    ],
    [
      "/regras-casa/",
      undefined,
      {
        method: "POST",
        body: {
          fk_casa_id: "casa-1",
          titulo: "Lixo",
          valor_multa_centavos: 1000,
        },
      },
    ],
    [
      "/regras-casa/regra-1",
      undefined,
      {
        method: "PATCH",
        body: {
          titulo: "Silêncio após 23h",
          descricao: null,
          valor_multa_centavos: 3000,
          ativa: false,
        },
      },
    ],
  ]);
});

test("aplica multa e alterna pagamento usando os verbos esperados", async () => {
  await regrasApi.aplicarMultaCasa({
    fk_casa_id: "casa-1",
    fk_regra_id: "regra-1",
    fk_usuario_multado_id: "user-2",
    observacao: "  Som alto na madrugada  ",
  });
  await regrasApi.aplicarMultaCasa({
    fk_casa_id: "casa-1",
    fk_regra_id: "regra-1",
    fk_usuario_multado_id: "user-2",
    observacao: "   ",
  });
  await regrasApi.definirMultaPaga("multa-1", true);
  await regrasApi.definirMultaPaga("multa-1", false);
  assert.deepEqual(chamadas, [
    [
      "/regras-casa/multas",
      undefined,
      {
        method: "POST",
        body: {
          fk_casa_id: "casa-1",
          fk_regra_id: "regra-1",
          fk_usuario_multado_id: "user-2",
          observacao: "Som alto na madrugada",
        },
      },
    ],
    [
      "/regras-casa/multas",
      undefined,
      {
        method: "POST",
        body: {
          fk_casa_id: "casa-1",
          fk_regra_id: "regra-1",
          fk_usuario_multado_id: "user-2",
        },
      },
    ],
    ["/regras-casa/multas/multa-1/pagar", undefined, { method: "POST" }],
    ["/regras-casa/multas/multa-1/pagar", undefined, { method: "DELETE" }],
  ]);
});

test("exclusões de regra e multa usam DELETE e aceitam resposta vazia", async () => {
  assert.equal(await regrasApi.excluirRegraCasa("regra-1"), undefined);
  assert.equal(await regrasApi.excluirMultaCasa("multa-1"), undefined);
  assert.deepEqual(chamadas, [
    ["/regras-casa/regra-1", undefined, { method: "DELETE" }],
    ["/regras-casa/multas/multa-1", undefined, { method: "DELETE" }],
  ]);
});

for (const status of [403, 409, 422]) {
  test(`propaga erro ${status} do backend sem mascarar mensagens`, async () => {
    erroAtual = Object.assign(new Error("Operação negada."), { status });
    await assert.rejects(
      regrasApi.excluirRegraCasa("regra-1"),
      (erro) => erro === erroAtual,
    );
  });
}

test("converte valores monetários válidos para centavos e rejeita inválidos", () => {
  assert.equal(valorParaCentavos("25"), 2500);
  assert.equal(valorParaCentavos(" 25,5 "), 2550);
  assert.equal(valorParaCentavos("25,50"), 2550);
  assert.equal(valorParaCentavos("25.50"), 2550);
  assert.equal(valorParaCentavos("R$ 10,05"), 1005);
  assert.equal(valorParaCentavos("0,50"), 50);

  for (const invalido of [
    "",
    "   ",
    "0",
    "0,00",
    "-10",
    "10,123",
    "10.5.2",
    "abc",
    "21474837",
  ]) {
    assert.equal(
      valorParaCentavos(invalido),
      null,
      `Deveria rejeitar ${invalido}`,
    );
  }
});

test("formata centavos em real brasileiro e prepara entrada de edição", () => {
  assert.equal(formatarCentavos(2550).replace(/\u00a0/g, " "), "R$ 25,50");
  assert.equal(formatarCentavos(0).replace(/\u00a0/g, " "), "R$ 0,00");
  assert.equal(centavosParaEntrada(2550), "25,50");
  assert.equal(centavosParaEntrada(50), "0,50");
});

test("filtra e resume multas preservando ordem da API", () => {
  const multas = [
    {
      id: "m1",
      fk_usuario_multado_id: "u1",
      valor_centavos: 2500,
      paga: false,
    },
    {
      id: "m2",
      fk_usuario_multado_id: "u2",
      valor_centavos: 1500,
      paga: true,
    },
    {
      id: "m3",
      fk_usuario_multado_id: "u1",
      valor_centavos: 1000,
      paga: false,
    },
    {
      id: "m4",
      fk_usuario_multado_id: "u2",
      valor_centavos: 500,
      paga: false,
    },
  ];

  assert.deepEqual(filtrarMultas(multas, "todas"), multas);
  assert.deepEqual(filtrarMultas(multas, "pendentes"), [
    multas[0],
    multas[2],
    multas[3],
  ]);
  assert.deepEqual(filtrarMultas(multas, "pagas"), [multas[1]]);

  assert.deepEqual(resumirMultas(multas, "u1"), {
    totalPendenteCentavos: 4000,
    totalPagoCentavos: 1500,
    quantidadePendentes: 3,
    minhasPendentesCentavos: 3500,
    minhasPendentesCount: 2,
  });
});
