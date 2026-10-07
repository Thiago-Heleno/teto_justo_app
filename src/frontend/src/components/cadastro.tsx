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
import { cadastrar } from "@/services/autenticacao-api";
import { validarCadastro, type ErrosCadastro } from "@/utils/cadastro";

export function CadastroScreen({
  emailInicial,
  onVoltar,
  onCadastrado,
}: {
  emailInicial: string;
  onVoltar: (email: string) => void;
  onCadastrado: (email: string) => void;
}) {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState(emailInicial);
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [errosCampos, setErrosCampos] = useState<ErrosCadastro>({});
  const [erro, setErro] = useState<string>();
  const [enviando, setEnviando] = useState(false);
  const envioEmAndamento = useRef(false);
  const nomeInput = useRef<TextInput>(null);
  const emailInput = useRef<TextInput>(null);
  const senhaInput = useRef<TextInput>(null);
  const confirmacaoInput = useRef<TextInput>(null);

  useEffect(() => {
    if (Platform.OS !== "android") return;
    const retorno = BackHandler.addEventListener("hardwareBackPress", () => {
      if (!enviando) onVoltar(email.trim());
      return true;
    });
    return () => retorno.remove();
  }, [email, enviando, onVoltar]);

  function focarPrimeiroErro(erros: ErrosCadastro) {
    if (erros.nome) nomeInput.current?.focus();
    else if (erros.email) emailInput.current?.focus();
    else if (erros.senha) senhaInput.current?.focus();
    else if (erros.confirmacao) confirmacaoInput.current?.focus();
  }

  async function enviar() {
    if (envioEmAndamento.current) return;
    const validacao = validarCadastro({ nome, email, senha, confirmacao });
    setErrosCampos(validacao);
    setErro(undefined);
    if (Object.keys(validacao).length) {
      focarPrimeiroErro(validacao);
      return;
    }

    envioEmAndamento.current = true;
    setEnviando(true);
    try {
      await cadastrar(nome, email, senha);
      setSenha("");
      setConfirmacao("");
      onCadastrado(email.trim());
    } catch (falha) {
      if (falha instanceof ErroApi && falha.status === 400) {
        setErrosCampos({
          email: "Este e-mail já está cadastrado. Entre na sua conta.",
        });
        emailInput.current?.focus();
      } else if (falha instanceof ErroApi && falha.status === 422) {
        const campos: ErrosCadastro = {};
        for (const validacao of falha.validacoes) {
          if (validacao.loc[0] !== "body") continue;
          if (validacao.loc[1] === "nome") campos.nome = "Informe seu nome.";
          else if (validacao.loc[1] === "email") {
            campos.email = "Informe um e-mail válido.";
          } else if (validacao.loc[1] === "senha") {
            campos.senha = validacao.msg;
          }
        }
        setErrosCampos(campos);
        setErro(
          Object.keys(campos).length
            ? undefined
            : "Confira os dados informados.",
        );
        focarPrimeiroErro(campos);
      } else if (falha instanceof TypeError) {
        setErro(
          "Não foi possível conectar ao servidor. Verifique sua conexão.",
        );
      } else {
        setErro("Não foi possível criar sua conta. Tente novamente.");
      }
    } finally {
      envioEmAndamento.current = false;
      setEnviando(false);
    }
  }

  function alterarCampo(campo: keyof ErrosCadastro, valor: string) {
    setErrosCampos((atuais) => ({ ...atuais, [campo]: undefined }));
    setErro(undefined);
    if (campo === "nome") setNome(valor);
    else if (campo === "email") setEmail(valor);
    else if (campo === "senha") setSenha(valor);
    else setConfirmacao(valor);
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
              Crie sua conta.
            </Text>
            <Text style={styles.subtitle}>
              Depois do cadastro, entre para criar ou acessar sua casa.
            </Text>

            <Text style={styles.label}>Nome</Text>
            <TextInput
              ref={nomeInput}
              accessibilityLabel="Nome"
              style={[styles.input, errosCampos.nome && styles.inputError]}
              placeholder="Seu nome"
              placeholderTextColor="#666"
              value={nome}
              onChangeText={(valor) => alterarCampo("nome", valor)}
              autoComplete="name"
              autoCapitalize="words"
              editable={!enviando}
              returnKeyType="next"
              onSubmitEditing={() => emailInput.current?.focus()}
            />
            {errosCampos.nome && (
              <Text accessibilityRole="alert" style={styles.fieldError}>
                {errosCampos.nome}
              </Text>
            )}

            <Text style={styles.label}>E-mail</Text>
            <TextInput
              ref={emailInput}
              accessibilityLabel="E-mail"
              style={[styles.input, errosCampos.email && styles.inputError]}
              placeholder="Seu e-mail"
              placeholderTextColor="#666"
              value={email}
              onChangeText={(valor) => alterarCampo("email", valor)}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="email"
              keyboardType="email-address"
              editable={!enviando}
              returnKeyType="next"
              onSubmitEditing={() => senhaInput.current?.focus()}
            />
            {errosCampos.email && (
              <Text accessibilityRole="alert" style={styles.fieldError}>
                {errosCampos.email}
              </Text>
            )}

            <Text style={styles.label}>Senha</Text>
            <TextInput
              ref={senhaInput}
              accessibilityLabel="Senha para cadastro"
              style={[styles.input, errosCampos.senha && styles.inputError]}
              placeholder="Crie uma senha"
              placeholderTextColor="#666"
              value={senha}
              onChangeText={(valor) => alterarCampo("senha", valor)}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="new-password"
              secureTextEntry
              editable={!enviando}
              returnKeyType="next"
              onSubmitEditing={() => confirmacaoInput.current?.focus()}
            />
            {errosCampos.senha && (
              <Text accessibilityRole="alert" style={styles.fieldError}>
                {errosCampos.senha}
              </Text>
            )}

            <Text style={styles.label}>Confirme a senha</Text>
            <TextInput
              ref={confirmacaoInput}
              accessibilityLabel="Confirme a senha"
              style={[
                styles.input,
                errosCampos.confirmacao && styles.inputError,
              ]}
              placeholder="Repita sua senha"
              placeholderTextColor="#666"
              value={confirmacao}
              onChangeText={(valor) => alterarCampo("confirmacao", valor)}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="new-password"
              secureTextEntry
              editable={!enviando}
              returnKeyType="go"
              onSubmitEditing={() => void enviar()}
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
            <Pressable
              accessibilityLabel="Criar conta"
              accessibilityRole="button"
              accessibilityState={{ disabled: enviando, busy: enviando }}
              disabled={enviando}
              onPress={() => void enviar()}
              style={[styles.button, enviando && styles.disabled]}
            >
              {enviando ? (
                <ActivityIndicator color={Caldera.chalk} />
              ) : (
                <Text style={styles.buttonText}>Criar conta</Text>
              )}
            </Pressable>
            <Pressable
              accessibilityLabel="Voltar ao login"
              accessibilityRole="button"
              accessibilityState={{ disabled: enviando }}
              disabled={enviando}
              onPress={() => onVoltar(email.trim())}
              style={styles.backButton}
            >
              <Text style={styles.backButtonText}>Já tenho conta</Text>
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
  inputError: { borderColor: "#a32316" },
  fieldError: { color: "#a32316", marginBottom: 12 },
  error: { color: "#a32316", marginBottom: 12, lineHeight: 22 },
  button: {
    backgroundColor: Caldera.ember,
    padding: 18,
    borderRadius: 12,
    alignItems: "center",
    marginTop: 12,
  },
  buttonText: { color: Caldera.chalk, fontWeight: "700", fontSize: 16 },
  backButton: { alignItems: "center", padding: 16, marginTop: 8 },
  backButtonText: { color: Caldera.obsidian, fontWeight: "600" },
  disabled: { opacity: 0.6 },
});
