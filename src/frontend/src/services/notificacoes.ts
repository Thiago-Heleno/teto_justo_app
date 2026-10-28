import Constants from "expo-constants";
import * as Notifications from "expo-notifications";
import * as SecureStore from "expo-secure-store";
import { router } from "expo-router";
import { Alert, AppState, Linking, Platform } from "react-native";

import { requisitar } from "./api.ts";
import { listarCasas } from "./casas-api.ts";
import { selecionarCasa, sessao } from "./sessao-store.ts";
import type { Tarefa } from "./tarefas-api.ts";

const CHAVE_TOKEN_PUSH = "teto_justo_push_token";

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function permissaoConcedida(
  permissao: Notifications.NotificationPermissionsStatus,
) {
  return (
    permissao.granted ||
    permissao.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL
  );
}

export async function notificacoesAtivas() {
  if (Platform.OS === "web") return false;

  const token = await SecureStore.getItemAsync(CHAVE_TOKEN_PUSH);
  const permissao = await Notifications.getPermissionsAsync();

  return Boolean(token && permissaoConcedida(permissao));
}

let ativacaoEmAndamento: Promise<boolean> | undefined;
let sessaoDaAtivacao: string | null;

export function ativarNotificacoes(solicitarPermissao = true) {
  const tokenDaSessao = sessao.getState().token;
  if (!ativacaoEmAndamento || sessaoDaAtivacao !== tokenDaSessao) {
    sessaoDaAtivacao = tokenDaSessao;
    const operacao = registrarNotificacoes(solicitarPermissao).finally(() => {
      if (ativacaoEmAndamento === operacao) ativacaoEmAndamento = undefined;
    });
    ativacaoEmAndamento = operacao;
  }
  return ativacaoEmAndamento;
}

async function registrarNotificacoes(solicitarPermissao: boolean) {
  if (Platform.OS === "web") return false;

  const tokenDaSessao = sessao.getState().token;
  if (!tokenDaSessao) return false;

  if (Platform.OS === "android") {
    await Notifications.setNotificationChannelAsync("default", {
      name: "Tarefas",
      importance: Notifications.AndroidImportance.HIGH,
    });
  }

  let permissao = await Notifications.getPermissionsAsync();
  if (sessao.getState().token !== tokenDaSessao) return false;

  if (!permissaoConcedida(permissao)) {
    if (!solicitarPermissao) return false;
    if (!permissao.canAskAgain) {
      await Linking.openSettings();
      return false;
    }
    permissao = await Notifications.requestPermissionsAsync();
  }

  if (!permissaoConcedida(permissao)) return false;

  const projectId = Constants.expoConfig?.extra?.eas?.projectId;

  if (!projectId) {
    throw new Error("Projeto Expo não configurado para notificações.");
  }

  const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;

  const anterior = await SecureStore.getItemAsync(CHAVE_TOKEN_PUSH);

  if (sessao.getState().token !== tokenDaSessao) return false;

  if (anterior && anterior !== token) {
    await requisitar<void>("/usuarios/eu/dispositivos", undefined, {
      method: "DELETE",
      body: { token: anterior },
    });
  }

  if (sessao.getState().token !== tokenDaSessao) return false;

  await requisitar("/usuarios/eu/dispositivos", undefined, {
    method: "POST",
    body: {
      token,
      plataforma: Platform.OS === "ios" ? "ios" : "android",
    },
  });

  if (sessao.getState().token !== tokenDaSessao) return false;
  await SecureStore.setItemAsync(CHAVE_TOKEN_PUSH, token);

  return true;
}

export function acompanharNotificacoes() {
  const tokenDaSessao = sessao.getState().token;
  if (Platform.OS === "web" || !tokenDaSessao) return () => {};

  let montado = true;
  let verificando = false;
  let avisoExibido = false;
  const vigente = () => montado && sessao.getState().token === tokenDaSessao;
  const informarFalha = () => {
    if (!vigente()) return;
    Alert.alert(
      "Notificações",
      "Não foi possível ativar as notificações. Tente novamente pelo Perfil.",
    );
  };

  async function verificar() {
    if (!vigente() || verificando || AppState.currentState === "background")
      return;
    verificando = true;
    try {
      const ativas = await ativarNotificacoes(false);
      if (!vigente() || ativas) return;
      await removerNotificacoesDoDispositivo().catch(() => {});
      if (!vigente() || avisoExibido) return;
      avisoExibido = true;
      Alert.alert(
        "Ativar notificações?",
        "Receba avisos sobre suas tarefas e prazos. Se a permissão estiver bloqueada, abra as configurações do app e ative Notificações.",
        [
          { text: "Agora não", style: "cancel" },
          {
            text: "Ativar",
            onPress: () => {
              if (vigente()) void ativarNotificacoes().catch(informarFalha);
            },
          },
        ],
      );
    } catch {
      if (!avisoExibido) {
        avisoExibido = true;
        informarFalha();
      }
    } finally {
      verificando = false;
    }
  }

  void verificar();
  const assinatura = AppState.addEventListener("change", (estado) => {
    if (estado === "active") void verificar();
  });
  return () => {
    montado = false;
    assinatura.remove();
  };
}

export async function removerNotificacoesDoDispositivo() {
  if (Platform.OS === "web") return;

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
  acao = Notifications.DEFAULT_ACTION_IDENTIFIER,
) {
  const tarefaId = typeof dados.tarefa_id === "string" ? dados.tarefa_id : "";

  const casaId = dados.casa_id;

  const resumoRodizio = dados.tipo === "rodizio_distribuido";

  if (!resumoRodizio && !UUID.test(tarefaId)) return;

  if (typeof casaId !== "string" || !UUID.test(casaId)) {
    return;
  }

  const casas = await listarCasas();

  const casa = casas.find((item) => item.id === casaId);

  if (!casa || sessao.getState().token !== tokenDaSessao) {
    return;
  }

  if (sessao.getState().casaAtiva?.id !== casaId) {
    if (!(await selecionarCasa(casa))) return;
  }

  if (resumoRodizio) {
    if (sessao.getState().token === tokenDaSessao) {
      router.push("/tarefas");
    }

    return;
  }

  try {
    const tarefa = await requisitar<Tarefa>(`/tarefas/${tarefaId}`);

    if (
      tarefa.fk_casa_id !== casaId ||
      sessao.getState().token !== tokenDaSessao
    ) {
      return;
    }

    // Conclui a tarefa quando essa ação for selecionada.
    if (
      acao === "concluir_tarefa" &&
      (dados.tipo === "tarefa_vence_hoje" || dados.tipo === "tarefa_atrasada")
    ) {
      try {
        await requisitar<Tarefa>(`/tarefas/${tarefaId}/conclusoes`, undefined, {
          method: "POST",
        });
      } catch {
        // Se a conclusão falhar, permite abrir a tarefa
        // para que o usuário confira seu estado.
      }
    }

    // "Ver tarefa" e o toque normal na notificação
    // abrem os detalhes da tarefa.
    router.push({
      pathname: "/tarefas",
      params: { abrir: tarefaId },
    });

    return;
  } catch {
    // Se a tarefa não existir ou estiver inacessível,
    // direciona para a lista de tarefas.
  }

  if (sessao.getState().token === tokenDaSessao) {
    router.push("/tarefas");
  }
}
