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
      return undefined;
    },
  },
});
mock.module("../src/services/casas-api.ts", {
  namedExports: { listarCasas: async () => [{ id: casaId, nome: "Casa" }] },
});
mock.module("../src/services/sessao-store.ts", {
  namedExports: {
    sessao: { getState: () => ({ token: "sessao", casaAtiva }) },
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
} = await import("../src/services/notificacoes.ts");

beforeEach(() => {
  tokenSalvo = null;
  permissao = true;
  tokenExpo = "ExpoPushToken[novo]";
  pedidos = [];
  destinos = [];
  casaAtiva = null;
  tarefaDisponivel = true;
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
