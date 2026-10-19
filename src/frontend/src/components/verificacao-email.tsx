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
import { ErroApi } from "@/services/api";
import {
  cadastrar,
  solicitarCodigoVerificacao,
  type DadosConta,
} from "@/services/autenticacao-api";
import { somenteDigitosDoCodigo, TAMANHO_CODIGO } from "@/utils/cadastro";

const ESPERA_REENVIO_SEGUNDOS = 30;

function mensagemDeErro(falha: unknown) {
  if (falha instanceof ErroApi) {
    if (falha.status === 400) {
      return falha.message === "E-mail já cadastrado."
        ? "Este e-mail já está cadastrado. Volte e entre na sua conta."
        : "Código inválido ou expirado. Confira o e-mail ou peça um novo código.";
    }
    if (falha.status === 429) {
      const segundos = falha.retryAfter;
      return segundos
        ? `Muitas tentativas. Tente novamente em ${segundos >= 60 ? `${Math.ceil(segundos / 60)} min` : `${segundos} s`}.`
        : "Muitas tentativas. Aguarde antes de tentar novamente.";
    }
    if (falha.status === 503) {
      return "Serviço temporariamente indisponível. Tente novamente em instantes.";
    }
    if (falha.status === 422) {
      return "Confira os dados do cadastro. Volte e revise o formulário.";
    }
  }
  if (falha instanceof TypeError) {
    return "Não foi possível conectar ao servidor. Verifique sua conexão.";
  }
  return "Não foi possível concluir o cadastro. Tente novamente.";
}

export function VerificacaoEmailScreen({
  dados,
  tokenInicial,
  onVerificado,
  onVoltar,
}: {
  dados: DadosConta;
  tokenInicial: string;
  onVerificado: (email: string) => void;
  onVoltar: (email: string) => void;
}) {
  const [codigo, setCodigo] = useState("");
  const [token, setToken] = useState(tokenInicial);
  const [erro, setErro] = useState<string>();
  const [aviso, setAviso] = useState<string>();
  const [enviando, setEnviando] = useState(false);
  const [reenviando, setReenviando] = useState(false);
  const [espera, setEspera] = useState(ESPERA_REENVIO_SEGUNDOS);
  const ocupado = useRef(false);
  const ocupadoTela = enviando || reenviando;

  useEffect(() => {
    if (espera <= 0) return;
    const temporizador = setTimeout(() => setEspera((s) => s - 1), 1000);
    return () => clearTimeout(temporizador);
  }, [espera]);

  useEffect(() => {
    if (Platform.OS !== "android") return;
    const retorno = BackHandler.addEventListener("hardwareBackPress", () => {
      if (!ocupado.current) onVoltar(dados.email);
      return true;
    });
    return () => retorno.remove();
  }, [dados.email, onVoltar]);

  async function verificar() {
    if (ocupado.current) return;
    if (codigo.length !== TAMANHO_CODIGO) {
      setErro(`Digite os ${TAMANHO_CODIGO} dígitos do código.`);
      return;
    }
    ocupado.current = true;
    setEnviando(true);
    setErro(undefined);
    setAviso(undefined);
    try {
      await cadastrar(dados, codigo, token);
      onVerificado(dados.email);
    } catch (falha) {
      setErro(mensagemDeErro(falha));
    } finally {
      ocupado.current = false;
      setEnviando(false);
    }
  }

  async function reenviar() {
    if (ocupado.current || espera > 0) return;
    ocupado.current = true;
    setReenviando(true);
    setErro(undefined);
    setAviso(undefined);
    try {
      setToken(await solicitarCodigoVerificacao(dados));
      setCodigo("");
      setAviso("Enviamos um novo código para o seu e-mail.");
      setEspera(ESPERA_REENVIO_SEGUNDOS);
    } catch (falha) {
      setErro(mensagemDeErro(falha));
    } finally {
      ocupado.current = false;
      setReenviando(false);
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
              Confirme seu e-mail.
            </Text>
            <Text style={styles.subtitle}>
              Enviamos um código de {TAMANHO_CODIGO} dígitos para {dados.email}.
              Ele vale por 10 minutos.
            </Text>

            <Text style={styles.label}>Código de verificação</Text>
            <TextInput
              accessibilityLabel="Código de verificação"
              style={[styles.input, erro && styles.inputError]}
              placeholder="00000"
              placeholderTextColor="#999"
              value={codigo}
              onChangeText={(valor) => {
                setCodigo(somenteDigitosDoCodigo(valor));
                setErro(undefined);
              }}
              keyboardType="number-pad"
              autoComplete="one-time-code"
              textContentType="oneTimeCode"
              maxLength={TAMANHO_CODIGO}
              editable={!ocupadoTela}
              returnKeyType="go"
              onSubmitEditing={() => void verificar()}
            />
            {erro && (
              <Text accessibilityRole="alert" style={styles.error}>
                {erro}
              </Text>
            )}
            {aviso && (
              <Text accessibilityRole="alert" style={styles.success}>
                {aviso}
              </Text>
            )}

            <Pressable
              accessibilityLabel="Verificar e criar conta"
              accessibilityRole="button"
              accessibilityState={{ disabled: ocupadoTela, busy: enviando }}
              disabled={ocupadoTela}
              onPress={() => void verificar()}
              style={[styles.button, ocupadoTela && styles.disabled]}
            >
              {enviando ? (
                <ActivityIndicator color={Caldera.chalk} />
              ) : (
                <Text style={styles.buttonText}>Verificar e criar conta</Text>
              )}
            </Pressable>
            <Pressable
              accessibilityLabel="Reenviar código"
              accessibilityRole="button"
              accessibilityState={{
                disabled: ocupadoTela || espera > 0,
                busy: reenviando,
              }}
              disabled={ocupadoTela || espera > 0}
              onPress={() => void reenviar()}
              style={[
                styles.linkButton,
                (ocupadoTela || espera > 0) && styles.disabled,
              ]}
            >
              <Text style={styles.linkText}>
                {reenviando
                  ? "Enviando..."
                  : espera > 0
                    ? `Reenviar código em ${espera} s`
                    : "Reenviar código"}
              </Text>
            </Pressable>
            <Pressable
              accessibilityLabel="Voltar ao cadastro"
              accessibilityRole="button"
              accessibilityState={{ disabled: ocupadoTela }}
              disabled={ocupadoTela}
              onPress={() => onVoltar(dados.email)}
              style={styles.linkButton}
            >
              <Text style={styles.linkText}>Corrigir meus dados</Text>
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
    fontSize: 32,
    fontWeight: "800",
    letterSpacing: 12,
    textAlign: "center",
    marginBottom: 12,
  },
  inputError: { borderColor: "#a32316" },
  error: { color: "#a32316", marginBottom: 12, lineHeight: 22 },
  success: { color: "#176b39", marginBottom: 12, lineHeight: 22 },
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
