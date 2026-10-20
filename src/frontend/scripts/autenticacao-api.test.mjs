import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import { afterEach, beforeEach, mock, test } from "node:test";

let tokenSalvo = null;
let falhaArmazenamento = false;
let remocoesPush = 0;
mock.module("../src/services/notificacoes.ts", {
  namedExports: {
    removerNotificacoesDoDispositivo: async () => {
      remocoesPush += 1;
    },
  },
});
mock.module("../src/services/casa-storage.ts", {
  namedExports: {
    lerCasaSelecionada: async () => null,
    salvarCasaSelecionada: async () => {},
    removerCasaSelecionada: async () => {},
  },
});
mock.module("../src/services/token-storage.ts", {
  namedExports: {
    lerToken: async () => tokenSalvo,
    salvarToken: async (token) => {
      if (falhaArmazenamento) throw new Error("Armazenamento indisponível");
      tokenSalvo = token;
    },
    removerToken: async () => {
      tokenSalvo = null;
    },
  },
});

const {
  cadastrar,
  entrar,
  sair,
  iniciarAutenticacao,
  solicitarCodigoVerificacao,
} = await import("../src/services/autenticacao-api.ts");
const { atualizarPerfil, excluirConta } =
  await import("../src/services/perfil-api.ts");
const { requisitar } = await import("../src/services/api.ts");
const { sessao } = await import("../src/services/sessao-store.ts");
const { validarCadastro, somenteDigitosDoCodigo } =
  await import("../src/utils/cadastro.ts");
const fetchOriginal = globalThis.fetch;
const ambiente = { ...process.env };
const novoToken = () => randomBytes(32).toString("base64url");
const conta = () => ({
  nome: "Moradora",
  email: "moradora@example.com",
  senha: novoToken(),
});

beforeEach(() => {
  tokenSalvo = null;
  falhaArmazenamento = false;
  remocoesPush = 0;
  sessao.setState({
    token: null,
    pronta: false,
    casaAtiva: null,
    casaPreferidaId: null,
    restaurarCasa: true,
  });
  process.env.EXPO_PUBLIC_API_URL = "http://api.test/";
});

afterEach(() => {
  globalThis.fetch = fetchOriginal;
  for (const nome of [
    "EXPO_PUBLIC_API_URL",
    "EXPO_PUBLIC_CASA_ID",
    "EXPO_PUBLIC_TETO_JUSTO_TOKEN",
  ]) {
    if (ambiente[nome] === undefined) delete process.env[nome];
    else process.env[nome] = ambiente[nome];
  }
});

test("login envia credenciais e salva somente o token recebido em execução", async () => {
  const senha = novoToken();
  const token = novoToken();
  process.env.EXPO_PUBLIC_TETO_JUSTO_TOKEN = novoToken();
  delete process.env.EXPO_PUBLIC_CASA_ID;
  let pedido;
  globalThis.fetch = async (url, opcoes) => {
    pedido = { url, opcoes };
    return {
      ok: true,
      status: 200,
      json: async () => ({ token, expira_em: new Date().toISOString() }),
    };
  };

  await entrar(" morador@example.com ", senha);

  assert.equal(pedido.url, "http://api.test/sessoes/login");
  assert.equal(pedido.opcoes.method, "POST");
  assert.equal(pedido.opcoes.headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(pedido.opcoes.body), {
    email: "morador@example.com",
    senha,
  });
  assert.equal(tokenSalvo, token);
  assert.equal(sessao.getState().token, token);
});

test("pedido de código envia os dados do cadastro, sem sessão, e devolve o token", async () => {
  const senha = novoToken();
  let pedido;
  globalThis.fetch = async (url, opcoes) => {
    pedido = { url, opcoes };
    return {
      ok: true,
      status: 200,
      json: async () => ({ token_verificacao: "token-de-teste", expira_em: "x" }),
    };
  };

  const token = await solicitarCodigoVerificacao({
    nome: "  Moradora  ",
    email: "  moradora@example.com  ",
    senha,
  });

  assert.equal(token, "token-de-teste");
  assert.equal(pedido.url, "http://api.test/usuarios/codigo-verificacao");
  assert.equal(pedido.opcoes.method, "POST");
  assert.equal(pedido.opcoes.headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(pedido.opcoes.body), {
    nome: "Moradora",
    email: "moradora@example.com",
    senha,
  });
  assert.equal(sessao.getState().token, null);
});

test("cadastro público envia os dados com código e token sem iniciar sessão", async () => {
  const senha = novoToken();
  let pedido;
  globalThis.fetch = async (url, opcoes) => {
    pedido = { url, opcoes };
    return { ok: true, status: 201, json: async () => ({ id: "novo-usuario" }) };
  };

  await cadastrar(
    { nome: "  Moradora  ", email: "  moradora@example.com  ", senha },
    "48213",
    "token-de-teste",
  );

  assert.equal(pedido.url, "http://api.test/usuarios/");
  assert.equal(pedido.opcoes.method, "POST");
  assert.equal(pedido.opcoes.headers.Authorization, undefined);
  assert.deepEqual(JSON.parse(pedido.opcoes.body), {
    nome: "Moradora",
    email: "moradora@example.com",
    senha,
    codigo: "48213",
    token_verificacao: "token-de-teste",
  });
  assert.equal(tokenSalvo, null);
  assert.equal(sessao.getState().token, null);
});

