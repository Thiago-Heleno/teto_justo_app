import { useRef, useState } from "react";
import {
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ThemedText } from "@/components/themed-text";
import { pesosTarefa, type PesoTarefa } from "@/constants/tarefa";
import { Spacing } from "@/constants/theme";
import {
  casaDemonstracao,
  moradoresDemonstracao,
  usuarioDemonstracaoId,
} from "@/data/tarefa-demonstracao";
import { useTheme } from "@/hooks/use-theme";
import { TarefaDemonstracao, validarPrazo } from "@/utils/prazo-tarefa";

type Erros = {
  nome?: string;
  peso?: string;
  data?: string;
  horario?: string;
  responsaveis?: string;
};

function ErroCampo({ mensagem }: { mensagem?: string }) {
  if (!mensagem) return null;
  return (
    <ThemedText type="small" accessibilityLiveRegion="polite">
      Atenção: {mensagem}
    </ThemedText>
  );
}

export default function NovaTarefaScreen() {
  const theme = useTheme();
  const scrollRef = useRef<ScrollView>(null);
  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const [peso, setPeso] = useState<PesoTarefa | null>(null);
  const [data, setData] = useState("");
  const [horario, setHorario] = useState("");
  const [responsaveis, setResponsaveis] = useState<string[]>([]);
  const [erros, setErros] = useState<Erros>({});
  const [tarefa, setTarefa] = useState<TarefaDemonstracao | null>(null);

  const inputStyle = [
    styles.input,
    {
      color: theme.text,
      backgroundColor: theme.backgroundElement,
      borderColor: theme.textSecondary,
    },
  ];

  function alternarResponsavel(id: string) {
    setResponsaveis((atuais) =>
      atuais.includes(id)
        ? atuais.filter((selecionado) => selecionado !== id)
        : [...atuais, id],
    );
    setErros((atuais) => ({ ...atuais, responsaveis: undefined }));
  }

  function criarTarefa() {
    const prazo = validarPrazo(data.trim(), horario.trim());
    const novosErros: Erros = {
      nome: nome.trim() ? undefined : "Informe o nome da tarefa.",
      peso: peso === null ? "Selecione o peso da tarefa." : undefined,
      data: prazo.erroData,
      horario: prazo.erroHorario,
      responsaveis: responsaveis.length
        ? undefined
        : "Selecione pelo menos um responsável.",
    };
    setErros(novosErros);
    Keyboard.dismiss();

    if (
      Object.values(novosErros).some(Boolean) ||
      !prazo.data_fim ||
      peso === null
    ) {
      scrollRef.current?.scrollTo({ y: 0, animated: true });
      return;
    }

    setTarefa({
      nome: nome.trim(),
      descricao: descricao.trim(),
      peso,
      data_fim: prazo.data_fim,
      usuarios_atribuidos: [...responsaveis],
    });
    scrollRef.current?.scrollTo({ y: 0, animated: false });
  }

  function criarOutraTarefa() {
    setNome("");
    setDescricao("");
    setPeso(null);
    setData("");
    setHorario("");
    setResponsaveis([]);
    setErros({});
    setTarefa(null);
    scrollRef.current?.scrollTo({ y: 0, animated: false });
  }

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: theme.background }]}
      edges={["top", "left", "right"]}
    >
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <ScrollView
          ref={scrollRef}
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="on-drag"
        >
          <View style={styles.form}>
            <View style={styles.section}>
              <ThemedText type="smallBold" themeColor="textSecondary">
                {casaDemonstracao.nome}
              </ThemedText>
              <ThemedText accessibilityRole="header" style={styles.title}>
                {tarefa ? "Tudo pronto!" : "Nova tarefa"}
              </ThemedText>
              <ThemedText type="small" themeColor="textSecondary">
                Demonstração com dados fictícios.
              </ThemedText>
            </View>

            {tarefa ? (
              <>
                <View
                  style={[
                    styles.summary,
                    { backgroundColor: theme.backgroundElement },
                  ]}
                >
                  <ThemedText
                    accessibilityRole="header"
                    accessibilityLiveRegion="polite"
                    style={styles.summaryTitle}
                  >
                    Tarefa criada nesta demonstração
                  </ThemedText>
                  <ThemedText type="smallBold">Nome</ThemedText>
                  <ThemedText>{tarefa.nome}</ThemedText>
                  <ThemedText type="smallBold">Descrição</ThemedText>
                  <ThemedText>
                    {tarefa.descricao || "Sem descrição."}
                  </ThemedText>
                  <ThemedText type="smallBold">Peso</ThemedText>
                  <ThemedText>{tarefa.peso}</ThemedText>
                  <ThemedText type="smallBold">Prazo</ThemedText>
                  <ThemedText>
                    {new Date(tarefa.data_fim).toLocaleString("pt-BR", {
                      day: "2-digit",
                      month: "2-digit",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                      hour12: false,
                    })}
                  </ThemedText>
                  <ThemedText type="smallBold">Responsáveis</ThemedText>
                  {moradoresDemonstracao
                    .filter((morador) =>
                      tarefa.usuarios_atribuidos.includes(morador.id),
                    )
                    .map((morador) => (
                      <ThemedText key={morador.id}>{morador.nome}</ThemedText>
                    ))}
                </View>
                <Pressable
                  accessibilityRole="button"
                  onPress={criarOutraTarefa}
                  style={({ pressed }) => [
                    styles.button,
                    { backgroundColor: theme.text },
                    pressed && styles.pressed,
                  ]}
                >
                  <ThemedText style={{ color: theme.background }}>
                    Criar outra tarefa
                  </ThemedText>
                </Pressable>
              </>
            ) : (
              <>
                <View style={styles.section}>
                  <ThemedText type="smallBold">Nome *</ThemedText>
                  <TextInput
                    accessibilityLabel="Nome da tarefa, obrigatório"
                    accessibilityHint={erros.nome}
                    style={inputStyle}
                    placeholder="Ex.: Limpar a cozinha"
                    placeholderTextColor={theme.textSecondary}
                    value={nome}
                    onChangeText={(valor) => {
                      setNome(valor);
                      setErros((atuais) => ({ ...atuais, nome: undefined }));
                    }}
                  />
                  <ErroCampo mensagem={erros.nome} />
                </View>

                <View style={styles.section}>
                  <ThemedText type="smallBold">Descrição (opcional)</ThemedText>
                  <TextInput
                    accessibilityLabel="Descrição, opcional"
                    style={[inputStyle, styles.description]}
                    placeholder="O que precisa ser feito?"
                    placeholderTextColor={theme.textSecondary}
                    multiline
                    textAlignVertical="top"
                    value={descricao}
                    onChangeText={setDescricao}
                  />
                </View>

                <View style={styles.section}>
                  <ThemedText type="smallBold">Peso *</ThemedText>
                  <ThemedText type="small" themeColor="textSecondary">
                    Selecione a dificuldade: 1 é a menor e 4 é a maior.
                  </ThemedText>
                  <View style={styles.weights}>
                    {pesosTarefa.map((opcao) => (
                      <Pressable
                        key={opcao}
                        accessibilityRole="radio"
                        accessibilityLabel={`Peso ${opcao}`}
                        accessibilityState={{ checked: peso === opcao }}
                        onPress={() => {
                          setPeso(opcao);
                          setErros((atuais) => ({
                            ...atuais,
                            peso: undefined,
                          }));
                        }}
                        style={({ pressed }) => [
                          styles.weight,
                          {
                            backgroundColor:
                              peso === opcao
                                ? theme.backgroundSelected
                                : theme.backgroundElement,
                            borderColor:
                              peso === opcao ? theme.text : theme.textSecondary,
                          },
                          pressed && styles.pressed,
                        ]}
                      >
                        <ThemedText>
                          {peso === opcao ? "◉" : "○"} {opcao}
                        </ThemedText>
                      </Pressable>
                    ))}
                  </View>
                  <ErroCampo mensagem={erros.peso} />
                </View>

                <View style={styles.section}>
                  <ThemedText type="smallBold">Data limite *</ThemedText>
                  <TextInput
                    accessibilityLabel="Data limite, obrigatória, DD/MM/AAAA"
                    accessibilityHint={erros.data}
                    style={inputStyle}
                    placeholder="DD/MM/AAAA"
                    placeholderTextColor={theme.textSecondary}
                    keyboardType="numbers-and-punctuation"
                    maxLength={10}
                    value={data}
                    onChangeText={(valor) => {
                      setData(valor);
                      setErros((atuais) => ({
                        ...atuais,
                        data: undefined,
                        horario: undefined,
                      }));
                    }}
                  />
                  <ErroCampo mensagem={erros.data} />
                  <ThemedText type="smallBold">Horário limite *</ThemedText>
                  <TextInput
                    accessibilityLabel="Horário limite, obrigatório, HH:mm"
                    accessibilityHint={erros.horario}
                    style={inputStyle}
                    placeholder="HH:mm"
                    placeholderTextColor={theme.textSecondary}
                    keyboardType="numbers-and-punctuation"
                    maxLength={5}
                    value={horario}
                    onChangeText={(valor) => {
                      setHorario(valor);
                      setErros((atuais) => ({ ...atuais, horario: undefined }));
                    }}
                  />
                  <ErroCampo mensagem={erros.horario} />
                  <ThemedText type="small" themeColor="textSecondary">
                    Use o horário local do seu dispositivo, em formato de 24
                    horas.
                  </ThemedText>
                </View>

                <View style={styles.section}>
                  <ThemedText accessibilityRole="header" type="smallBold">
                    Responsáveis *
                  </ThemedText>
                  <ThemedText type="small" themeColor="textSecondary">
                    Selecione um ou mais moradores desta casa.
                  </ThemedText>
                  {moradoresDemonstracao.map((morador) => {
                    const selecionado = responsaveis.includes(morador.id);
                    const nomeExibido = `${morador.nome}${
                      morador.id === usuarioDemonstracaoId ? " (você)" : ""
                    }`;
                    return (
                      <Pressable
                        key={morador.id}
                        accessibilityRole="checkbox"
                        accessibilityLabel={nomeExibido}
                        accessibilityState={{ checked: selecionado }}
                        onPress={() => alternarResponsavel(morador.id)}
                        style={({ pressed }) => [
                          styles.resident,
                          {
                            backgroundColor: selecionado
                              ? theme.backgroundSelected
                              : theme.backgroundElement,
                            borderColor: selecionado
                              ? theme.text
                              : theme.backgroundElement,
                          },
                          pressed && styles.pressed,
                        ]}
                      >
                        <View
                          style={[
                            styles.avatar,
                            { backgroundColor: theme.background },
                          ]}
                        >
                          <ThemedText type="smallBold">
                            {morador.iniciais}
                          </ThemedText>
                        </View>
                        <ThemedText style={styles.residentName}>
                          {nomeExibido}
                        </ThemedText>
                        <ThemedText accessible={false} style={styles.check}>
                          {selecionado ? "☑" : "☐"}
                        </ThemedText>
                      </Pressable>
                    );
                  })}
                  <ThemedText type="small" accessibilityLiveRegion="polite">
                    {responsaveis.length} selecionado(s)
                  </ThemedText>
                  <ErroCampo mensagem={erros.responsaveis} />
                </View>

                <Pressable
                  accessibilityRole="button"
                  onPress={criarTarefa}
                  style={({ pressed }) => [
                    styles.button,
                    { backgroundColor: theme.text },
                    pressed && styles.pressed,
                  ]}
                >
                  <ThemedText style={{ color: theme.background }}>
                    Criar tarefa
                  </ThemedText>
                </Pressable>
              </>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: {
    flexGrow: 1,
    padding: Spacing.four,
    paddingTop: Platform.OS === "web" ? 120 : Spacing.four,
    paddingBottom: Spacing.five,
  },
  form: {
    width: "100%",
    maxWidth: 600,
    alignSelf: "center",
    gap: Spacing.four,
  },
  section: { gap: Spacing.two },
  title: { fontSize: 30, lineHeight: 38, fontWeight: "700" },
  input: {
    borderWidth: 1,
    borderRadius: 10,
    padding: Spacing.three,
    minHeight: 52,
    fontSize: 16,
  },
  description: { minHeight: 112 },
  weights: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  weight: {
    minWidth: 64,
    minHeight: 48,
    padding: Spacing.two,
    borderWidth: 1,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  resident: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.three,
    padding: Spacing.three,
    borderRadius: 10,
    borderWidth: 1,
    minHeight: 64,
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
  },
  residentName: { flex: 1 },
  check: { fontSize: 24, lineHeight: 32 },
  button: {
    minHeight: 52,
    padding: Spacing.three,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  pressed: { opacity: 0.7 },
  summary: { padding: Spacing.four, borderRadius: 12, gap: Spacing.three },
  summaryTitle: { fontSize: 22, lineHeight: 30, fontWeight: "700" },
});
