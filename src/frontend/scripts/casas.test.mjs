import assert from "node:assert/strict";
import { afterEach, beforeEach, mock, test } from "node:test";

let tokenSalvo;
let casaSalva;
let salvarCasa;
mock.module("../src/services/token-storage.ts", {
  namedExports: {
    lerToken: async () => tokenSalvo,
    salvarToken: async (valor) => {
      tokenSalvo = valor;
    },
    removerToken: async () => {
      tokenSalvo = null;
    },
  },
});
mock.module("../src/services/casa-storage.ts", {
  namedExports: {
    lerCasaSelecionada: async () => casaSalva,
    salvarCasaSelecionada: async (valor) => {
      await salvarCasa(valor);
    },
    removerCasaSelecionada: async () => {
      casaSalva = null;
    },
  },
});

const { listarCasas, casaInicial, criarCasa } =
  await import("../src/services/casas-api.ts");
const {
  sessao,
  restaurarSessao,
  salvarSessao,
  selecionarCasa,
  trocarCasa,
  encerrarSessao,
} = await import("../src/services/sessao-store.ts");
const { carregarTarefas, carregarPlacar, carregarContextoTarefas } =
  await import("../src/services/tarefas-api.ts");
const { requisitar, ErroApi } = await import("../src/services/api.ts");
const fetchOriginal = globalThis.fetch;
const ambiente = { ...process.env };
const casa = (id) => ({
  id,
  nome: `Casa ${id}`,
  endereco: "Rua das Flores",
  foto: null,
  fk_usuario_id: "morador",
  timezone: "America/Sao_Paulo",
});
const resposta = (dados) => ({
  ok: true,
  status: 200,
  json: async () => dados,
});

beforeEach(() => {
  tokenSalvo = "sessao-teste";
  casaSalva = null;
  salvarCasa = async (id) => {
    casaSalva = id;
  };
  sessao.setState({
    token: tokenSalvo,
    pronta: true,
    casaAtiva: null,
    casaPreferidaId: null,
  });
  process.env.EXPO_PUBLIC_API_URL = "http://api.test";
  process.env.EXPO_PUBLIC_CASA_ID = "casa-legada";
});

afterEach(() => {
  globalThis.fetch = fetchOriginal;
  for (const nome of ["EXPO_PUBLIC_API_URL", "EXPO_PUBLIC_CASA_ID"]) {
    if (ambiente[nome] === undefined) delete process.env[nome];
    else process.env[nome] = ambiente[nome];
  }
});

test("zero casas mantém a escolha vazia; uma casa permite entrada automática", async () => {
  globalThis.fetch = async () => resposta([]);
  const vazia = await listarCasas();
  assert.deepEqual(vazia, []);
  assert.equal(casaInicial(vazia, null), null);
  assert.deepEqual(casaInicial([casa("a")], null), casa("a"));
});

test("várias casas exigem escolha, exceto quando a preferência ainda é acessível", () => {
  const casas = [casa("a"), casa("b")];
  assert.equal(casaInicial(casas, null), null);
  assert.equal(casaInicial(casas, "removida"), null);
  assert.deepEqual(casaInicial(casas, "b"), casa("b"));
  assert.deepEqual(casaInicial([casa("a")], "removida"), casa("a"));
});

test("lista todas as páginas com a credencial e o cancelamento da consulta", async () => {
  const sinal = new AbortController().signal;
  const paginas = [
    Array.from({ length: 100 }, (_, id) => casa(`${id}`)),
    [casa("ultima")],
  ];
  const chamadas = [];
  globalThis.fetch = async (url, opcoes) => {
    chamadas.push(url);
    assert.equal(opcoes.headers.Authorization, "Bearer sessao-teste");
    assert.equal(opcoes.signal, sinal);
    return resposta(paginas[chamadas.length - 1]);
  };
  const lista = await listarCasas(sinal);
  assert.equal(lista.length, 101);
  assert.deepEqual(chamadas, [
    "http://api.test/casas/?inicio=0&limite=100",
    "http://api.test/casas/?inicio=100&limite=100",
  ]);
  assert.deepEqual(casaInicial(lista, "ultima"), casa("ultima"));
});

test("restaura apenas a preferência; a casa não é liberada antes de consultar o acesso", async () => {
  casaSalva = "antiga";
  await restaurarSessao();
  assert.equal(sessao.getState().casaPreferidaId, "antiga");
  assert.equal(sessao.getState().casaAtiva, null);
  globalThis.fetch = async () => {
    throw new TypeError("Sem conexão");
  };
  await assert.rejects(listarCasas(), /Sem conexão/);
  assert.equal(sessao.getState().casaAtiva, null);
  globalThis.fetch = async () => resposta([casa("nova"), casa("outra")]);
  assert.equal(
    casaInicial(await listarCasas(), sessao.getState().casaPreferidaId),
    null,
  );
});

test("seleção e troca alimentam tarefas, moradores e placar sem usar a casa do ambiente", async () => {
  const chamadas = [];
  globalThis.fetch = async (url) => {
    chamadas.push(url);
    return resposta([]);
  };
  await selecionarCasa(casa("a"));
  await carregarTarefas({
    estado: "todos",
    prazo: "todos",
    responsavel: "todos",
  });
  trocarCasa();
  assert.equal(sessao.getState().casaAtiva, null);
  assert.equal(sessao.getState().token, "sessao-teste");
  await assert.rejects(carregarContextoTarefas(), /Escolha uma casa/);
  await selecionarCasa(casa("b"));
  await carregarContextoTarefas();
  await carregarPlacar();
  assert.deepEqual(chamadas, [
    "http://api.test/tarefas/casa/a?estado=todos&prazo=todos",
    "http://api.test/casas/b",
    "http://api.test/casas/b/moradores",
    "http://api.test/casas/b/placar",
  ]);
  assert.equal(casaSalva, "b");
});