test("campo do código aceita só dígitos e no máximo cinco", () => {
  assert.equal(somenteDigitosDoCodigo("4 8-2a1b3"), "48213");
  assert.equal(somenteDigitosDoCodigo("123456789"), "12345");
  assert.equal(somenteDigitosDoCodigo("abc"), "");
});

test("cadastro preserva erros de e-mail duplicado e validação sem iniciar sessão", async () => {
  for (const [status, detail] of [
    [400, "E-mail já cadastrado."],
    [422, [{ loc: ["body", "email"], msg: "E-mail inválido." }]],
  ]) {
    globalThis.fetch = async () => ({
      ok: false,
      status,
      json: async () => ({ detail }),
    });
    await assert.rejects(
      cadastrar(conta(), "48213", "token-de-teste"),
      (erro) => erro.status === status,
    );
    assert.equal(tokenSalvo, null);
    assert.equal(sessao.getState().token, null);
  }
});

test("cadastro propaga falha de conexão sem iniciar sessão", async () => {
  globalThis.fetch = async () => {
    throw new TypeError("Conexão indisponível");
  };
  await assert.rejects(cadastrar(conta(), "48213", "token-de-teste"), TypeError);
  assert.equal(tokenSalvo, null);
  assert.equal(sessao.getState().token, null);
});

test("cadastro valida campos obrigatórios, e-mail e confirmação da senha", () => {
  assert.deepEqual(validarCadastro({
    nome: " ", email: "sem-arroba", senha: " ", confirmacao: "",
  }), {
    nome: "Informe seu nome.",
    email: "Informe um e-mail válido.",
    senha: "Informe uma senha.",
    confirmacao: "Confirme sua senha.",
  });
  assert.equal(validarCadastro({
    nome: "Moradora", email: "moradora@example.com", senha: "senha-A", confirmacao: "senha-B",
  }).confirmacao, "As senhas não coincidem.");
  assert.deepEqual(validarCadastro({
    nome: " Moradora ", email: " moradora@example.com ", senha: "senha-A", confirmacao: "senha-A",
  }), {});
});

test("senha incorreta mostra erro e não persiste sessão", async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: "E-mail ou senha inválidos." }),
  });
  await assert.rejects(
    entrar("morador@example.com", novoToken()),
    /E-mail ou senha inválidos/,
  );
  assert.equal(tokenSalvo, null);
  assert.equal(sessao.getState().token, null);
});

test("bloqueio de login informa o tempo de espera sem salvar sessão", async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 429,
    headers: { get: (nome) => (nome === "Retry-After" ? "61" : null) },
    json: async () => ({ detail: "Muitas tentativas de login." }),
  });
  await assert.rejects(
    entrar("morador@example.com", novoToken()),
    (erro) => erro.status === 429 && erro.retryAfter === 61,
  );
  assert.equal(tokenSalvo, null);
});

test("falha ao salvar token não libera as telas autenticadas", async () => {
  falhaArmazenamento = true;
  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => ({ token: novoToken() }),
  });
  await assert.rejects(
    entrar("morador@example.com", novoToken()),
    /Armazenamento/,
  );
  assert.equal(sessao.getState().token, null);
});

test("token de build não autentica uma requisição", async () => {
  process.env.EXPO_PUBLIC_TETO_JUSTO_TOKEN = novoToken();
  let chamadas = 0;
  globalThis.fetch = async () => {
    chamadas++;
    throw new Error("Não deve consultar a rede");
  };
  await assert.rejects(requisitar("/usuarios/eu"), /Entre na sua conta/);
  assert.equal(chamadas, 0);
});

test("restauração valida o token salvo antes de liberar a sessão", async () => {
  tokenSalvo = novoToken();
  const token = tokenSalvo;
  globalThis.fetch = async (url, opcoes) => {
    assert.equal(url, "http://api.test/usuarios/eu");
    assert.equal(opcoes.headers.Authorization, `Bearer ${token}`);
    assert.equal(sessao.getState().pronta, false);
    return { ok: true, status: 200, json: async () => ({ id: "morador" }) };
  };
  await iniciarAutenticacao();
  assert.equal(sessao.getState().token, token);
  assert.equal(sessao.getState().pronta, true);
});

test("restauração sem token termina sem consultar a API", async () => {
  globalThis.fetch = async () => {
    throw new Error("Não deve consultar a rede");
  };
  await iniciarAutenticacao();
  assert.deepEqual(sessao.getState(), {
    token: null,
    pronta: true,
    casaAtiva: null,
    casaPreferidaId: null,
    restaurarCasa: true,
  });
});

