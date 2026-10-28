import assert from "node:assert/strict";
import { beforeEach, mock, test } from "node:test";

const tarefaId = "11111111-1111-4111-8111-111111111111";
const casaId = "22222222-2222-4222-8222-222222222222";
let tokenSalvo;
let permissao;
let tokenExpo;
let pedidos;
let destinos;
let casaAtiva;
let tarefaDisponivel;
let tokenDaSessao;
let casasDisponiveis;
let podePedir;
let permissaoSolicitada;
let pedidosPermissao;
let configuracoesAbertas;
let alertas;
let aoMudarEstado;
let falhaCadastro;
let statusIos;
let antesDeObterToken;
const plataforma = { OS: "android" };
const appState = {
  currentState: "active",
  addEventListener: (_evento, callback) => {
    aoMudarEstado = callback;
    return {
      remove: () => {
        aoMudarEstado = undefined;
      },
    };
  },
};

mock.module("react-native", {
  namedExports: {
    Platform: plataforma,
    AppState: appState,
    Alert: { alert: (...args) => alertas.push(args) },
    Linking: {
      openSettings: async () => {
        configuracoesAbertas++;
      },
    },
  },
});
mock.module("expo-constants", {
  defaultExport: {
    expoConfig: { extra: { eas: { projectId: "projeto-teste" } } },
  },
});
mock.module("expo-notifications", {
  namedExports: {
    AndroidImportance: { HIGH: 4 },
    IosAuthorizationStatus: { PROVISIONAL: 3 },
    setNotificationChannelAsync: async () => {},
    setNotificationCategoryAsync: async () => {},
    DEFAULT_ACTION_IDENTIFIER: "expo.modules.notifications.actions.DEFAULT",
    getPermissionsAsync: async () => ({
      granted: permissao,
      canAskAgain: podePedir,
      ios: { status: statusIos },
    }),
    requestPermissionsAsync: async () => {
      pedidosPermissao++;
      permissao = permissaoSolicitada;
      return { granted: permissao, canAskAgain: podePedir };
    },
    getExpoPushTokenAsync: async () => {
      await antesDeObterToken?.();
      return { data: tokenExpo };
    },
  },
});
mock.module("expo-secure-store", {
  namedExports: {
    getItemAsync: async () => tokenSalvo,
    setItemAsync: async (_chave, token) => {
      tokenSalvo = token;
    },
    deleteItemAsync: async () => {
      tokenSalvo = null;
    },
  },
});
mock.module("expo-router", {
  namedExports: { router: { push: (destino) => destinos.push(destino) } },
});
mock.module("../src/services/api.ts", {
  namedExports: {
    requisitar: async (caminho, _signal, opcoes) => {
      pedidos.push({ caminho, opcoes });
      if (
        opcoes?.method === "POST" &&
        caminho === "/usuarios/eu/dispositivos" &&
        falhaCadastro
      ) {
        throw new Error("Falha ao cadastrar dispositivo");
      }
      if (caminho.startsWith("/tarefas/")) {
        if (!tarefaDisponivel) throw new Error("Tarefa não encontrada");
        return { id: tarefaId, fk_casa_id: casaId };
      }
      return undefined;
    },
  },
});
mock.module("../src/services/casas-api.ts", {
  namedExports: { listarCasas: async () => casasDisponiveis },
});
mock.module("../src/services/sessao-store.ts", {
  namedExports: {
    sessao: { getState: () => ({ token: tokenDaSessao, casaAtiva }) },
    selecionarCasa: async (casa) => {
      casaAtiva = casa;
      return true;
    },
  },
});

const {
  abrirTarefaNotificada,
  acompanharNotificacoes,
  notificacoesAtivas,
  ativarNotificacoes,
  removerNotificacoesDoDispositivo,
} = await import("../src/services/notificacoes.ts");

beforeEach(() => {
  tokenSalvo = null;
  permissao = true;
  podePedir = true;
  permissaoSolicitada = false;
  pedidosPermissao = 0;
  configuracoesAbertas = 0;
  alertas = [];
  aoMudarEstado = undefined;
  falhaCadastro = false;
  statusIos = undefined;
  antesDeObterToken = undefined;
  plataforma.OS = "android";
  appState.currentState = "active";
  tokenExpo = "ExpoPushToken[novo]";
  pedidos = [];
  destinos = [];
  casaAtiva = null;
  tarefaDisponivel = true;
  tokenDaSessao = "sessao";
  casasDisponiveis = [{ id: casaId, nome: "Casa" }];
});

test("ativação registra token e remoção acontece antes do logout", async () => {
  assert.equal(await ativarNotificacoes(), true);
  assert.equal(tokenSalvo, tokenExpo);
  assert.deepEqual(pedidos[0], {
    caminho: "/usuarios/eu/dispositivos",
    opcoes: {
      method: "POST",
      body: { token: tokenExpo, plataforma: "android" },
    },
  });
  await removerNotificacoesDoDispositivo();
  assert.deepEqual(pedidos[1].opcoes, {
    method: "DELETE",
    body: { token: tokenExpo },
  });
  assert.equal(tokenSalvo, null);
});