test("falha ao salvar a seleção mantém a tela de escolha e permite nova tentativa", async () => {
  salvarCasa = async () => {
    throw new Error("Armazenamento indisponível");
  };
  await assert.rejects(selecionarCasa(casa("a")), /Armazenamento/);
  assert.equal(sessao.getState().casaAtiva, null);
  salvarCasa = async (id) => {
    casaSalva = id;
  };
  assert.equal(await selecionarCasa(casa("a")), true);
});

test("uma consulta cancelada não seleciona nem persiste a casa", async () => {
  const controlador = new AbortController();
  controlador.abort();
  assert.equal(await selecionarCasa(casa("a"), controlador.signal), false);
  assert.equal(casaSalva, null);
  assert.equal(sessao.getState().casaAtiva, null);
});

test("logout limpa a preferência mesmo quando a gravação da seleção já estava em andamento", async () => {
  let liberar;
  let iniciou;
  const inicio = new Promise((resolve) => {
    iniciou = resolve;
  });
  salvarCasa = async (id) => {
    iniciou();
    await new Promise((resolve) => {
      liberar = resolve;
    });
    casaSalva = id;
  };
  const escolha = selecionarCasa(casa("a"));
  await inicio;
  const logout = encerrarSessao();
  liberar();
  await Promise.all([escolha, logout]);
  assert.equal(casaSalva, null);
  assert.equal(tokenSalvo, null);
  assert.equal(sessao.getState().casaAtiva, null);
  assert.equal(sessao.getState().casaPreferidaId, null);
});

test("um novo login não herda a casa da sessão anterior nem aceita seleção enfileirada dela", async () => {
  await selecionarCasa(casa("a"));
  const login = salvarSessao("nova-sessao");
  const atrasada = selecionarCasa(casa("b"));
  await login;
  assert.equal(await atrasada, false);
  assert.equal(casaSalva, null);
  assert.equal(sessao.getState().casaAtiva, null);
  assert.equal(sessao.getState().casaPreferidaId, null);
});

test("sessão expirada apaga a casa ativa e a seleção persistida", async () => {
  await selecionarCasa(casa("a"));
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: "Sessão expirada" }),
  });
  await assert.rejects(requisitar("/casas/"), /Sessão expirada/);
  assert.equal(sessao.getState().token, null);
  assert.equal(sessao.getState().casaAtiva, null);
  assert.equal(casaSalva, null);
});

test("cria casa autenticada enviando só nome e endereço, com administrador definido pelo backend", async () => {
  const sinal = new AbortController().signal;
  const criada = { ...casa("nova"), fk_usuario_id: "usuario-autenticado" };
  let pedido;
  globalThis.fetch = async (url, opcoes) => {
    pedido = { url, opcoes };
    return { ...resposta(criada), status: 201 };
  };
  const resultado = await criarCasa(
    {
      nome: "  Casa nova  ",
      endereco: "  Rua das Flores, 10  ",
      fk_usuario_id: "nao-deve-ser-enviado",
    },
    sinal,
  );
  assert.equal(pedido.url, "http://api.test/casas/");
  assert.equal(pedido.opcoes.method, "POST");
  assert.equal(pedido.opcoes.headers.Authorization, "Bearer sessao-teste");
  assert.equal(pedido.opcoes.signal, sinal);
  assert.deepEqual(JSON.parse(pedido.opcoes.body), {
    nome: "Casa nova",
    endereco: "Rua das Flores, 10",
  });
  assert.deepEqual(resultado, criada);
});

test("validação 422 preserva os campos e mensagens sem reter o conteúdo enviado no erro", async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 422,
    json: async () => ({
      detail: [
        {
          loc: ["body", "nome"],
          msg: "Nome inválido.",
          input: "valor-enviado",
        },
        { loc: ["body", "endereco"], msg: "Endereço inválido." },
        { loc: ["body"], msg: "Confira os dados da casa." },
      ],
    }),
  });
  await assert.rejects(criarCasa({ nome: "Casa", endereco: "Rua" }), (erro) => {
    assert.ok(erro instanceof ErroApi);
    assert.equal(erro.status, 422);
    assert.deepEqual(erro.validacoes, [
      { loc: ["body", "nome"], msg: "Nome inválido." },
      { loc: ["body", "endereco"], msg: "Endereço inválido." },
      { loc: ["body"], msg: "Confira os dados da casa." },
    ]);
    assert.equal(
      erro.message,
      "Nome inválido. Endereço inválido. Confira os dados da casa.",
    );
    return true;
  });
});

test("erro geral de criação mantém a mensagem do backend e permite outra tentativa", async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 500,
    json: async () => ({ detail: "Erro ao vincular o proprietário à casa." }),
  });
  await assert.rejects(criarCasa({ nome: "Casa", endereco: "Rua" }), (erro) => {
    assert.equal(erro.message, "Erro ao vincular o proprietário à casa.");
    assert.deepEqual(erro.validacoes, []);
    return true;
  });
  assert.equal(sessao.getState().casaAtiva, null);
  globalThis.fetch = async () => resposta(casa("nova"));
  assert.deepEqual(
    await criarCasa({ nome: "Casa", endereco: "Rua" }),
    casa("nova"),
  );
});
