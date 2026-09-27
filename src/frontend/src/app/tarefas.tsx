import { useEffect, useState } from "react";
import { Platform, ScrollView, StyleSheet, Text, View } from "react-native";
import Animated, {
  FadeIn,
  FadeInDown,
  FadeOut,
  interpolateColor,
  LinearTransition,
  ReduceMotion,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";
import { SafeAreaView } from "react-native-safe-area-context";

import {
  DetalheTarefa,
  type ResultadoFinalizacao,
} from "@/components/detalhe-tarefa";
import { EditarTarefa } from "@/components/editar-tarefa";
import { MotionPressable } from "@/components/motion-pressable";
import { opcoesEstadoTarefa, rotulosEstado } from "@/constants/tarefa";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import {
  carregarContextoTarefas,
  carregarPlacar,
  carregarTarefas,
  carregarUsuarioAtual,
  editarTarefa,
  finalizarTarefa,
  type Casa,
  type Morador,
  type Placar,
  type Tarefa,
  type UsuarioAtual,
  type TarefaAtualizar,
} from "@/services/tarefas-api";
import {
  formatarPrazo,
  type FiltrosTarefa,
  type FiltroPrazo,
} from "@/utils/filtros-tarefa";

type FilterPillProps = {
  label: string;
  selected: boolean;
  onPress: () => void;
};

function FilterPill({ label, selected, onPress }: FilterPillProps) {
  const selection = useSharedValue(selected ? 1 : 0);

  useEffect(() => {
    selection.value = withTiming(selected ? 1 : 0, {
      duration: 160,
      reduceMotion: ReduceMotion.System,
    });
  }, [selected, selection]);

  const animatedStyle = useAnimatedStyle(() => ({
    backgroundColor: interpolateColor(
      selection.value,
      [0, 1],
      [Caldera.limestone, Caldera.ember],
    ),
  }));

  return (
    <MotionPressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={[styles.filterPill, animatedStyle]}
    >
      <Text style={styles.filterPillText}>{label}</Text>
    </MotionPressable>
  );
}

const opcoesPrazo: { valor: FiltroPrazo; rotulo: string }[] = [
  { valor: "todos", rotulo: "Qualquer prazo" },
  { valor: "hoje", rotulo: "Hoje" },
  { valor: "sete_dias", rotulo: "Próximos 7 dias" },
  { valor: "atrasadas", rotulo: "Prazo vencido" },
];

function iniciais(nome: string) {
  return nome
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0])
    .join("")
    .toUpperCase();
}

