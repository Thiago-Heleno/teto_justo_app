import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from "expo-router";
import { useEffect, useState } from "react";
import * as SplashScreen from "expo-splash-screen";
import { ActivityIndicator, Text, useColorScheme, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { useStore } from "zustand";

import { AnimatedSplashOverlay } from "@/components/animated-icon";
import { Caldera } from "@/constants/theme";
import { iniciarAutenticacao } from "@/services/autenticacao-api";
import { sessao } from "@/services/sessao-store";

void SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const { token, pronta, casaAtiva } = useStore(sessao);
  const [aviso, setAviso] = useState<string>();

  useEffect(() => {
    void iniciarAutenticacao().catch(() => {
      setAviso("Não foi possível recuperar a sessão. Tente entrar novamente.");
    });
  }, []);

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
              </Stack.Protected>
            </Stack>
          </>
        )}
      </ThemeProvider>
    </GestureHandlerRootView>
  );
}