test("sessão expirada é removida ao restaurar", async () => {
  tokenSalvo = novoToken();
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: "Não autenticado." }),
  });
  await iniciarAutenticacao();
  assert.equal(tokenSalvo, null);
  assert.deepEqual(sessao.getState(), {
    token: null,
    pronta: true,
    casaAtiva: null,
    casaPreferidaId: null,
    restaurarCasa: true,
  });
});

test("falha de rede ao restaurar preserva o token para nova tentativa", async () => {
  tokenSalvo = novoToken();
  const token = tokenSalvo;
  globalThis.fetch = async () => {
    throw new Error("Sem conexão");
  };
  await assert.rejects(iniciarAutenticacao(), /Sem conexão/);
  assert.equal(tokenSalvo, token);
  assert.deepEqual(sessao.getState(), {
    token,
    pronta: true,
    casaAtiva: null,
    casaPreferidaId: null,
    restaurarCasa: true,
  });
});

test("logout revoga a própria sessão e aceita resposta 204 sem JSON", async () => {
  tokenSalvo = novoToken();
  const token = tokenSalvo;
  sessao.setState({ token, pronta: true });
  globalThis.fetch = async (url, opcoes) => {
    assert.equal(url, "http://api.test/sessoes/logout");
    assert.equal(opcoes.method, "POST");
    assert.equal(opcoes.headers.Authorization, `Bearer ${token}`);
    return {
      ok: true,
      status: 204,
      json: async () => {
        throw new Error("Corpo vazio");
      },
    };
  };
  await sair();
  assert.equal(remocoesPush, 1);
  assert.equal(tokenSalvo, null);
  assert.equal(sessao.getState().token, null);
});

test("falha no logout mantém a sessão para tentar revogar novamente", async () => {
  tokenSalvo = novoToken();
  const token = tokenSalvo;
  sessao.setState({ token, pronta: true });
  globalThis.fetch = async () => {
    throw new Error("Sem conexão");
  };
  await assert.rejects(sair(), /Sem conexão/);
  assert.equal(tokenSalvo, token);
  assert.equal(sessao.getState().token, token);
});

test("401 numa chamada protegida remove a sessão atual", async () => {
  tokenSalvo = novoToken();
  sessao.setState({ token: tokenSalvo, pronta: true });
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: "Não autenticado." }),
  });
  await assert.rejects(requisitar("/tarefas/"), /Não autenticado/);
  assert.equal(tokenSalvo, null);
  assert.equal(sessao.getState().token, null);
});

test("401 de uma requisição antiga não apaga uma sessão nova", async () => {
  sessao.setState({ token: novoToken(), pronta: true });
  const tokenNovo = novoToken();
  globalThis.fetch = async () => {
    sessao.setState({ token: tokenNovo });
    tokenSalvo = tokenNovo;
    return {
      ok: false,
      status: 401,
      json: async () => ({ detail: "Não autenticado." }),
    };
  };
  await assert.rejects(requisitar("/tarefas/"), /Não autenticado/);
  assert.equal(tokenSalvo, tokenNovo);
  assert.equal(sessao.getState().token, tokenNovo);
});

test("exclusão da conta encerra a sessão local só depois do 204", async () => {
  tokenSalvo = novoToken();
  const token = tokenSalvo;
  sessao.setState({ token, pronta: true });
  globalThis.fetch = async (url, opcoes) => {
    assert.equal(url, "http://api.test/usuarios/morador");
    assert.equal(opcoes.method, "DELETE");
    assert.equal(opcoes.headers.Authorization, `Bearer ${token}`);
    assert.equal(sessao.getState().token, token);
    return { ok: true, status: 204 };
  };
  await excluirConta("morador");
  assert.equal(tokenSalvo, null);
  assert.equal(sessao.getState().token, null);
});

test("proprietário recebe o 409 da API e continua com a sessão", async () => {
  tokenSalvo = novoToken();
  const token = tokenSalvo;
  sessao.setState({ token, pronta: true });
  globalThis.fetch = async () => ({
    ok: false,
    status: 409,
    json: async () => ({ detail: "Você é proprietário de uma casa." }),
  });
  await assert.rejects(
    excluirConta("morador"),
    (erro) => erro.status === 409 && /proprietário/.test(erro.message),
  );
  assert.equal(tokenSalvo, token);
  assert.equal(sessao.getState().token, token);
});

test("edição do perfil envia só os campos alterados e devolve os dados novos", async () => {
  sessao.setState({ token: novoToken(), pronta: true });
  globalThis.fetch = async (url, opcoes) => {
    assert.equal(url, "http://api.test/usuarios/morador");
    assert.equal(opcoes.method, "PATCH");
    assert.deepEqual(JSON.parse(opcoes.body), { nome: "Nova" });
    return {
      ok: true,
      status: 200,
      json: async () => ({ id: "morador", nome: "Nova", email: "a@b.co" }),
    };
  };
  assert.equal((await atualizarPerfil("morador", { nome: "Nova" })).nome, "Nova");
});
