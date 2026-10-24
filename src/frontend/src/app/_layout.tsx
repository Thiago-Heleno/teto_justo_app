import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from "expo-router";
import { useEffect, useRef, useState } from "react";
import * as Notifications from "expo-notifications";
import * as SplashScreen from "expo-splash-screen";
import {
  ActivityIndicator,
  Platform,
  Text,
  useColorScheme,
  View,
} from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { useStore } from "zustand";

import { AnimatedSplashOverlay } from "@/components/animated-icon";
import { Caldera } from "@/constants/theme";
import { iniciarAutenticacao } from "@/services/autenticacao-api";
import {
  abrirTarefaNotificada,
  ativarNotificacoes,
  notificacoesAtivas,
  removerNotificacoesDoDispositivo,
} from "@/services/notificacoes";
import { sessao } from "@/services/sessao-store";

void SplashScreen.preventAutoHideAsync();

if (Platform.OS !== "web") {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: false,
      shouldSetBadge: false,
    }),
  });
  void Notifications.setNotificationCategoryAsync("tarefa_pendente", [
    {
      identifier: "concluir_tarefa",
      buttonTitle: "Concluir",
      options: { opensAppToForeground: true },
    },
    {
      identifier: "ver_tarefa",
      buttonTitle: "Ver tarefa",
      options: { opensAppToForeground: true },
    },
  ]).catch(() => {});
}

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const { token, pronta, casaAtiva } = useStore(sessao);
  const [aviso, setAviso] = useState<string>();
  const ultimaResposta = useRef<string | null>(null);

  useEffect(() => {
    void iniciarAutenticacao().catch(() => {
      setAviso("Não foi possível recuperar a sessão. Tente entrar novamente.");
    });
  }, []);

  useEffect(() => {
    if (Platform.OS === "web" || !pronta || !token) return;
    void notificacoesAtivas()
      .then(async (ativa) => {
        if (ativa) await ativarNotificacoes();
        else await removerNotificacoesDoDispositivo();
      })
      .catch(() => {});
  }, [pronta, token]);

  useEffect(() => {
    if (Platform.OS === "web" || !pronta || !token) return;
    const tokenDaSessao = token;
    let montado = true;

    async function abrir(response: Notifications.NotificationResponse) {
      const identificador =
        `${response.notification.request.identifier}:${response.actionIdentifier}`;
      if (ultimaResposta.current === identificador) return;
      ultimaResposta.current = identificador;
      try {
        if (montado)
          await abrirTarefaNotificada(
            response.notification.request.content.data ?? {},
            tokenDaSessao,
            response.actionIdentifier,
          );
      } finally {
        await Notifications.clearLastNotificationResponseAsync().catch(
          () => {},
        );
      }
    }

    const assinatura = Notifications.addNotificationResponseReceivedListener(
      (response) => void abrir(response).catch(() => {}),
    );
    void Notifications.getLastNotificationResponseAsync()
      .then((response) => {
        if (response && montado) void abrir(response).catch(() => {});
      })
      .catch(() => {});
    return () => {
      montado = false;
      assinatura.remove();
    };
  }, [pronta, token]);

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <ThemeProvider value={colorScheme === "dark" ? DarkTheme : DefaultTheme}>
        <AnimatedSplashOverlay />
        {!pronta ? (
          <View
            style={{
              flex: 1,
              justifyContent: "center",
              backgroundColor: Caldera.limestone,
            }}
          >
            <ActivityIndicator accessibilityLabel="Carregando sessão" />
          </View>
        ) : (
          <>
            {!token && aviso && (
              <Text
                accessibilityRole="alert"
                style={{ padding: 16, color: "#a32316" }}
              >
                {aviso}
              </Text>
            )}
            <Stack screenOptions={{ headerShown: false }}>
              <Stack.Protected guard={!token}>
                <Stack.Screen name="login" />
              </Stack.Protected>
              <Stack.Protected guard={Boolean(token) && !casaAtiva}>
                <Stack.Screen name="casas" />
              </Stack.Protected>
              <Stack.Protected guard={Boolean(token) && Boolean(casaAtiva)}>
                <Stack.Screen name="(app)" />
                <Stack.Screen name="gerenciar-casa" />
                <Stack.Screen name="rotatividades" />
                <Stack.Screen name="calendario" />
              </Stack.Protected>
            </Stack>
          </>
        )}
      </ThemeProvider>
    </GestureHandlerRootView>
  );
}
