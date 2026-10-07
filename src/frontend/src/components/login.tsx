import { useRef, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Caldera } from "@/constants/theme";
import { ErroApi } from "@/services/api";
import { entrar } from "@/services/autenticacao-api";

export function LoginScreen({
  aviso,
  emailInicial = "",
  mensagemCadastro,
  onCriarConta,
  onIniciarLogin,
}: {
  aviso?: string;
  emailInicial?: string;
  mensagemCadastro?: string;
  onCriarConta: (email: string) => void;
  onIniciarLogin: () => void;
}) {
  const [email, setEmail] = useState(emailInicial);
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState<string>();
  const [enviando, setEnviando] = useState(false);
  const envioEmAndamento = useRef(false);

  async function fazerLogin() {
    if (envioEmAndamento.current) return;
    onIniciarLogin();
    if (!email.trim() || !senha) {
      setErro("Preencha seu e-mail e sua senha.");
      return;
    }
    envioEmAndamento.current = true;
    setEnviando(true);
    setErro(undefined);
    try {
      await entrar(email, senha);
      setSenha("");
    } catch (falha) {
      let mensagem = "Não foi possível entrar. Tente novamente em instantes.";
      if (falha instanceof ErroApi) {
        if (falha.status === 401) mensagem = "E-mail ou senha inválidos.";
        else if (falha.status === 429) {
          const segundos = falha.retryAfter;
          mensagem = segundos
            ? `Muitas tentativas. Tente novamente em ${segundos >= 60 ? `${Math.ceil(segundos / 60)} min` : `${segundos} s`}.`
            : "Muitas tentativas. Aguarde antes de tentar novamente.";
        } else if (falha.status === 503)
          mensagem =
            "Login temporariamente indisponível. Tente novamente mais tarde.";
        else if (falha.status === 422)
          mensagem = "Confira o e-mail e a senha informados.";
      } else if (falha instanceof TypeError) {
        mensagem =
          "Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.";
      }
      setErro(mensagem);
    } finally {
      envioEmAndamento.current = false;
      setEnviando(false);
    }
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        style={styles.safeArea}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.page}
          keyboardShouldPersistTaps="handled"
        >
          <View style={styles.card}>
            <Text style={styles.brand}>TETO JUSTO</Text>
            <Text accessibilityRole="header" style={styles.title}>
              Entre na sua casa.
            </Text>
            <Text style={styles.subtitle}>
              Use sua conta para acompanhar as tarefas e a pontuação.
            </Text>

            <Text style={styles.label}>E-mail</Text>
            <TextInput
              accessibilityLabel="E-mail"
              style={styles.input}
              placeholder="Seu e-mail"
              placeholderTextColor="#666"
              value={email}
              onChangeText={setEmail}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="email"
              keyboardType="email-address"
              editable={!enviando}
            />
            <Text style={styles.label}>Senha</Text>
            <TextInput
              accessibilityLabel="Senha"
              style={styles.input}
              placeholder="Sua senha"
              placeholderTextColor="#666"
              value={senha}
              onChangeText={setSenha}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="current-password"
              secureTextEntry
              editable={!enviando}
              returnKeyType="go"
              onSubmitEditing={() => void fazerLogin()}
            />
            {(erro || aviso) && (
              <Text accessibilityRole="alert" style={styles.error}>
                {erro || aviso}
              </Text>
            )}
            {mensagemCadastro && (
              <Text accessibilityRole="alert" style={styles.success}>
                {mensagemCadastro}
              </Text>
            )}
            <Pressable
              accessibilityLabel="Entrar"
              accessibilityRole="button"
              accessibilityState={{ disabled: enviando, busy: enviando }}
              aria-busy={enviando}
              disabled={enviando}
              onPress={() => void fazerLogin()}
              style={[styles.button, enviando && styles.disabled]}
            >
              {enviando ? (
                <ActivityIndicator color={Caldera.chalk} />
              ) : (
                <Text style={styles.buttonText}>Entrar</Text>
              )}
            </Pressable>
            <Pressable
              accessibilityLabel="Criar conta"
              accessibilityRole="button"
              accessibilityState={{ disabled: enviando }}
              disabled={enviando}
              onPress={() => onCriarConta(email.trim())}
              style={styles.createAccountButton}
            >
              <Text style={styles.createAccountText}>Criar conta</Text>
            </Pressable>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Caldera.limestone },
  page: { flexGrow: 1, justifyContent: "center", padding: 24 },
  card: { width: "100%", maxWidth: 440, alignSelf: "center" },
  brand: {
    color: Caldera.ember,
    fontWeight: "800",
    letterSpacing: 2,
    marginBottom: 24,
  },
  title: { fontSize: 36, fontWeight: "800", color: Caldera.obsidian },
  subtitle: {
    fontSize: 16,
    lineHeight: 24,
    color: "#555",
    marginTop: 12,
    marginBottom: 32,
  },
  label: { color: Caldera.obsidian, fontWeight: "600", marginBottom: 8 },
  input: {
    backgroundColor: Caldera.chalk,
    color: Caldera.obsidian,
    borderWidth: 1,
    borderColor: Caldera.pumice,
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    marginBottom: 20,
  },
  button: {
    backgroundColor: Caldera.ember,
    padding: 18,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 8,
  },
  buttonText: { color: Caldera.chalk, fontWeight: "700", fontSize: 16 },
  disabled: { opacity: 0.6 },
  error: { color: "#a32316", marginBottom: 12, lineHeight: 22 },
  success: { color: "#176b39", marginBottom: 12, lineHeight: 22 },
  createAccountButton: { alignItems: "center", padding: 16, marginTop: 8 },
  createAccountText: { color: Caldera.obsidian, fontWeight: "600" },
});
