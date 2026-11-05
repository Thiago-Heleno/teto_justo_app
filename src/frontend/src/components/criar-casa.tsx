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
import {
  criarCasa,
  type Casa,
  type CasaCriar,
  type PoliticaReclamacao,
} from "@/services/casas-api";

type ErrosCampos = Partial<Record<keyof CasaCriar, string>>;

export function CriarCasa({
  onVoltar,
  onCriada,
}: {
  onVoltar: () => void;
  onCriada: (casa: Casa, signal?: AbortSignal) => Promise<void>;
}) {
  const [nome, setNome] = useState("");
  const [endereco, setEndereco] = useState("");
  const [politicaReclamacao, setPoliticaReclamacao] =
    useState<PoliticaReclamacao>("nenhuma");
  const [errosCampos, setErrosCampos] = useState<ErrosCampos>({});
  const [erro, setErro] = useState<string>();
  const [enviando, setEnviando] = useState(false);
  const [casaCriada, setCasaCriada] = useState<Casa | null>(null);
  const emAndamento = useRef(false);
  const requisicao = useRef<AbortController | null>(null);
  const nomeInput = useRef<TextInput>(null);
  const enderecoInput = useRef<TextInput>(null);

  useEffect(() => {
    const controlador = new AbortController();
    requisicao.current = controlador;
    return () => controlador.abort();
  }, []);

  async function enviar() {
    if (emAndamento.current) return;
    const validacao: ErrosCampos = {};
    if (!nome.trim()) validacao.nome = "Informe o nome da casa.";
    if (!endereco.trim()) validacao.endereco = "Informe o endereço da casa.";
    setErrosCampos(validacao);
    setErro(undefined);
    if (validacao.nome || validacao.endereco) {
      (validacao.nome ? nomeInput : enderecoInput).current?.focus();
      return;
    }

    emAndamento.current = true;
    setEnviando(true);
    const signal = requisicao.current?.signal;
    let criada = casaCriada;
    try {
      if (!criada) {
        criada = await criarCasa(
          { nome, endereco, politica_reclamacao: politicaReclamacao },
          signal,
        );
        if (signal?.aborted) return;
        setCasaCriada(criada);
      }
      await onCriada(criada, signal);
    } catch (falha) {
      if (signal?.aborted) return;
      if (criada) {
        setErro(
          "Sua casa foi criada, mas não foi possível abri-la. Tente abrir novamente.",
        );
      } else if (falha instanceof ErroApi) {
        const campos: ErrosCampos = {};
        const gerais: string[] = [];
        for (const validacao of falha.validacoes) {
          const campo = validacao.loc[1];
          if (validacao.loc[0] === "body" && campo === "nome") {
            campos.nome = [campos.nome, validacao.msg]
              .filter(Boolean)
              .join(" ");
          } else if (validacao.loc[0] === "body" && campo === "endereco") {
            campos.endereco = [campos.endereco, validacao.msg]
              .filter(Boolean)
              .join(" ");
          } else {
            gerais.push(validacao.msg);
          }
        }
        setErrosCampos(campos);
        if (gerais.length) setErro(gerais.join(" "));
        else if (!campos.nome && !campos.endereco) setErro(falha.message);
        if (campos.nome) nomeInput.current?.focus();
        else if (campos.endereco) enderecoInput.current?.focus();
      } else if (falha instanceof TypeError) {
        setErro(
          "Não foi possível confirmar a criação. Verifique sua conexão e confira a lista de casas antes de tentar novamente.",
        );
      } else {
        setErro("Não foi possível criar a casa. Tente novamente.");
      }
    } finally {
      emAndamento.current = false;
      if (!signal?.aborted) setEnviando(false);
    }
  }

  const editavel = !enviando && !casaCriada;

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
              {casaCriada ? "CASA CRIADA" : "CRIE SUA CASA"}
            </Text>
            <Text style={styles.description}>
              {casaCriada
                ? "Tudo pronto. Abra sua casa para começar."
                : "Dê um nome ao seu lar. Você será o administrador e poderá organizar as tarefas da casa."}
            </Text>

            <View style={styles.field}>
              <Text style={styles.label}>Nome da casa</Text>
              <TextInput
                ref={nomeInput}
                accessibilityLabel="Nome da casa"
                aria-invalid={Boolean(errosCampos.nome)}
                aria-describedby={
                  errosCampos.nome ? "erro-nome-casa" : undefined
                }
                placeholder="Ex.: Casa das Flores"
                placeholderTextColor="#666"
                value={nome}
                onChangeText={(valor) => {
                  setNome(valor);
                  setErrosCampos((atuais) => ({ ...atuais, nome: undefined }));
                }}
                editable={editavel}
                autoCapitalize="sentences"
                returnKeyType="next"
                onSubmitEditing={() => enderecoInput.current?.focus()}
                style={[styles.input, errosCampos.nome && styles.inputError]}
              />
              {errosCampos.nome && (
                <Text
                  nativeID="erro-nome-casa"
                  accessibilityRole="alert"
                  style={styles.error}
                >
                  {errosCampos.nome}
                </Text>
              )}
            </View>

            <View style={styles.field}>
              <Text style={styles.label}>Endereço</Text>
              <TextInput
                ref={enderecoInput}
                accessibilityLabel="Endereço"
                aria-invalid={Boolean(errosCampos.endereco)}
                aria-describedby={
                  errosCampos.endereco ? "erro-endereco-casa" : undefined
                }
                placeholder="Rua, número e cidade"
                placeholderTextColor="#666"
                value={endereco}
                onChangeText={(valor) => {
                  setEndereco(valor);
                  setErrosCampos((atuais) => ({
                    ...atuais,
                    endereco: undefined,
                  }));
                }}
                editable={editavel}
                autoCapitalize="words"
                autoComplete="street-address"
                returnKeyType="go"
                onSubmitEditing={() => void enviar()}
                style={[
                  styles.input,
                  errosCampos.endereco && styles.inputError,
                ]}
              />
              {errosCampos.endereco && (
                <Text
                  nativeID="erro-endereco-casa"
                  accessibilityRole="alert"
                  style={styles.error}
                >
                  {errosCampos.endereco}
                </Text>
              )}
            </View>

            <View style={styles.field}>
              <Text style={styles.label}>Política de reclamações</Text>
              <Text style={styles.optionDescription}>
                Defina como as reclamações serão tratadas e quando o responsável
                pela tarefa receberá notificações.
              </Text>
              {(
                [
                  {
                    value: "nenhuma",
                    title: "Sem reclamações",
                    description:
                      "Esta casa não utiliza o sistema de reclamações de tarefas.",
                  },
                  {
                    value: "uma_reclamacao",
                    title: "A cada reclamação",
                    description:
                      "O responsável recebe um aviso a cada reclamação. A tarefa reabre quando o mínimo de reclamações é atingido.",
                  },
                  {
                    value: "votacao",
                    title: "Somente na reabertura",
                    description:
                      "O responsável só recebe um aviso quando a tarefa é reaberta por atingir o mínimo de reclamações.",
                  },
                ] as const
              ).map((opcao) => {
                const selecionada = politicaReclamacao === opcao.value;
                return (
                  <Pressable
                    key={opcao.value}
                    accessibilityRole="radio"
                    accessibilityState={{
                      checked: selecionada,
                      disabled: !editavel,
                    }}
                    disabled={!editavel}
                    onPress={() => setPoliticaReclamacao(opcao.value)}
                    style={[
                      styles.policyOption,
                      selecionada && styles.policyOptionSelected,
                      !editavel && styles.dimmed,
                    ]}
                  >
                    <View style={styles.policyHeading}>
                      <View
                        style={[
                          styles.radio,
                          selecionada && styles.radioSelected,
                        ]}
                      >
                        {selecionada && <View style={styles.radioDot} />}
                      </View>
                      <Text style={styles.policyTitle}>{opcao.title}</Text>
                    </View>
                    <Text style={styles.optionDescription}>
                      {opcao.description}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            {erro && (
              <Text accessibilityRole="alert" style={styles.error}>
                {erro}
              </Text>
            )}

            <Pressable
              accessibilityRole="button"
              accessibilityLabel={casaCriada ? "Abrir casa" : "Criar casa"}
              accessibilityState={{ disabled: enviando, busy: enviando }}
              disabled={enviando}
              onPress={() => void enviar()}
              style={[styles.primaryButton, enviando && styles.dimmed]}
            >
              {enviando ? (
                <ActivityIndicator
                  color={Caldera.obsidian}
                  accessibilityLabel="Salvando sua casa"
                />
              ) : (
                <Text style={styles.buttonText}>
                  {casaCriada ? "Abrir casa" : "Criar casa"}
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
  optionDescription: { color: "#555", fontSize: 14, lineHeight: 21 },
  policyOption: {
    borderWidth: 1,
    borderColor: Caldera.pumice,
    borderRadius: 16,
    padding: 16,
    gap: 8,
    backgroundColor: Caldera.chalk,
  },
  policyOptionSelected: {
    borderColor: Caldera.ember,
    borderWidth: 2,
  },
  policyHeading: { flexDirection: "row", alignItems: "center", gap: 10 },
  policyTitle: { color: Caldera.obsidian, fontWeight: "700", fontSize: 15 },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    alignItems: "center",
    justifyContent: "center",
  },
  radioSelected: { borderColor: Caldera.ember },
  radioDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: Caldera.ember,
  },
  label: { color: Caldera.obsidian, fontWeight: "600", fontSize: 16 },
  input: {
    backgroundColor: Caldera.chalk,
    color: Caldera.obsidian,
    borderWidth: 1,
    borderColor: Caldera.pumice,
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
  },
  inputError: { borderColor: "#a32316" },
  error: { color: "#a32316", lineHeight: 22 },
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
