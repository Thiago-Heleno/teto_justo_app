import { DarkTheme, DefaultTheme, ThemeProvider } from "expo-router";
import { useEffect, useState } from "react";
import * as SplashScreen from "expo-splash-screen";
import { ActivityIndicator, useColorScheme, View } from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { useStore } from "zustand";

import { AnimatedSplashOverlay } from "@/components/animated-icon";
import { CadastroScreen } from "@/components/cadastro";
import { LoginScreen } from "@/components/login";
import { FluxoCasa } from "@/components/selecao-casa";
import { Caldera } from "@/constants/theme";
import { iniciarAutenticacao } from "@/services/autenticacao-api";
import { sessao } from "@/services/sessao-store";

SplashScreen.preventAutoHideAsync();

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const { token, pronta } = useStore(sessao);
  const [aviso, setAviso] = useState<string>();
  const [cadastroAberto, setCadastroAberto] = useState(false);
  const [emailLogin, setEmailLogin] = useState("");
  const [mensagemCadastro, setMensagemCadastro] = useState<string>();

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
          <FluxoCasa key={token} />
        ) : cadastroAberto ? (
          <CadastroScreen
            emailInicial={emailLogin}
            onVoltar={(email) => {
              setEmailLogin(email);
              setCadastroAberto(false);
            }}
            onCadastrado={(email) => {
              setEmailLogin(email);
              setMensagemCadastro(
                "Conta criada. Entre com seu e-mail e senha.",
              );
              setAviso(undefined);
              setCadastroAberto(false);
            }}
          />
        ) : (
          <LoginScreen
            aviso={aviso}
            emailInicial={emailLogin}
            mensagemCadastro={mensagemCadastro}
            onIniciarLogin={() => setMensagemCadastro(undefined)}
            onCriarConta={(email) => {
              setEmailLogin(email);
              setMensagemCadastro(undefined);
              setCadastroAberto(true);
            }}
          />
        )}
      </ThemeProvider>
    </GestureHandlerRootView>
  );
}
