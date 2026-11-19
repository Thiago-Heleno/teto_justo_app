import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import ts from "typescript";

class ErroApiTeste extends Error {
  constructor(mensagem, status, validacoes = []) {
    super(mensagem);
    this.status = status;
    this.validacoes = validacoes;
  }
}

const require = createRequire(import.meta.url);
const codigo = ts.transpileModule(
  readFileSync(
    new URL("../src/hooks/use-gerenciamento-casa.ts", import.meta.url),
    "utf8",
  ),
  { compilerOptions: { module: ts.ModuleKind.CommonJS } },
).outputText;

const modulo = { exports: {} };
const mocks = {
  "expo-router": { useFocusEffect: () => {} },
  react: { useCallback: (fn) => fn, useRef: () => ({}), useState: () => [] },
  zustand: { useStore: () => ({}) },
  "@/services/api": { ErroApi: ErroApiTeste },
  "@/services/casas-api": {},
  "@/services/sessao-store": { sessao: {} },
  "@/services/tarefas-api": {},
};

runInNewContext(codigo, {
  Error,
  TypeError,
  exports: modulo.exports,
  require: (nome) => mocks[nome] ?? require(nome),
});

const { mensagemGerenciamento } = modulo.exports;

test("mensagemGerenciamento formata erros de validação, rede e erro genérico", () => {
  const validacao = new ErroApiTeste("Erro", 422, [
    { loc: ["body", "nome"], msg: "campo obrigatório" },
    { loc: ["body"], msg: "dados inválidos" },
  ]);
  assert.equal(
    mensagemGerenciamento(validacao),
    "nome: campo obrigatório\nFormulário: dados inválidos",
  );

  assert.match(
    mensagemGerenciamento(new TypeError("Failed to fetch")),
    /Falha de conexão/,
  );
  assert.equal(
    mensagemGerenciamento(new ErroApiTeste("Sem permissão", 403)),
    "Sem permissão",
  );
  assert.equal(
    mensagemGerenciamento("desconhecido"),
    "Não foi possível concluir a operação.",
  );
});
