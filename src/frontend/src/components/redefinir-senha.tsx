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
  redefinirSenha,
  solicitarRecuperacaoSenha,
} from "@/services/autenticacao-api";
import {
  somenteDigitosDoCodigo,
  TAMANHO_CODIGO,
  validarNovaSenha,
  type ErrosCadastro,
} from "@/utils/cadastro";
import {
  ESPERA_REENVIO_SEGUNDOS,
  mensagemDeErroRecuperacao,
} from "@/utils/recuperacao-senha";

export function RedefinirSenhaScreen({
  email,
  tokenInicial,
  onRedefinida,
  onVoltar,
}: {
  email: string;
  tokenInicial: string;
  onRedefinida: (email: string) => void;
  onVoltar: (email: string) => void;
}) {
  const [codigo, setCodigo] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [token, setToken] = useState(tokenInicial);
  const [errosCampos, setErrosCampos] = useState<ErrosCadastro>({});
  const [erroCodigo, setErroCodigo] = useState<string>();
  const [erro, setErro] = useState<string>();
  const [aviso, setAviso] = useState<string>();
  const [enviando, setEnviando] = useState(false);
  const [reenviando, setReenviando] = useState(false);
  const [espera, setEspera] = useState(ESPERA_REENVIO_SEGUNDOS);
  const ocupado = useRef(false);
  const senhaInput = useRef<TextInput>(null);
  const confirmacaoInput = useRef<TextInput>(null);
  const ocupadoTela = enviando || reenviando;

  useEffect(() => {
    if (espera <= 0) return;
    const temporizador = setTimeout(() => setEspera((s) => s - 1), 1000);
    return () => clearTimeout(temporizador);
  }, [espera]);

  useEffect(() => {
    if (Platform.OS !== "android") return;
    const retorno = BackHandler.addEventListener("hardwareBackPress", () => {
      if (!ocupado.current) onVoltar(email);
      return true;
    });
    return () => retorno.remove();
  }, [email, onVoltar]);

  async function redefinir() {
    if (ocupado.current) return;
    const erroDoCodigo =
      codigo.length === TAMANHO_CODIGO
        ? undefined
        : `Digite os ${TAMANHO_CODIGO} dígitos do código.`;
    const erros = validarNovaSenha({ senha, confirmacao });
    setErroCodigo(erroDoCodigo);
    setErrosCampos(erros);
    setErro(undefined);
    setAviso(undefined);
    if (erroDoCodigo || Object.keys(erros).length) return;

    ocupado.current = true;
    setEnviando(true);
    try {
      await redefinirSenha(email, codigo, token, senha);
      setSenha("");
      setConfirmacao("");
      onRedefinida(email);
    } catch (falha) {
      if (falha instanceof ErroApi && falha.status === 400) {
        setErro(
          "Código inválido ou expirado. Confira o e-mail ou peça um novo código.",
        );
      } else if (falha instanceof ErroApi && falha.status === 422) {
        const mensagem = falha.validacoes.find(
          (validacao) => validacao.loc[1] === "nova_senha",
        )?.msg;
        if (mensagem) {
          setErrosCampos({ senha: mensagem });
          senhaInput.current?.focus();
        } else {
          setErro("Confira os dados informados.");
        }
      } else {
        setErro(
          mensagemDeErroRecuperacao(
            falha,
            "Não foi possível redefinir a senha. Tente novamente.",
          ),
        );
      }
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
      setToken(await solicitarRecuperacaoSenha(email));
      setCodigo("");
      setAviso("Se o e-mail estiver cadastrado, enviamos um novo código.");
      setEspera(ESPERA_REENVIO_SEGUNDOS);
    } catch (falha) {
      setErro(
        mensagemDeErroRecuperacao(
          falha,
          "Não foi possível enviar o código. Tente novamente.",
        ),
      );
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
              Crie uma nova senha.
            </Text>
            <Text style={styles.subtitle}>
              Se {email} estiver cadastrado, enviamos um código de{" "}
              {TAMANHO_CODIGO} dígitos para ele. O código vale por 10 minutos.
            </Text>

            <Text style={styles.label}>Código</Text>
            <TextInput
              accessibilityLabel="Código de verificação"
              style={[
                styles.input,
                styles.codeInput,
                erroCodigo && styles.inputError,
              ]}
              placeholder="00000"
              placeholderTextColor="#999"
              value={codigo}
              onChangeText={(valor) => {
                setCodigo(somenteDigitosDoCodigo(valor));
                setErroCodigo(undefined);
                setErro(undefined);
              }}
              keyboardType="number-pad"
              autoComplete="one-time-code"
              textContentType="oneTimeCode"
              maxLength={TAMANHO_CODIGO}
              editable={!ocupadoTela}
              returnKeyType="next"
              onSubmitEditing={() => senhaInput.current?.focus()}
            />
            {erroCodigo && (
              <Text accessibilityRole="alert" style={styles.fieldError}>
                {erroCodigo}
              </Text>
            )}

            <Text style={styles.label}>Nova senha</Text>
            <TextInput
              ref={senhaInput}
              accessibilityLabel="Nova senha"
              style={[styles.input, errosCampos.senha && styles.inputError]}
              placeholder="Crie uma senha"
              placeholderTextColor="#666"
              value={senha}
              onChangeText={(valor) => {
                setSenha(valor);
                setErrosCampos((atuais) => ({ ...atuais, senha: undefined }));
                setErro(undefined);
              }}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="new-password"
              secureTextEntry
              editable={!ocupadoTela}
              returnKeyType="next"
              onSubmitEditing={() => confirmacaoInput.current?.focus()}
            />
            {errosCampos.senha && (
              <Text accessibilityRole="alert" style={styles.fieldError}>
                {errosCampos.senha}
              </Text>
            )}

            <Text style={styles.label}>Confirme a nova senha</Text>
            <TextInput
              ref={confirmacaoInput}
              accessibilityLabel="Confirme a nova senha"
              style={[
                styles.input,
                errosCampos.confirmacao && styles.inputError,
              ]}
              placeholder="Repita a senha"
              placeholderTextColor="#666"
              value={confirmacao}
              onChangeText={(valor) => {
                setConfirmacao(valor);
                setErrosCampos((atuais) => ({
                  ...atuais,
                  confirmacao: undefined,
                }));
                setErro(undefined);
              }}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="new-password"
              secureTextEntry
              editable={!ocupadoTela}
              returnKeyType="go"
              onSubmitEditing={() => void redefinir()}
            />
            {errosCampos.confirmacao && (
              <Text accessibilityRole="alert" style={styles.fieldError}>
                {errosCampos.confirmacao}
              </Text>
            )}

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
              accessibilityLabel="Redefinir senha"
              accessibilityRole="button"
              accessibilityState={{ disabled: ocupadoTela, busy: enviando }}
              disabled={ocupadoTela}
              onPress={() => void redefinir()}
              style={[styles.button, ocupadoTela && styles.disabled]}
            >
              {enviando ? (
                <ActivityIndicator color={Caldera.chalk} />
              ) : (
                <Text style={styles.buttonText}>Redefinir senha</Text>
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
              accessibilityLabel="Voltar ao login"
              accessibilityRole="button"
              accessibilityState={{ disabled: ocupadoTela }}
              disabled={ocupadoTela}
              onPress={() => onVoltar(email)}
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
    marginBottom: 8,
  },
  codeInput: {
    fontSize: 32,
    fontWeight: "800",
    letterSpacing: 12,
    textAlign: "center",
  },
  inputError: { borderColor: "#a32316" },
  fieldError: { color: "#a32316", marginBottom: 12 },
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
