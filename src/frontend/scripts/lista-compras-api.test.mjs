import assert from "node:assert/strict";
import { afterEach, mock, test } from "node:test";

const chamadas = [];
let erroAtual;
mock.module("../src/services/api.ts", {
  namedExports: {
    requisitar: async (...args) => {
      chamadas.push(args);
      if (erroAtual) throw erroAtual;
      return args[2]?.method === "DELETE" && !args[0].endsWith("/comprado")
        ? undefined
        : { id: "resultado" };
    },
  },
});

const compras = await import("../src/services/lista-compras-api.ts");
const { agruparItensCompra, quantidadeValida } = await import("../src/utils/lista-compras.ts");

afterEach(() => {
  chamadas.length = 0;
  erroAtual = undefined;
});

test("consulta listas apenas da casa e itens apenas da lista, com cancelamento", async () => {
  const sinal = new AbortController().signal;
  await compras.listarListasCompra("casa-1", sinal);
  await compras.listarItensCompra("lista-2", sinal);
  assert.deepEqual(chamadas, [
    ["/lista/casa/casa-1", sinal],
    ["/lista/lista-2/itens", sinal],
  ]);
});

test("cria e renomeia listas sem enviar campos extras", async () => {
  await compras.criarListaCompra("casa-1", "  Mercado  ");
  await compras.renomearListaCompra("lista-2", "  Limpeza  ");
  assert.deepEqual(chamadas, [
    ["/lista/", undefined, { method: "POST", body: { fk_casa_id: "casa-1", nome: "Mercado" } }],
    ["/lista/lista-2", undefined, { method: "PATCH", body: { nome: "Limpeza" } }],
  ]);
});

test("cria e edita produtos informando nome e quantidade, sem identidade do usuário", async () => {
  await compras.criarItemCompra("lista-1", "  Detergente  ", 3);
  await compras.editarItemCompra("item-1", { nome: "  Sabão  ", quantidade: 2 });
  assert.deepEqual(chamadas, [
    ["/lista/itens", undefined, { method: "POST", body: { fk_lista_id: "lista-1", nome: "Detergente", quantidade: 3 } }],
    ["/lista/itens/item-1", undefined, { method: "PATCH", body: { nome: "Sabão", quantidade: 2 } }],
  ]);
});

test("marcar ou desmarcar comprado usa os verbos exigidos pelo backend", async () => {
  await compras.definirItemComprado("item-1", true);
  await compras.definirItemComprado("item-1", false);
  assert.deepEqual(chamadas, [
    ["/lista/itens/item-1/comprado", undefined, { method: "POST" }],
    ["/lista/itens/item-1/comprado", undefined, { method: "DELETE" }],
  ]);
});

test("exclusões usam rota de lista e item e aceitam resposta vazia", async () => {
  assert.equal(await compras.excluirListaCompra("lista-1"), undefined);
  assert.equal(await compras.excluirItemCompra("item-2"), undefined);
  assert.deepEqual(chamadas, [
    ["/lista/lista-1", undefined, { method: "DELETE" }],
    ["/lista/itens/item-2", undefined, { method: "DELETE" }],
  ]);
});

test("erros do backend são propagados sem mascarar permissões", async () => {
  erroAtual = Object.assign(new Error("Apenas o administrador pode excluir."), { status: 403 });
  await assert.rejects(compras.excluirListaCompra("lista-1"), (erro) => erro === erroAtual);
});

test("quantidades exigem inteiros positivos no intervalo do banco", () => {
  assert.equal(quantidadeValida(" 2 "), 2);
  for (const valor of ["", "0", "-1", "1.5", "1e2", "abc", "2147483648", "999999999999999999"]) {
    assert.equal(quantidadeValida(valor), null, `Deveria rejeitar ${valor}`);
  }
});

test("separa itens comprados dos pendentes sem perder a ordem da API", () => {
  const itens = [
    { id: "1", comprado: false },
    { id: "2", comprado: true },
    { id: "3", comprado: false },
  ];
  assert.deepEqual(agruparItensCompra(itens), {
    pendentes: [itens[0], itens[2]],
    comprados: [itens[1]],
  });
});
