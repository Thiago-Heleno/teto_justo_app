import { DarkTheme, DefaultTheme, ThemeProvider } from "expo-router";
import { useEffect, useState } from "react";
import * as SplashScreen from "expo-splash-screen";
import { ActivityIndicator, useColorScheme, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { useStore } from "zustand";

import { AnimatedSplashOverlay } from "@/components/animated-icon";
import AppTabs from "@/components/app-tabs";
import { LoginScreen } from "@/components/login";
import { Caldera } from "@/constants/theme";
import { iniciarAutenticacao } from "@/services/autenticacao-api";
import { sessao } from "@/services/sessao-store";

SplashScreen.preventAutoHideAsync();

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const { token, pronta } = useStore(sessao);
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
        ) : token ? (
          <AppTabs />
        ) : (
          <LoginScreen aviso={aviso} />
        )}
      </ThemeProvider>
    </GestureHandlerRootView>
  );
}
