import assert from "node:assert/strict";
import { mock, test } from "node:test";

const chamadas = [];

mock.module("react-native", { namedExports: { Platform: { OS: "web" } } });
mock.module("expo-constants", { defaultExport: { expoConfig: {} } });
mock.module("expo-notifications", { namedExports: {} });
mock.module("expo-secure-store", { namedExports: {} });
mock.module("expo-router", { namedExports: { router: {} } });
mock.module("../src/services/api.ts", {
  namedExports: { requisitar: async () => {} },
});
mock.module("../src/services/casas-api.ts", {
  namedExports: { listarCasas: async () => [] },
});
mock.module("../src/services/sessao-store.ts", {
  namedExports: {
    sessao: { getState: () => ({}) },
    selecionarCasa: async () => true,
  },
});
mock.module("../src/services/web-push.web.ts", {
  namedExports: {
    ativarWebPush: async () => (chamadas.push("ativar"), true),
    removerWebPush: async () => void chamadas.push("remover"),
    webPushAtivo: async () => (chamadas.push("ativo"), true),
  },
});

const {
  ativarNotificacoes,
  notificacoesAtivas,
  removerNotificacoesDoDispositivo,
} = await import("../src/services/notificacoes.ts");

test("na web, as notificações usam a implementação de Web Push", async () => {
  assert.equal(await ativarNotificacoes(), true);
  assert.equal(await notificacoesAtivas(), true);
  await removerNotificacoesDoDispositivo();

  assert.deepEqual(chamadas, ["ativar", "ativo", "remover"]);
});