test("permissão negada não registra dispositivo", async () => {
  permissao = false;
  assert.equal(await ativarNotificacoes(), false);
  assert.deepEqual(pedidos, []);
});

test("toque escolhe casa e abre tarefa autorizada", async () => {
  await abrirTarefaNotificada(
    { tarefa_id: tarefaId, casa_id: casaId },
    "sessao",
  );
  assert.equal(casaAtiva.id, casaId);
  assert.deepEqual(
    pedidos.map((pedido) => pedido.caminho),
    [`/tarefas/${tarefaId}`],
  );
  assert.deepEqual(destinos, [
    { pathname: "/tarefas", params: { abrir: tarefaId } },
  ]);
});

test("tarefa removida abre só a lista e payload inválido é ignorado", async () => {
  tarefaDisponivel = false;
  await abrirTarefaNotificada(
    { tarefa_id: tarefaId, casa_id: casaId },
    "sessao",
  );
  assert.deepEqual(destinos, ["/tarefas"]);
  await abrirTarefaNotificada(
    { tarefa_id: "inválido", casa_id: casaId },
    "sessao",
  );
  assert.deepEqual(destinos, ["/tarefas"]);
});

test("resumo do rodízio escolhe a casa e abre a lista sem consultar tarefa", async () => {
  await abrirTarefaNotificada(
    { tipo: "rodizio_distribuido", casa_id: casaId },
    "sessao",
  );
  assert.equal(casaAtiva.id, casaId);
  assert.deepEqual(pedidos, []);
  assert.deepEqual(destinos, ["/tarefas"]);
});

test("resumo não navega para casa inacessível, sessão trocada ou payload inválido", async () => {
  casasDisponiveis = [];
  await abrirTarefaNotificada(
    { tipo: "rodizio_distribuido", casa_id: casaId },
    "sessao",
  );
  casasDisponiveis = [{ id: casaId, nome: "Casa" }];
  tokenDaSessao = "outra-sessao";
  await abrirTarefaNotificada(
    { tipo: "rodizio_distribuido", casa_id: casaId },
    "sessao",
  );
  tokenDaSessao = "sessao";
  await abrirTarefaNotificada(
    { tipo: "rodizio_distribuido", casa_id: "invalido" },
    "sessao",
  );
  await abrirTarefaNotificada(
    { tipo: "desconhecido", casa_id: casaId },
    "sessao",
  );
  assert.deepEqual(pedidos, []);
  assert.deepEqual(destinos, []);
});

test("ação Concluir chama endpoint de conclusão e abre a tarefa", async () => {
  await abrirTarefaNotificada(
    { tipo: "tarefa_vence_hoje", tarefa_id: tarefaId, casa_id: casaId },
    "sessao",
    "concluir_tarefa",
  );

  assert.deepEqual(
    pedidos.map((pedido) => [pedido.caminho, pedido.opcoes?.method]),
    [
      [`/tarefas/${tarefaId}`, undefined],
      [`/tarefas/${tarefaId}/conclusoes`, "POST"],
    ],
  );
  assert.deepEqual(destinos, [
    { pathname: "/tarefas", params: { abrir: tarefaId } },
  ]);
});

test("ação Concluir também é válida para aviso de tarefa atrasada", async () => {
  await abrirTarefaNotificada(
    { tipo: "tarefa_atrasada", tarefa_id: tarefaId, casa_id: casaId },
    "sessao",
    "concluir_tarefa",
  );
  assert.equal(pedidos[1].caminho, `/tarefas/${tarefaId}/conclusoes`);
  assert.equal(pedidos[1].opcoes.method, "POST");
});

test("ação Ver tarefa apenas abre o detalhe sem concluir", async () => {
  await abrirTarefaNotificada(
    { tipo: "tarefa_atrasada", tarefa_id: tarefaId, casa_id: casaId },
    "sessao",
    "ver_tarefa",
  );
  assert.deepEqual(
    pedidos.map((pedido) => pedido.caminho),
    [`/tarefas/${tarefaId}`],
  );
  assert.deepEqual(destinos, [
    { pathname: "/tarefas", params: { abrir: tarefaId } },
  ]);
});

const concluirAssincronos = () =>
  new Promise((resolve) => setImmediate(resolve));

test("ativação solicita permissão e cadastra após o aceite", async () => {
  permissao = false;
  permissaoSolicitada = true;
  assert.equal(await ativarNotificacoes(), true);
  assert.equal(pedidosPermissao, 1);
  assert.equal(tokenSalvo, tokenExpo);
});

test("permissão bloqueada abre configurações sem repetir pedido nativo", async () => {
  permissao = false;
  podePedir = false;
  assert.equal(await ativarNotificacoes(), false);
  assert.equal(configuracoesAbertas, 1);
  assert.equal(pedidosPermissao, 0);
  assert.deepEqual(pedidos, []);
});

test("verificação silenciosa não solicita permissão nem abre configurações", async () => {
  permissao = false;
  podePedir = false;
  assert.equal(await ativarNotificacoes(false), false);
  assert.equal(configuracoesAbertas, 0);
  assert.equal(pedidosPermissao, 0);
  assert.deepEqual(pedidos, []);
});

