import { useRef, useState } from "react";
import {
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { MotionPressable } from "@/components/motion-pressable";
import {
  pesosTarefa,
  prazosTarefa,
  type PesoTarefa,
  type PrazoDias,
  type TarefaDemonstracao,
} from "@/constants/tarefa";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import {
  casaDemonstracao,
  moradoresDemonstracao,
  usuarioDemonstracaoId,
} from "@/data/tarefa-demonstracao";

type Erros = {
  nome?: string;
  peso?: string;
  prazo?: string;
  responsavel?: string;
};

function ErroCampo({ mensagem }: { mensagem?: string }) {
  if (!mensagem) return null;
  return (
    <Text style={styles.help} accessibilityLiveRegion="polite">
      Atenção: {mensagem}
    </Text>
  );
}

function IndicadorSelecao({ selecionado }: { selecionado: boolean }) {
  return (
    <View accessible={false} style={styles.radio}>
      {selecionado && <View style={styles.radioDot} />}
    </View>
  );
}

export default function NovaTarefaScreen() {
  const { width } = useWindowDimensions();
  const scrollRef = useRef<ScrollView>(null);
  const descricaoRef = useRef<TextInput>(null);
  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const [peso, setPeso] = useState<PesoTarefa | null>(null);
  const [dias, setDias] = useState<PrazoDias | null>(null);
  const [responsavel, setResponsavel] = useState<string | null>(null);
  const [erros, setErros] = useState<Erros>({});
  const [tarefa, setTarefa] = useState<TarefaDemonstracao | null>(null);
  const cardStyle = [styles.card, width < 600 && styles.compactCard];

  function criarTarefa() {
    const novosErros: Erros = {
      nome: nome.trim() ? undefined : "Informe o nome da tarefa.",
      peso: peso === null ? "Selecione um peso de 1 a 3." : undefined,
      prazo: dias === null ? "Selecione um prazo de 1 a 5 dias." : undefined,
      responsavel: responsavel ? undefined : "Selecione um responsável.",
    };
    setErros(novosErros);
    Keyboard.dismiss();

    if (
      Object.values(novosErros).some(Boolean) ||
      peso === null ||
      dias === null ||
      responsavel === null
    ) {
      scrollRef.current?.scrollTo({ y: 0, animated: false });
      return;
    }

    setTarefa({
      nome: nome.trim(),
      descricao: descricao.trim(),
      peso,
      prazo_dias: dias,
      usuarios_atribuidos: [responsavel],
    });
    scrollRef.current?.scrollTo({ y: 0, animated: false });
  }

  function criarOutraTarefa() {
    setNome("");
    setDescricao("");
    setPeso(null);
    setDias(null);
    setResponsavel(null);
    setErros({});
    setTarefa(null);
    scrollRef.current?.scrollTo({ y: 0, animated: false });
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
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
              <Text style={styles.help}>{casaDemonstracao.nome}</Text>
              <Text accessibilityRole="header" style={styles.title}>
                {tarefa ? "TUDO PRONTO!" : "NOVA TAREFA"}
              </Text>
              <Text style={styles.body}>
                {tarefa
                  ? "Confira os detalhes abaixo."
                  : "Organize o que precisa ser feito na casa."}
              </Text>
              <View style={styles.badge}>
                <Text style={styles.help}>Demonstração · dados fictícios</Text>
              </View>
            </View>

            {tarefa ? (
              <>
                <View style={cardStyle}>
                  <Text
                    accessibilityRole="header"
                    accessibilityLiveRegion="polite"
                    style={styles.sectionTitle}
                  >
                    Tarefa criada nesta demonstração
                  </Text>
                  <View style={styles.section}>
                    <Text style={styles.help}>Nome</Text>
                    <Text style={styles.body}>{tarefa.nome}</Text>
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.help}>Descrição</Text>
                    <Text style={styles.body}>
                      {tarefa.descricao || "Sem descrição."}
                    </Text>
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.help}>Peso</Text>
                    <Text style={styles.body}>{tarefa.peso}</Text>
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.help}>Prazo para terminar</Text>
                    <Text style={styles.body}>
                      {tarefa.prazo_dias}{" "}
                      {tarefa.prazo_dias === 1 ? "dia" : "dias"}
                    </Text>
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.help}>Responsável</Text>
                    <Text style={styles.body}>
                      {
                        moradoresDemonstracao.find(
                          (morador) =>
                            morador.id === tarefa.usuarios_atribuidos[0],
                        )?.nome
                      }
                    </Text>
                  </View>
                </View>
                <MotionPressable
                  accessibilityRole="button"
                  onPress={criarOutraTarefa}
                  style={styles.button}
                >
                  <Text style={styles.body}>Criar outra tarefa</Text>
                </MotionPressable>
              </>
            ) : (
              <>
                <View style={cardStyle}>
                  <View style={styles.section}>
                    <Text
                      accessibilityRole="header"
                      style={styles.sectionTitle}
                    >
                      OS DETALHES
                    </Text>
                    <Text style={styles.help}>
                      Campos com * são obrigatórios.
                    </Text>
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.body}>Nome *</Text>
                    <TextInput
                      accessibilityLabel="Nome da tarefa, obrigatório"
                      accessibilityHint={erros.nome}
                      style={styles.input}
                      placeholder="Ex.: Limpar a cozinha"
                      placeholderTextColor={Caldera.obsidian}
                      selectionColor={Caldera.ember}
                      returnKeyType="next"
                      onSubmitEditing={() => descricaoRef.current?.focus()}
                      value={nome}
                      onChangeText={(valor) => {
                        setNome(valor);
                        setErros((atuais) => ({ ...atuais, nome: undefined }));
                      }}
                    />
                    <ErroCampo mensagem={erros.nome} />
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.body}>Descrição (opcional)</Text>
                    <TextInput
                      ref={descricaoRef}
                      accessibilityLabel="Descrição, opcional"
                      style={[styles.input, styles.description]}
                      placeholder="O que precisa ser feito?"
                      placeholderTextColor={Caldera.obsidian}
                      selectionColor={Caldera.ember}
                      multiline
                      textAlignVertical="top"
                      value={descricao}
                      onChangeText={setDescricao}
                    />
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.body}>Peso *</Text>
                    <Text style={styles.help}>
                      Selecione a dificuldade: 1 é a menor e 3 é a maior.
                    </Text>
                    <View
                      style={styles.options}
                      accessibilityRole="radiogroup"
                      accessibilityLabel="Peso da tarefa"
                    >
                      {pesosTarefa.map((opcao) => (
                        <MotionPressable
                          key={opcao}
                          accessibilityRole="radio"
                          accessibilityLabel={`Peso ${opcao}`}
                          accessibilityState={{ checked: peso === opcao }}
                          aria-checked={peso === opcao}
                          onPress={() => {
                            setPeso(opcao);
                            setErros((atuais) => ({
                              ...atuais,
                              peso: undefined,
                            }));
                          }}
                          style={[
                            styles.option,
                            peso === opcao && styles.selected,
                          ]}
                        >
                          <IndicadorSelecao selecionado={peso === opcao} />
                          <Text style={styles.body}>{opcao}</Text>
                        </MotionPressable>
                      ))}
                    </View>
                    <ErroCampo mensagem={erros.peso} />
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.body}>Dias para terminar *</Text>
                    <Text style={styles.help}>Escolha de 1 a 5 dias.</Text>
                    <View
                      style={styles.options}
                      accessibilityRole="radiogroup"
                      accessibilityLabel="Dias para terminar"
                    >
                      {prazosTarefa.map((opcao) => (
                        <MotionPressable
                          key={opcao}
                          accessibilityRole="radio"
                          accessibilityLabel={`${opcao} ${opcao === 1 ? "dia" : "dias"}`}
                          accessibilityState={{ checked: dias === opcao }}
                          aria-checked={dias === opcao}
                          onPress={() => {
                            setDias(opcao);
                            setErros((atuais) => ({
                              ...atuais,
                              prazo: undefined,
                            }));
                          }}
                          style={[
                            styles.option,
                            dias === opcao && styles.selected,
                          ]}
                        >
                          <IndicadorSelecao selecionado={dias === opcao} />
                          <Text style={styles.body}>{opcao}</Text>
                        </MotionPressable>
                      ))}
                    </View>
                    <ErroCampo mensagem={erros.prazo} />
                  </View>
                </View>

                <View style={cardStyle}>
                  <View style={styles.section}>
                    <Text
                      accessibilityRole="header"
                      style={styles.sectionTitle}
                    >
                      QUEM VAI FAZER?
                    </Text>
                    <Text style={styles.body}>Responsável *</Text>
                    <Text style={styles.help}>
                      Escolha apenas um morador. Ao escolher outro, a seleção
                      anterior é substituída.
                    </Text>
                  </View>
                  <View
                    style={styles.section}
                    accessibilityRole="radiogroup"
                    accessibilityLabel="Responsável pela tarefa"
                  >
                    {moradoresDemonstracao.map((morador) => {
                      const selecionado = responsavel === morador.id;
                      const nomeExibido = `${morador.nome}${morador.id === usuarioDemonstracaoId ? " (você)" : ""}`;
                      return (
                        <MotionPressable
                          key={morador.id}
                          accessibilityRole="radio"
                          accessibilityLabel={nomeExibido}
                          accessibilityState={{ checked: selecionado }}
                          aria-checked={selecionado}
                          onPress={() => {
                            setResponsavel(morador.id);
                            setErros((atuais) => ({
                              ...atuais,
                              responsavel: undefined,
                            }));
                          }}
                          style={[
                            styles.resident,
                            selecionado && styles.selected,
                          ]}
                        >
                          <View style={styles.avatar}>
                            <Text style={styles.help}>{morador.iniciais}</Text>
                          </View>
                          <Text style={[styles.body, styles.residentName]}>
                            {nomeExibido}
                          </Text>
                          <IndicadorSelecao selecionado={selecionado} />
                        </MotionPressable>
                      );
                    })}
                  </View>
                  <ErroCampo mensagem={erros.responsavel} />
                </View>
                <MotionPressable
                  accessibilityRole="button"
                  onPress={criarTarefa}
                  style={styles.button}
                >
                  <Text style={styles.body}>Criar tarefa</Text>
                </MotionPressable>
              </>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Caldera.pumice },
  container: { flex: 1 },
  content: {
    flexGrow: 1,
    paddingHorizontal: Spacing.three,
    paddingTop: Platform.OS === "web" ? 120 : Spacing.four,
    paddingBottom: Spacing.six,
  },
  form: {
    width: "100%",
    maxWidth: 760,
    alignSelf: "center",
    gap: Spacing.four,
  },
  section: { gap: Spacing.two },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 48,
    lineHeight: 56,
    letterSpacing: 0.96,
  },
  sectionTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 26,
    lineHeight: 32,
    letterSpacing: 0.52,
  },
  body: {
    color: Caldera.obsidian,
    fontSize: 16,
    lineHeight: 24,
    fontWeight: "500",
  },
  help: {
    color: Caldera.obsidian,
    fontSize: 14,
    lineHeight: 20,
    fontWeight: "500",
  },
  badge: {
    alignSelf: "flex-start",
    backgroundColor: Caldera.sulfur,
    borderRadius: 800,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  card: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: 40,
    gap: Spacing.four,
  },
  compactCard: { padding: Spacing.four },
  input: {
    color: Caldera.obsidian,
    backgroundColor: Caldera.pumice,
    borderRadius: 100,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.three,
    minHeight: 56,
    fontSize: 16,
    fontWeight: "500",
  },
  description: { minHeight: 128, borderRadius: 40 },
  options: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  option: {
    flexGrow: 1,
    minWidth: 52,
    minHeight: 48,
    borderRadius: 800,
    backgroundColor: Caldera.pumice,
    padding: Spacing.two,
    flexDirection: "row",
    gap: Spacing.two,
    justifyContent: "center",
    alignItems: "center",
  },
  selected: { backgroundColor: Caldera.ember },
  radio: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    alignItems: "center",
    justifyContent: "center",
  },
  radioDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Caldera.obsidian,
  },
  resident: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.two,
    padding: Spacing.three,
    borderRadius: 40,
    backgroundColor: Caldera.pumice,
    minHeight: 72,
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Caldera.limestone,
    alignItems: "center",
    justifyContent: "center",
  },
  residentName: { flex: 1 },
  button: {
    minHeight: 56,
    paddingVertical: 12,
    paddingHorizontal: Spacing.four,
    borderRadius: 800,
    backgroundColor: Caldera.ember,
    alignItems: "center",
    justifyContent: "center",
  },
});
