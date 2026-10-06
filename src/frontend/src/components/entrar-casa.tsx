import { useEffect, useRef, useState } from "react";
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

import { Caldera, CompactFont } from "@/constants/theme";
import { ErroApi } from "@/services/api";
import { entrarCasa, type Casa } from "@/services/casas-api";

export function EntrarCasa({
  onVoltar,
  onEntrada,
}: {
  onVoltar: () => void;
  onEntrada: (casa: Casa, signal?: AbortSignal) => Promise<void>;
}) {
  const [convite, setConvite] = useState("");
  const [erroConvite, setErroConvite] = useState<string>();
  const [erro, setErro] = useState<string>();
  const [enviando, setEnviando] = useState(false);
  const [casaConfirmada, setCasaConfirmada] = useState<Casa | null>(null);
  const emAndamento = useRef(false);
  const requisicao = useRef<AbortController | null>(null);
  const conviteInput = useRef<TextInput>(null);

  useEffect(() => {
    const controlador = new AbortController();
    requisicao.current = controlador;
    return () => controlador.abort();
  }, []);

  async function enviar() {
    if (emAndamento.current) return;
    setErro(undefined);
    setErroConvite(undefined);
    if (!casaConfirmada && !convite.trim()) {
      setErroConvite("Cole o convite que você recebeu do administrador.");
      conviteInput.current?.focus();
      return;
    }

    emAndamento.current = true;
    setEnviando(true);
    const signal = requisicao.current?.signal;
    let casa = casaConfirmada;
    try {
      if (!casa) {
        casa = await entrarCasa(convite, signal);
        if (signal?.aborted) return;
        setCasaConfirmada(casa);
        setConvite("");
      }
      await onEntrada(casa, signal);
    } catch (falha) {
      if (signal?.aborted) return;
      if (casa) {
        setErro(
          "Sua entrada foi confirmada, mas não foi possível abrir a casa. Tente abrir novamente.",
        );
      } else if (falha instanceof ErroApi) {
        const mensagensConvite = falha.validacoes.filter(
          (validacao) =>
            validacao.loc[0] === "body" && validacao.loc[1] === "convite",
        );
        const mensagensGerais = falha.validacoes.filter(
          (validacao) =>
            validacao.loc[0] !== "body" || validacao.loc[1] !== "convite",
        );
        if (falha.status === 400) {
          setErroConvite(
            `${falha.message} Peça um novo convite ao administrador.`,
          );
        } else if (mensagensConvite.length) {
          setErroConvite(
            mensagensConvite.map((validacao) => validacao.msg).join(" "),
          );
        }
        if (mensagensGerais.length) {
          setErro(mensagensGerais.map((validacao) => validacao.msg).join(" "));
        } else if (falha.status !== 400 && !mensagensConvite.length) {
          setErro(falha.message);
        }
        if (falha.status === 400 || mensagensConvite.length)
          conviteInput.current?.focus();
      } else if (falha instanceof TypeError) {
        setErro(
          "Não foi possível confirmar sua entrada. Verifique sua conexão e tente novamente.",
        );
      } else {
        setErro("Não foi possível entrar na casa. Tente novamente.");
      }
    } finally {
      emAndamento.current = false;
      if (!signal?.aborted) setEnviando(false);
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
          <View style={styles.content}>
            <Text style={styles.brand}>TETO JUSTO</Text>
            <Text accessibilityRole="header" style={styles.title}>
              {casaConfirmada ? "CONVITE ACEITO" : "ENTRE NA CASA"}
            </Text>
            <Text style={styles.description}>
              {casaConfirmada
                ? `Você já faz parte de ${casaConfirmada.nome}. Abra a casa para continuar.`
                : "Cole o convite enviado pelo administrador da casa para participar das tarefas e acompanhar a pontuação."}
            </Text>

            {!casaConfirmada && (
              <View style={styles.field}>
                <Text style={styles.label}>Convite da casa</Text>
                <TextInput
                  ref={conviteInput}
                  accessibilityLabel="Convite da casa"
                  aria-invalid={Boolean(erroConvite)}
                  aria-describedby={
                    erroConvite ? "erro-convite-casa" : undefined
                  }
                  placeholder="Cole seu convite aqui"
                  placeholderTextColor="#666"
                  value={convite}
                  onChangeText={(valor) => {
                    setConvite(valor);
                    setErroConvite(undefined);
                    setErro(undefined);
                  }}
                  editable={!enviando}
                  multiline
                  autoCapitalize="none"
                  autoCorrect={false}
                  spellCheck={false}
                  autoComplete="off"
                  textAlignVertical="top"
                  style={[styles.input, erroConvite && styles.inputError]}
                />
                {erroConvite && (
                  <Text
                    nativeID="erro-convite-casa"
                    accessibilityRole="alert"
                    style={styles.error}
                  >
                    {erroConvite}
                  </Text>
                )}
                <Text style={styles.help}>
                  O convite vale por 24 horas. Se estiver vencido, peça um novo
                  ao administrador.
                </Text>
              </View>
            )}

            {erro && (
              <Text accessibilityRole="alert" style={styles.error}>
                {erro}
              </Text>
            )}

            <Pressable
              accessibilityRole="button"
              accessibilityLabel={
                casaConfirmada ? "Abrir casa" : "Entrar na casa"
              }
              accessibilityState={{ disabled: enviando, busy: enviando }}
              disabled={enviando}
              onPress={() => void enviar()}
              style={[styles.primaryButton, enviando && styles.dimmed]}
            >
              {enviando ? (
                <ActivityIndicator
                  color={Caldera.obsidian}
                  accessibilityLabel="Confirmando sua entrada"
                />
              ) : (
                <Text style={styles.buttonText}>
                  {casaConfirmada ? "Abrir casa" : "Entrar na casa"}
                </Text>
              )}
            </Pressable>
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ disabled: enviando }}
              disabled={enviando}
              onPress={onVoltar}
              style={[styles.secondaryButton, enviando && styles.dimmed]}
            >
              <Text style={styles.buttonText}>Voltar às casas</Text>
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
  content: { width: "100%", maxWidth: 560, alignSelf: "center", gap: 20 },
  brand: { color: Caldera.ember, fontWeight: "800", letterSpacing: 2 },
  title: {
    fontFamily: CompactFont,
    fontSize: 42,
    fontWeight: "800",
    color: Caldera.obsidian,
  },
  description: { color: "#555", fontSize: 16, lineHeight: 24 },
  field: { gap: 8 },
  label: { color: Caldera.obsidian, fontWeight: "600", fontSize: 16 },
  input: {
    backgroundColor: Caldera.chalk,
    color: Caldera.obsidian,
    borderWidth: 1,
    borderColor: Caldera.pumice,
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    minHeight: 132,
    maxHeight: 220,
  },
  inputError: { borderColor: "#a32316" },
  error: { color: "#a32316", lineHeight: 22 },
  help: { color: "#555", fontSize: 14, lineHeight: 21 },
  primaryButton: {
    backgroundColor: Caldera.ember,
    borderRadius: 24,
    padding: 18,
    alignItems: "center",
  },
  secondaryButton: {
    borderWidth: 1,
    borderColor: Caldera.obsidian,
    borderRadius: 24,
    padding: 16,
    alignItems: "center",
  },
  buttonText: { color: Caldera.obsidian, fontWeight: "700", fontSize: 16 },
  dimmed: { opacity: 0.6 },
});