export default function TarefasScreen() {
  const [casa, setCasa] = useState<Casa>();
  const [moradores, setMoradores] = useState<Morador[]>([]);
  const [placar, setPlacar] = useState<Placar>();
  const [erroPlacar, setErroPlacar] = useState<string>();
  const [usuarioAtual, setUsuarioAtual] = useState<UsuarioAtual>();
  const [tarefas, setTarefas] = useState<Tarefa[]>();
  const [tarefasEmAberto, setTarefasEmAberto] = useState(0);
  const [carregandoContexto, setCarregandoContexto] = useState(true);
  const [carregandoTarefas, setCarregandoTarefas] = useState(true);
  const [erroContexto, setErroContexto] = useState<string>();
  const [erroTarefas, setErroTarefas] = useState<string>();
  const [tentativa, setTentativa] = useState(0);
  const [filtros, setFiltros] = useState<FiltrosTarefa>({
    estado: "todos",
    responsavel: "todos",
    prazo: "todos",
  });
  const [tarefaSelecionadaId, setTarefaSelecionadaId] = useState<string>();
  const [editando, setEditando] = useState(false);

  useEffect(() => {
    const controlador = new AbortController();
    // Reset síncrono do estado de loading/erro ao (re)disparar a busca de
    // contexto (mount ou retry); risco de cascata é aceitável aqui.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCarregandoContexto(true);
    setErroContexto(undefined);

    Promise.all([
      carregarContextoTarefas(controlador.signal),
      carregarUsuarioAtual(controlador.signal),
      carregarTarefas(
        { estado: "todos", responsavel: "todos", prazo: "todos" },
        controlador.signal,
      ),
    ])
      .then(([[casaAtual, moradoresAtuais], usuario, todasTarefas]) => {
        setCasa(casaAtual);
        setMoradores(moradoresAtuais);
        setUsuarioAtual(usuario);
        setTarefasEmAberto(
          todasTarefas.filter((tarefa) => tarefa.estado_atual !== "finalizado")
            .length,
        );
      })
      .catch((erro: unknown) => {
        if (!controlador.signal.aborted) {
          setErroContexto(
            erro instanceof Error
              ? erro.message
              : "Não foi possível carregar a casa.",
          );
        }
      })
      .finally(() => {
        if (!controlador.signal.aborted) setCarregandoContexto(false);
      });

    return () => controlador.abort();
  }, [tentativa]);

  useEffect(() => {
    const controlador = new AbortController();
    // Reset síncrono do estado de loading/erro ao (re)disparar a busca de
    // tarefas (filtro ou retry); risco de cascata é aceitável aqui.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCarregandoTarefas(true);
    setErroTarefas(undefined);

    carregarTarefas(filtros, controlador.signal)
      .then(setTarefas)
      .catch((erro: unknown) => {
        if (!controlador.signal.aborted) {
          setErroTarefas(
            erro instanceof Error
              ? erro.message
              : "Não foi possível carregar as tarefas.",
          );
        }
      })
      .finally(() => {
        if (!controlador.signal.aborted) setCarregandoTarefas(false);
      });

    return () => controlador.abort();
  }, [filtros, tentativa]);

  useEffect(() => {
    const controlador = new AbortController();
    carregarPlacar(controlador.signal)
      .then((dados) => {
        if (!controlador.signal.aborted) {
          setPlacar(dados);
          setErroPlacar(undefined);
        }
      })
      .catch((erro: unknown) => {
        if (!controlador.signal.aborted)
          setErroPlacar(
            erro instanceof Error
              ? erro.message
              : "Não foi possível carregar o placar.",
          );
      });
    return () => controlador.abort();
  }, [tentativa]);

  const tarefaSelecionada = tarefas?.find(
    (tarefa) => tarefa.id === tarefaSelecionadaId,
  );

  async function concluirTarefaSelecionada(): Promise<ResultadoFinalizacao> {
    if (!tarefaSelecionada) {
      throw new Error("Tarefa não encontrada.");
    }

    if (!usuarioAtual) {
      throw new Error("Usuário atual não encontrado.");
    }

    const tarefaFinalizada = await finalizarTarefa(tarefaSelecionada.id);
    const pontuacao = tarefaFinalizada.resultado_pontuacao;
    if (!pontuacao)
      throw new Error("O servidor não retornou a pontuação da tarefa.");

    setMoradores((atuais) =>
      atuais.map((morador) =>
        morador.id === usuarioAtual.id
          ? { ...morador, score: pontuacao.saldo_atual }
          : morador,
      ),
    );
    setTarefas((atuais) =>
      atuais?.map((tarefa) =>
        tarefa.id === tarefaFinalizada.id ? tarefaFinalizada : tarefa,
      ),
    );
    setTarefasEmAberto((quantidade) => Math.max(0, quantidade - 1));

    return {
      pontosPossiveis: pontuacao.pontos_possiveis,
      pontosObtidos: pontuacao.pontos_ganhos,
      saldoAtual: pontuacao.saldo_atual,
    };
  }

  function continuarAposFinalizacao() {
    setTarefaSelecionadaId(undefined);
    setTentativa((atual) => atual + 1);
  }

  async function salvarEdicao(dados: TarefaAtualizar) {
    if (!tarefaSelecionada) throw new Error("Tarefa não encontrada.");
    const tarefaAtualizada = await editarTarefa(tarefaSelecionada.id, dados);
    setTarefas((atuais) =>
      atuais?.map((tarefa) =>
        tarefa.id === tarefaAtualizada.id ? tarefaAtualizada : tarefa,
      ),
    );
    setEditando(false);
  }

  if (
    carregandoContexto ||
    !casa ||
    !usuarioAtual ||
    (carregandoTarefas && !tarefas)
  ) {
    const erro = erroContexto || erroTarefas;
    return (
      <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
        <View style={[styles.page, styles.feedback]}>
          <Text style={styles.emptyTitle}>
            {erro ? "NÃO FOI POSSÍVEL CARREGAR" : "CARREGANDO TAREFAS"}
          </Text>
          <Text style={styles.emptyText}>
            {erro || "Buscando as tarefas da sua casa."}
          </Text>
          {erro && (
            <MotionPressable
              accessibilityRole="button"
              onPress={() => setTentativa((atual) => atual + 1)}
              style={styles.retryButton}
            >
              <Text style={styles.retryButtonText}>Tentar novamente</Text>
            </MotionPressable>
          )}
        </View>
      </SafeAreaView>
    );
  }

  const tarefasFiltradas = tarefas ?? [];

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
      <ScrollView contentContainerStyle={styles.page}>
        {tarefaSelecionada && editando ? (
          <EditarTarefa
            tarefa={tarefaSelecionada}
            moradores={moradores}
            onCancelar={() => setEditando(false)}
            onSalvar={salvarEdicao}
          />
        ) : tarefaSelecionada ? (
          <DetalheTarefa
            tarefa={tarefaSelecionada}
            moradores={moradores}
            usuarioAtualId={usuarioAtual.id}
            onVoltar={() => {
              setEditando(false);
              setTarefaSelecionadaId(undefined);
            }}
            onEditar={
              casa.fk_usuario_id === usuarioAtual.id
                ? () => setEditando(true)
                : undefined
            }
            onFinalizar={concluirTarefaSelecionada}
            onContinuar={continuarAposFinalizacao}
          />
        ) : (
          <Animated.View
            entering={FadeIn.duration(220).reduceMotion(ReduceMotion.System)}
            style={styles.content}
          >
            <View style={styles.hero}>
              <View style={styles.heroCopy}>
                <Text style={styles.houseName}>{casa.nome}</Text>
                <Text accessibilityRole="header" style={styles.title}>
                  TAREFAS DA CASA
                </Text>
                <Text style={styles.subtitle}>
                  Organize o combinado, veja quem ficou responsável e acompanhe
                  cada prazo.
                </Text>
              </View>
              <View style={styles.statCard}>
                <Text style={styles.statLabel}>EM ABERTO</Text>
                <Text style={styles.statValue}>{tarefasEmAberto}</Text>
                <Text style={styles.statCaption}>tarefas pedem atenção</Text>
              </View>
            </View>

            <View style={styles.filtersCard}>
              <Text accessibilityRole="header" style={styles.sectionTitle}>
                PLACAR DA CASA
              </Text>
              {placar ? (
                <>
                  <Text style={styles.filterLabel}>
                    Períodos no fuso {placar.fuso_horario}
                  </Text>
                  <View style={styles.placarGrid}>
                    {placar.moradores.map((morador) => (
                      <View
                        key={morador.usuario_id}
                        style={styles.placarMorador}
                      >
                        <Text style={styles.placarNome}>{morador.nome}</Text>
                        <Text style={styles.metaValue}>
                          Semana: {morador.semanal}
                        </Text>
                        <Text style={styles.metaValue}>
                          Mês: {morador.mensal}
                        </Text>
                        <Text style={styles.metaValue}>
                          Ano: {morador.anual}
                        </Text>
                        <Text style={styles.metaValue}>
                          Total: {morador.acumulado}
                        </Text>
                      </View>
                    ))}
                  </View>
                </>
              ) : (
                <Text accessibilityLiveRegion="polite" style={styles.emptyText}>
                  {erroPlacar ?? "Carregando placar..."}
                </Text>
              )}
            </View>

            <View style={styles.filtersCard}>
              <View style={styles.filterGroup}>
                <Text style={styles.filterLabel}>STATUS</Text>
                <View style={styles.filterOptions}>
                  <FilterPill
                    label="Todos"
                    selected={filtros.estado === "todos"}
                    onPress={() =>
                      setFiltros((atuais) => ({ ...atuais, estado: "todos" }))
                    }
                  />
                  {opcoesEstadoTarefa.map((opcao) => (
                    <FilterPill
                      key={opcao.valor}
                      label={opcao.rotulo}
                      selected={filtros.estado === opcao.valor}
                      onPress={() =>
                        setFiltros((atuais) => ({
                          ...atuais,
                          estado: opcao.valor,
                        }))
                      }
                    />
                  ))}
                </View>
              </View>

              <View style={styles.filterGroup}>
                <Text style={styles.filterLabel}>RESPONSÁVEL</Text>
                <View style={styles.filterOptions}>
                  <FilterPill
                    label="Todos"
                    selected={filtros.responsavel === "todos"}
                    onPress={() =>
                      setFiltros((atuais) => ({
                        ...atuais,
                        responsavel: "todos",
                      }))
                    }
                  />
                  {moradores.map((morador) => (
                    <FilterPill
                      key={morador.id}
                      label={morador.nome}
                      selected={filtros.responsavel === morador.id}
                      onPress={() =>
                        setFiltros((atuais) => ({
                          ...atuais,
                          responsavel: morador.id,
                        }))
                      }
                    />
                  ))}
                </View>
              </View>

              <View style={styles.filterGroup}>
                <Text style={styles.filterLabel}>PRAZO</Text>
                <View style={styles.filterOptions}>
                  {opcoesPrazo.map((opcao) => (
                    <FilterPill
                      key={opcao.valor}
                      label={opcao.rotulo}
                      selected={filtros.prazo === opcao.valor}
                      onPress={() =>
                        setFiltros((atuais) => ({
                          ...atuais,
                          prazo: opcao.valor,
                        }))
                      }
                    />
                  ))}
                </View>
              </View>
            </View>

            <View style={styles.listHeading}>
              <Text style={styles.sectionTitle}>TAREFAS</Text>
              <Animated.Text
                key={tarefasFiltradas.length}
                accessibilityLiveRegion="polite"
                entering={FadeIn.duration(160).reduceMotion(
                  ReduceMotion.System,
                )}
                style={styles.resultCount}
              >
                {tarefasFiltradas.length} resultado(s)
              </Animated.Text>
            </View>

            {erroTarefas && (
              <View style={styles.errorNotice}>
                <Text style={styles.emptyText}>{erroTarefas}</Text>
              </View>
            )}

            {tarefasFiltradas.length ? (
              <View style={styles.taskGrid}>
                {tarefasFiltradas.map((tarefa, index) => {
                  const responsaveis = moradores.filter((morador) =>
                    tarefa.usuarios_atribuidos.includes(morador.id),
                  );
                  const finalizada = tarefa.estado_atual === "finalizado";

                  return (
                    <Animated.View
                      key={tarefa.id}
                      entering={FadeInDown.delay(Math.min(index * 40, 160))
                        .duration(260)
                        .reduceMotion(ReduceMotion.System)}
                      exiting={FadeOut.duration(140).reduceMotion(
                        ReduceMotion.System,
                      )}
                      layout={LinearTransition.duration(220).reduceMotion(
                        ReduceMotion.System,
                      )}
                      style={styles.taskCardSlot}
                    >
                      <MotionPressable
                        accessibilityRole="button"
                        accessibilityLabel={`Ver detalhes de ${tarefa.nome}`}
                        onPress={() => setTarefaSelecionadaId(tarefa.id)}
                        style={styles.taskCard}
                      >
                        <View style={styles.taskTopRow}>
                          <View
                            style={[
                              styles.statusBadge,
                              finalizada && styles.statusBadgeFinished,
                            ]}
                          >
                            <Text
                              style={[
                                styles.statusText,
                                finalizada && styles.statusTextFinished,
                              ]}
                            >
                              {rotulosEstado[tarefa.estado_atual]}
                            </Text>
                          </View>
                          <Text style={styles.weight}>PESO {tarefa.peso}</Text>
                        </View>

                        <Text style={styles.taskTitle}>
                          {tarefa.nome.toUpperCase()}
                        </Text>
                        <Text numberOfLines={2} style={styles.taskDescription}>
                          {tarefa.descricao || "Sem descrição."}
                        </Text>

                        <View style={styles.taskMeta}>
                          <View>
                            <Text style={styles.metaLabel}>PRAZO</Text>
                            <Text style={styles.metaValue}>
                              {formatarPrazo(tarefa.data_fim, tarefa.data_fixa)}
                            </Text>
                          </View>
                          <View style={styles.avatars}>
                            {responsaveis.map((morador) => (
                              <View key={morador.id} style={styles.avatar}>
                                <Text style={styles.avatarText}>
                                  {iniciais(morador.nome)}
                                </Text>
                              </View>
                            ))}
                          </View>
                        </View>

                        <Text style={styles.detailsLink}>Ver detalhes →</Text>
                      </MotionPressable>
                    </Animated.View>
                  );
                })}
              </View>
            ) : (
              <Animated.View
                entering={FadeInDown.duration(220).reduceMotion(
                  ReduceMotion.System,
                )}
                exiting={FadeOut.duration(140).reduceMotion(
                  ReduceMotion.System,
                )}
                style={styles.emptyCard}
              >
                <Text style={styles.emptyTitle}>NENHUMA TAREFA POR AQUI</Text>
                <Text style={styles.emptyText}>
                  Ajuste os filtros para ver outras tarefas da casa.
                </Text>
              </Animated.View>
            )}
          </Animated.View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Caldera.pumice },
  page: {
    flexGrow: 1,
    paddingHorizontal: Spacing.four,
    paddingTop: Platform.OS === "web" ? 112 : Spacing.four,
    paddingBottom: Spacing.six,
  },
  content: {
    width: "100%",
    maxWidth: 1280,
    alignSelf: "center",
    gap: 40,
  },
  hero: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "stretch",
    gap: Spacing.four,
  },
  heroCopy: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 320,
    justifyContent: "center",
    gap: Spacing.three,
  },
  houseName: { color: Caldera.ember, fontSize: 14, fontWeight: "500" },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 64,
    lineHeight: 62,
    letterSpacing: 1.28,
  },
  subtitle: {
    color: Caldera.obsidian,
    fontSize: 18,
    lineHeight: 28,
    fontWeight: "500",
    maxWidth: 620,
  },
  statCard: {
    flexGrow: 1,
    flexBasis: 240,
    maxWidth: 360,
    minHeight: 210,
    borderRadius: 40,
    backgroundColor: Caldera.ember,
    padding: Spacing.five,
    justifyContent: "space-between",
  },
  statLabel: { color: Caldera.chalk, fontSize: 14, fontWeight: "500" },
  statValue: {
    color: Caldera.chalk,
    fontFamily: CompactFont,
    fontSize: 80,
    lineHeight: 82,
  },
  statCaption: { color: Caldera.chalk, fontSize: 16, fontWeight: "500" },
  filtersCard: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.four,
  },
  placarGrid: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.three },
  placarMorador: {
    flexGrow: 1,
    minWidth: 180,
    gap: 6,
    padding: Spacing.three,
    backgroundColor: Caldera.pumice,
    borderRadius: 20,
  },
  placarNome: { color: Caldera.obsidian, fontSize: 18, fontWeight: "600" },
  filterGroup: { gap: 12 },
  filterLabel: { color: Caldera.obsidian, fontSize: 12, fontWeight: "500" },
  filterOptions: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  filterPill: {
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.three,
    paddingVertical: 10,
  },
  filterPillText: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  listHeading: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    gap: Spacing.three,
  },
  sectionTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 48,
    lineHeight: 48,
    letterSpacing: 0.96,
  },
  resultCount: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  taskGrid: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.four },
  taskCardSlot: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 320,
  },
  taskCard: {
    flex: 1,
    minHeight: 330,
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.three,
  },
  taskTopRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: Spacing.two,
  },
  statusBadge: {
    backgroundColor: Caldera.sulfur,
    borderRadius: 800,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  statusBadgeFinished: { backgroundColor: Caldera.obsidian },
  statusText: { color: Caldera.obsidian, fontSize: 12, fontWeight: "500" },
  statusTextFinished: { color: Caldera.chalk },
  weight: { color: Caldera.obsidian, fontSize: 12, fontWeight: "500" },
  taskTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 32,
    lineHeight: 34,
    letterSpacing: 0.64,
  },
  taskDescription: {
    color: Caldera.obsidian,
    fontSize: 16,
    lineHeight: 24,
    fontWeight: "500",
  },
  taskMeta: {
    marginTop: "auto",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    gap: Spacing.three,
  },
  metaLabel: {
    color: Caldera.obsidian,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: "500",
  },
  metaValue: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  avatars: { flexDirection: "row" },
  avatar: {
    width: 36,
    height: 36,
    marginLeft: -6,
    borderRadius: 18,
    borderWidth: 2,
    borderColor: Caldera.limestone,
    backgroundColor: Caldera.ember,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { color: Caldera.obsidian, fontSize: 11, fontWeight: "500" },
  detailsLink: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  emptyCard: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: 40,
    gap: Spacing.two,
  },
  emptyTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 32,
    lineHeight: 36,
  },
  emptyText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  feedback: {
    alignItems: "center",
    justifyContent: "center",
    gap: Spacing.three,
  },
  errorNotice: {
    backgroundColor: Caldera.limestone,
    borderRadius: 20,
    padding: Spacing.three,
  },
  retryButton: {
    backgroundColor: Caldera.ember,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.two,
  },
  retryButtonText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
});
