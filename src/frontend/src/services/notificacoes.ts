import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import * as SecureStore from "expo-secure-store";
import { router } from "expo-router";
import { Platform } from "react-native";

import { requisitar } from "./api.ts";
import { listarCasas } from "./casas-api.ts";
import { selecionarCasa, sessao } from "./sessao-store.ts";
import type { Tarefa } from "./tarefas-api.ts";

const CHAVE_TOKEN_PUSH = "teto_justo_push_token";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function notificacoesAtivas() {
  if (Platform.OS !== "android") return false;
  const token = await SecureStore.getItemAsync(CHAVE_TOKEN_PUSH);
  const permissao = await Notifications.getPermissionsAsync();
  return Boolean(token && permissao.granted);
}

export async function ativarNotificacoes() {
  if (Platform.OS !== "android") return false;
  await Notifications.setNotificationChannelAsync("default", {
    name: "Tarefas",
    importance: Notifications.AndroidImportance.HIGH,
  });
  let permissao = await Notifications.getPermissionsAsync();
  if (!permissao.granted)
    permissao = await Notifications.requestPermissionsAsync();
  if (!permissao.granted) return false;

  const projectId = Constants.expoConfig?.extra?.eas?.projectId;
  if (!projectId)
    throw new Error("Projeto Expo não configurado para notificações.");
  const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
  const anterior = await SecureStore.getItemAsync(CHAVE_TOKEN_PUSH);
  if (anterior && anterior !== token) {
    await requisitar<void>("/usuarios/eu/dispositivos", undefined, {
      method: "DELETE",
      body: { token: anterior },
    });
  }
  await requisitar("/usuarios/eu/dispositivos", undefined, {
    method: "POST",
    body: { token, plataforma: "android" },
  });
  await SecureStore.setItemAsync(CHAVE_TOKEN_PUSH, token);
  return true;
}

export async function removerNotificacoesDoDispositivo() {
  if (Platform.OS !== "android") return;
  const token = await SecureStore.getItemAsync(CHAVE_TOKEN_PUSH);
  if (!token) return;
  await requisitar<void>("/usuarios/eu/dispositivos", undefined, {
    method: "DELETE",
    body: { token },
  });
  await SecureStore.deleteItemAsync(CHAVE_TOKEN_PUSH);
}

export async function abrirTarefaNotificada(
  dados: Record<string, unknown>,
  tokenDaSessao: string,
) {
  const tarefaId = typeof dados.tarefa_id === "string" ? dados.tarefa_id : "";
  const casaId = dados.casa_id;
  const resumoRodizio = dados.tipo === "rodizio_distribuido";
  if (!resumoRodizio && !UUID.test(tarefaId)) return;
  if (typeof casaId !== "string" || !UUID.test(casaId)) return;

  const casas = await listarCasas();
  const casa = casas.find((item) => item.id === casaId);
  if (!casa || sessao.getState().token !== tokenDaSessao) return;
  if (sessao.getState().casaAtiva?.id !== casaId) {
    if (!(await selecionarCasa(casa))) return;
  }
  if (resumoRodizio) {
    if (sessao.getState().token === tokenDaSessao) router.push("/tarefas");
    return;
  }
  try {
    const tarefa = await requisitar<Tarefa>(`/tarefas/${tarefaId}`);
    if (
      tarefa.fk_casa_id === casaId &&
      sessao.getState().token === tokenDaSessao
    ) {
      router.push({ pathname: "/tarefas", params: { abrir: tarefaId } });
      return;
    }
  } catch {
    // A lista continua disponível quando a tarefa sumiu ou ficou inacessível.
  }
  if (sessao.getState().token === tokenDaSessao) router.push("/tarefas");
}