test("token salvo não indica notificações ativas após revogar permissão", async () => {
  tokenSalvo = tokenExpo;
  permissao = false;
  assert.equal(await notificacoesAtivas(), false);
});

test("falha no cadastro não salva token como se a ativação tivesse funcionado", async () => {
  falhaCadastro = true;
  await assert.rejects(ativarNotificacoes(), /Falha ao cadastrar/);
  assert.equal(tokenSalvo, null);
});

test("aviso automático permite adiar sem reaparecer ao retornar ao app", async () => {
  permissao = false;
  const parar = acompanharNotificacoes();
  await concluirAssincronos();
  assert.equal(alertas.length, 1);
  assert.equal(alertas[0][2][0].text, "Agora não");
  assert.equal(pedidosPermissao, 0);
  aoMudarEstado("active");
  await concluirAssincronos();
  assert.equal(alertas.length, 1);
  parar();
  assert.equal(aoMudarEstado, undefined);
});

test("aceitar aviso automático solicita permissão e registra dispositivo", async () => {
  permissao = false;
  permissaoSolicitada = true;
  const parar = acompanharNotificacoes();
  await concluirAssincronos();
  alertas[0][2][1].onPress();
  await concluirAssincronos();
  assert.equal(pedidosPermissao, 1);
  assert.equal(tokenSalvo, tokenExpo);
  parar();
});

test("retorno das configurações registra permissão concedida sem token anterior", async () => {
  permissao = false;
  const parar = acompanharNotificacoes();
  await concluirAssincronos();
  permissao = true;
  aoMudarEstado("active");
  await concluirAssincronos();
  assert.equal(tokenSalvo, tokenExpo);
  assert.equal(pedidosPermissao, 0);
  assert.equal(alertas.length, 1);
  parar();
});

test("revogar permissão remove cadastro e oferece ativação ao retornar", async () => {
  const parar = acompanharNotificacoes();
  await concluirAssincronos();
  assert.equal(alertas.length, 0);
  permissao = false;
  aoMudarEstado("active");
  await concluirAssincronos();
  assert.equal(tokenSalvo, null);
  assert.equal(pedidos.at(-1).opcoes.method, "DELETE");
  assert.equal(alertas.length, 1);
  parar();
});

test("aviso de sessão encerrada não solicita permissão", async () => {
  permissao = false;
  const parar = acompanharNotificacoes();
  await concluirAssincronos();
  tokenDaSessao = null;
  alertas[0][2][1].onPress();
  await concluirAssincronos();
  assert.equal(pedidosPermissao, 0);
  assert.deepEqual(pedidos, []);
  parar();
});

test("web não solicita notificações nem acompanha estado nativo", async () => {
  plataforma.OS = "web";
  const parar = acompanharNotificacoes();
  assert.equal(await ativarNotificacoes(), false);
  assert.equal(await notificacoesAtivas(), false);
  assert.equal(aoMudarEstado, undefined);
  assert.deepEqual(alertas, []);
  parar();
});

test("permissão provisória iOS registra sem solicitar novamente", async () => {
  plataforma.OS = "ios";
  permissao = false;
  statusIos = 3;
  assert.equal(await ativarNotificacoes(false), true);
  assert.equal(pedidosPermissao, 0);
  assert.equal(pedidos[0].opcoes.body.plataforma, "ios");
});

test("verificações concorrentes compartilham um único cadastro", async () => {
  const resultados = await Promise.all([
    ativarNotificacoes(false),
    ativarNotificacoes(false),
  ]);
  assert.deepEqual(resultados, [true, true]);
  assert.equal(pedidos.filter((p) => p.opcoes?.method === "POST").length, 1);
});

test("troca de sessão durante obtenção de token impede cadastro na conta nova", async () => {
  antesDeObterToken = () => {
    tokenDaSessao = "nova-sessao";
  };
  assert.equal(await ativarNotificacoes(), false);
  assert.deepEqual(pedidos, []);
  assert.equal(tokenSalvo, null);
});

test("acompanhamento encerrado não exibe aviso pendente", async () => {
  permissao = false;
  const parar = acompanharNotificacoes();
  parar();
  await concluirAssincronos();
  assert.deepEqual(alertas, []);
});

test("falha de cadastro automático informa como tentar novamente", async () => {
  falhaCadastro = true;
  const parar = acompanharNotificacoes();
  await concluirAssincronos();
  assert.equal(alertas.length, 1);
  assert.match(alertas[0][1], /Tente novamente pelo Perfil/);
  assert.equal(tokenSalvo, null);
  parar();
});

test("app em segundo plano aguarda retorno para oferecer ativação", async () => {
  permissao = false;
  appState.currentState = "background";
  const parar = acompanharNotificacoes();
  await concluirAssincronos();
  assert.deepEqual(alertas, []);
  appState.currentState = "active";
  aoMudarEstado("active");
  await concluirAssincronos();
  assert.equal(alertas.length, 1);
  parar();
});
