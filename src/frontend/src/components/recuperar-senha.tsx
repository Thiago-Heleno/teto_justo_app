import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  BackHandler,
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
import { solicitarRecuperacaoSenha } from "@/services/autenticacao-api";
import { validarEmail } from "@/utils/cadastro";
import { mensagemDeErroRecuperacao } from "@/utils/recuperacao-senha";

export function RecuperarSenhaScreen({
  emailInicial,
  onVoltar,
  onCodigoEnviado,
}: {
  emailInicial: string;
  onVoltar: (email: string) => void;
  onCodigoEnviado: (email: string, tokenVerificacao: string) => void;
}) {
  const [email, setEmail] = useState(emailInicial);
  const [erro, setErro] = useState<string>();
  const [enviando, setEnviando] = useState(false);
  const envioEmAndamento = useRef(false);

  useEffect(() => {
    if (Platform.OS !== "android") return;
    const retorno = BackHandler.addEventListener("hardwareBackPress", () => {
      if (!enviando) onVoltar(email.trim());
      return true;
    });
    return () => retorno.remove();
  }, [email, enviando, onVoltar]);

  async function enviar() {
    if (envioEmAndamento.current) return;
    const erroEmail = validarEmail(email);
    setErro(erroEmail);
    if (erroEmail) return;

    envioEmAndamento.current = true;
    setEnviando(true);
    try {
      const token = await solicitarRecuperacaoSenha(email);
      onCodigoEnviado(email.trim(), token);
    } catch (falha) {
      setErro(
        mensagemDeErroRecuperacao(
          falha,
          "Não foi possível enviar o código. Tente novamente.",
        ),
      );
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
              Esqueceu a senha?
            </Text>
            <Text style={styles.subtitle}>
              Informe o e-mail da sua conta. Se ele estiver cadastrado,
              enviaremos um código para criar uma nova senha.
            </Text>

            <Text style={styles.label}>E-mail</Text>
            <TextInput
              accessibilityLabel="E-mail"
              style={[styles.input, erro && styles.inputError]}
              placeholder="Seu e-mail"
              placeholderTextColor="#666"
              value={email}
              onChangeText={(valor) => {
                setEmail(valor);
                setErro(undefined);
              }}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="email"
              keyboardType="email-address"
              editable={!enviando}
              returnKeyType="go"
              onSubmitEditing={() => void enviar()}
            />
            {erro && (
              <Text accessibilityRole="alert" style={styles.error}>
                {erro}
              </Text>
            )}

            <Pressable
              accessibilityLabel="Enviar código"
              accessibilityRole="button"
              accessibilityState={{ disabled: enviando, busy: enviando }}
              disabled={enviando}
              onPress={() => void enviar()}
              style={[styles.button, enviando && styles.disabled]}
            >
              {enviando ? (
                <ActivityIndicator color={Caldera.chalk} />
              ) : (
                <Text style={styles.buttonText}>Enviar código</Text>
              )}
            </Pressable>
            <Pressable
              accessibilityLabel="Voltar ao login"
              accessibilityRole="button"
              accessibilityState={{ disabled: enviando }}
              disabled={enviando}
              onPress={() => onVoltar(email.trim())}
              style={styles.linkButton}
            >
              <Text style={styles.linkText}>Voltar ao login</Text>
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
    marginBottom: 12,
  },
  inputError: { borderColor: "#a32316" },
  error: { color: "#a32316", marginBottom: 12, lineHeight: 22 },
  button: {
    backgroundColor: Caldera.ember,
    padding: 18,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 12,
  },
  buttonText: { color: Caldera.chalk, fontWeight: "700", fontSize: 16 },
  linkButton: { alignItems: "center", padding: 16, marginTop: 8 },
  linkText: { color: Caldera.obsidian, fontWeight: "600" },
  disabled: { opacity: 0.6 },
});
