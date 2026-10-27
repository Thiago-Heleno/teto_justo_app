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
let falhaTeste;

mock.module("react-native", { namedExports: { Platform: { OS: "android" } } });
mock.module("expo-constants", {
  defaultExport: {
    expoConfig: { extra: { eas: { projectId: "projeto-teste" } } },
  },
});
mock.module("expo-notifications", {
  namedExports: {
    AndroidImportance: { HIGH: 4 },
    setNotificationChannelAsync: async () => {},
    setNotificationCategoryAsync: async () => {},
    DEFAULT_ACTION_IDENTIFIER: "expo.modules.notifications.actions.DEFAULT",
    getPermissionsAsync: async () => ({ granted: permissao }),
    requestPermissionsAsync: async () => ({ granted: permissao }),
    getExpoPushTokenAsync: async () => ({ data: tokenExpo }),
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
      if (caminho.startsWith("/tarefas/")) {
        if (!tarefaDisponivel) throw new Error("Tarefa não encontrada");
        return { id: tarefaId, fk_casa_id: casaId };
      }
      if (caminho === "/usuarios/eu/notificacoes/teste") {
        if (falhaTeste) throw falhaTeste;
        return { aceitos: 1, falhas: 0, invalidos: 0 };
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
  ativarNotificacoes,
  removerNotificacoesDoDispositivo,
  enviarNotificacaoTeste,
} = await import("../src/services/notificacoes.ts");

beforeEach(() => {
  falhaTeste = undefined;
  tokenSalvo = null;
  permissao = true;
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

test("teste manual envia apenas o tipo e a tarefa à rota do usuário logado", async () => {
  const resultado = await enviarNotificacaoTeste("tarefa_atrasada", tarefaId);
  assert.deepEqual(resultado, { aceitos: 1, falhas: 0, invalidos: 0 });
  assert.deepEqual(pedidos, [
    {
      caminho: "/usuarios/eu/notificacoes/teste",
      opcoes: {
        method: "POST",
        body: { tipo: "tarefa_atrasada", tarefa_id: tarefaId },
      },
    },
  ]);
});


test("teste manual preserva a falha da API para a tela informar o problema", async () => {
  falhaTeste = new Error("Ative as notificações no celular.");
  await assert.rejects(enviarNotificacaoTeste("tarefa_atribuida", tarefaId), falhaTeste);
});
