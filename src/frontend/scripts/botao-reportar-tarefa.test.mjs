import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import { runInNewContext } from "node:vm";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import ts from "typescript";

import * as permissao from "../src/utils/pode-reportar-tarefa.ts";

const require = createRequire(import.meta.url);
const codigo = ts.transpileModule(
  readFileSync(
    new URL("../src/components/botao-reportar-tarefa.tsx", import.meta.url),
    "utf8",
  ),
  {
    compilerOptions: {
      jsx: ts.JsxEmit.ReactJSX,
      module: ts.ModuleKind.CommonJS,
    },
  },
).outputText;

function renderizar(props, api = {}) {
  let botao;
  const modulo = { exports: {} };
  const mocks = {
    "react-native": {
      StyleSheet: { create: (styles) => styles },
      Text: ({ children }) => React.createElement("span", null, children),
      useWindowDimensions: () => ({ width: 800 }),
    },
    "lucide-react-native": { TriangleAlert: () => null },
    "@/components/motion-pressable": {
      MotionPressable: (props) => {
        botao = props;
        return React.createElement("button", null, props.children);
      },
    },
    "@/constants/theme": {
      Caldera: { ember: "#fc5000", obsidian: "#070607", chalk: "#ffffff" },
      Spacing: { two: 8, four: 16 },
    },
    "@/services/tarefas-api": api,
    "@/utils/pode-reportar-tarefa": permissao,
  };
  runInNewContext(codigo, {
    exports: modulo.exports,
    require: (nome) => mocks[nome] ?? require(nome),
  });
  const html = renderToStaticMarkup(
    React.createElement(modulo.exports.BotaoReportarTarefa, {
      tarefaId: "tarefa-1",
      concluidaEm: new Date().toISOString(),
      politica: "votacao",
      ehResponsavel: false,
      votosAtuais: 1,
      votosPossiveis: 3,
      ...props,
    }),
  );
  return {
    botao,
    html,
    style: Object.assign({}, ...botao.style.filter(Boolean)),
  };
}

test("sem voto fica apagado mesmo com votos de outros moradores", () => {
  const { botao, html, style } = renderizar({ usuarioReclamou: false });
  assert.match(html, /Reportar.*1\/3/);
  assert.equal(botao.accessibilityState.selected, false);
  assert.equal(botao.disabled, false);
  assert.equal(style.backgroundColor, undefined);
  assert.equal(style.borderColor, "#070607");
});

test("voto carregado da API fica aceso e permite retirar ao reabrir a tela", () => {
  const { botao, html, style } = renderizar({ usuarioReclamou: true });
  assert.match(html, /Reportado.*1\/3/);
  assert.equal(botao.accessibilityState.selected, true);
  assert.equal(botao.disabled, false);
  assert.equal(botao.accessibilityHint, "Retirar meu voto");
  assert.equal(style.backgroundColor, "#fc5000");
});

for (const votou of [false, true]) {
  test(`${votou ? "retira" : "envia"} voto e devolve resposta confirmada sem duplicar clique`, async () => {
    let confirmar;
    const pendente = new Promise((resolve) => {
      confirmar = resolve;
    });
    const chamadas = [];
    const respostas = [];
    const concluidaEm = new Date().toISOString();
    const api = Object.fromEntries(
      ["reportarTarefa", "retirarReportTarefa"].map((acao) => [
        acao,
        (...args) => {
          chamadas.push([acao, ...args]);
          return pendente;
        },
      ]),
    );
    const { botao } = renderizar(
      {
        usuarioReclamou: votou,
        concluidaEm,
        onReportada: (tarefa) => respostas.push(tarefa),
      },
      api,
    );
    const envio = botao.onPress();
    await botao.onPress();
    assert.equal(respostas.length, 0);
    assert.deepEqual(chamadas, [
      [
        votou ? "retirarReportTarefa" : "reportarTarefa",
        "tarefa-1",
        concluidaEm,
      ],
    ]);
    const resultado = {
      usuario_reclamou: !votou,
      reclamacoes_count: votou ? 0 : 2,
    };
    confirmar(resultado);
    await envio;
    assert.deepEqual(respostas, [resultado]);
  });
}
