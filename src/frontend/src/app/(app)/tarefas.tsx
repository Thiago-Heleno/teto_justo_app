import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
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
import { useStore } from "zustand";

import { CalendarioTarefas } from "@/components/calendario-tarefas";
import {
  DetalheTarefa,
  type ResultadoFinalizacao,
} from "@/components/detalhe-tarefa";
import { EditarTarefa } from "@/components/editar-tarefa";
import { MotionPressable } from "@/components/motion-pressable";
import { opcoesEstadoTarefa, rotulosEstado } from "@/constants/tarefa";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import { sessao } from "@/services/sessao-store";
import {
  carregarContextoTarefas,
  carregarTarefas,
  carregarUsuarioAtual,
  editarTarefa,
  finalizarTarefa,
  reabrirTarefa,
  type Casa,
  type Morador,
  type Tarefa,
  type UsuarioAtual,
  type TarefaAtualizar,
} from "@/services/tarefas-api";
import { dataNoFuso } from "@/utils/calendario-tarefas";
import {
  formatarPrazo,
  ordenarTarefas,
  type FiltrosTarefa,
  type FiltroPrazo,
} from "@/utils/filtros-tarefa";
import { podeReabrirTarefa } from "@/utils/reabertura";

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
  { valor: "antigas", rotulo: "Antigas" },
  { valor: "hoje", rotulo: "Hoje" },
  { valor: "sete_dias", rotulo: "Próximos 7 dias" },
  { valor: "todos", rotulo: "Todas" },
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
  const { abrir } = useLocalSearchParams<{ abrir?: string }>();
  const { width } = useWindowDimensions();
  const casaId = useStore(sessao, (estado) => estado.casaAtiva?.id);
  const token = useStore(sessao, (estado) => estado.token);
  const telaPequena = width < 600;
  const estiloPagina = [styles.page, telaPequena && styles.pageSmall];
  const scrollRef = useRef<ScrollView>(null);
  const posicaoLista = useRef(0);
  const restaurarPosicaoLista = useRef(false);
  const chaveSessao = `${casaId}:${token}`;
  const [origemContexto, setOrigemContexto] = useState<string>();
  const [casa, setCasa] = useState<Casa>();
  const [moradores, setMoradores] = useState<Morador[]>([]);
  const [usuarioAtual, setUsuarioAtual] = useState<UsuarioAtual>();
  const [todasTarefas, setTodasTarefas] = useState<Tarefa[]>();
  const [resultadoFiltrado, setResultadoFiltrado] = useState<{
    chave: string;
    tarefas: Tarefa[];
  }>();
  const [carregandoContexto, setCarregandoContexto] = useState(true);
  const [carregandoTarefas, setCarregandoTarefas] = useState(false);
  const [erroContexto, setErroContexto] = useState<string>();
  const [erroTarefas, setErroTarefas] = useState<{
    chave: string;
    mensagem: string;
  }>();
  const [tentativa, setTentativa] = useState(0);
  const [filtros, setFiltros] = useState<FiltrosTarefa>({
    estado: "todos",
    responsavel: "todos",
    prazo: "sete_dias",
  });
  const [tarefaSelecionadaId, setTarefaSelecionadaId] = useState<string>();
  const [selecaoCalendario, setSelecaoCalendario] = useState<{
    chave: string;
    dia: string;
  }>();
  const [editando, setEditando] = useState(false);
  const [filtrosAbertos, setFiltrosAbertos] = useState(false);
  const { estado, responsavel, prazo } = filtros;
  const quantidadeFiltros = [estado, responsavel, prazo].filter(
    (valor) => valor !== "todos",
  ).length;
  const filtrosAtivos = quantidadeFiltros > 0;
  const chaveFiltro = `${chaveSessao}:${estado}:${responsavel}:${prazo}`;
  const [listaVisivel, setListaVisivel] = useState({
    chave: chaveFiltro,
    limite: 12,
  });
  if (listaVisivel.chave !== chaveFiltro) {
    setListaVisivel({ chave: chaveFiltro, limite: 12 });
  }
  const contextoAtual = origemContexto === chaveSessao;
  const tarefas = !contextoAtual
    ? undefined
    : filtrosAtivos
      ? resultadoFiltrado?.chave === chaveFiltro
        ? resultadoFiltrado.tarefas
        : undefined
      : todasTarefas;
  const erroFiltroAtual =
    erroTarefas?.chave === chaveFiltro ? erroTarefas.mensagem : undefined;
  const tarefasEmAberto =
    (contextoAtual ? todasTarefas : undefined)?.filter(
      (tarefa) =>
        tarefa.estado_atual === "pendente" ||
        tarefa.estado_atual === "atrasada",
    ).length ?? 0;
  const atualizando =
    carregandoContexto || (filtrosAtivos && carregandoTarefas);

  useFocusEffect(
    useCallback(() => {
      scrollRef.current?.scrollTo({ y: 0, animated: false });
    }, []),
  );

  useEffect(() => {
    if (!tarefaSelecionadaId) return;
    restaurarPosicaoLista.current = true;
    scrollRef.current?.scrollTo({ y: 0, animated: false });
  }, [tarefaSelecionadaId, editando]);

  useEffect(() => {
    if (!contextoAtual || !todasTarefas || typeof abrir !== "string") return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTarefaSelecionadaId(
      todasTarefas.some((tarefa) => tarefa.id === abrir) ? abrir : undefined,
    );
    setEditando(false);
    router.setParams({ abrir: undefined });
  }, [abrir, contextoAtual, todasTarefas]);

  useFocusEffect(
    useCallback(() => {
      if (!casaId || !token) return;
      const controlador = new AbortController();
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
          if (controlador.signal.aborted) return;
          setCasa(casaAtual);
          setMoradores(moradoresAtuais);
          setUsuarioAtual(usuario);
          setTodasTarefas(todasTarefas);
          setOrigemContexto(chaveSessao);
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
      // A tentativa também refaz a consulta sem trocar de aba.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [casaId, token, chaveSessao, tentativa]),
  );

  useFocusEffect(
    useCallback(() => {
      if (!casaId || !token || !filtrosAtivos) return;
      const controlador = new AbortController();
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCarregandoTarefas(true);
      setErroTarefas(undefined);

      carregarTarefas({ estado, responsavel, prazo }, controlador.signal)
        .then((dados) => {
          if (!controlador.signal.aborted)
            setResultadoFiltrado({ chave: chaveFiltro, tarefas: dados });
        })
        .catch((erro: unknown) => {
          if (!controlador.signal.aborted) {
            setErroTarefas({
              chave: chaveFiltro,
              mensagem:
                erro instanceof Error
                  ? erro.message
                  : "Não foi possível carregar as tarefas.",
            });
          }
        })
        .finally(() => {
          if (!controlador.signal.aborted) setCarregandoTarefas(false);
        });

      return () => controlador.abort();
      // A tentativa também refaz a consulta sem trocar de aba.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [
      casaId,
      token,
      estado,
      responsavel,
      prazo,
      filtrosAtivos,
      chaveFiltro,
      tentativa,
    ]),
  );

  useEffect(() => {
    if (!contextoAtual || !todasTarefas || !tarefaSelecionadaId) return;
    if (
      tarefas?.some((tarefa) => tarefa.id === tarefaSelecionadaId) ||
      todasTarefas.some((tarefa) => tarefa.id === tarefaSelecionadaId)
    )
      return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTarefaSelecionadaId(undefined);
    setEditando(false);
  }, [contextoAtual, tarefas, todasTarefas, tarefaSelecionadaId]);

  function atualizarTarefaLocal(atualizada: Tarefa) {
    setTodasTarefas((atuais) =>
      atuais?.map((tarefa) =>
        tarefa.id === atualizada.id ? atualizada : tarefa,
      ),
    );
    setResultadoFiltrado(
      (atual) =>
        atual && {
          ...atual,
          tarefas: atual.tarefas.map((tarefa) =>
            tarefa.id === atualizada.id ? atualizada : tarefa,
          ),
        },
    );
  }

  const tarefaSelecionada = contextoAtual
    ? (tarefas?.find((tarefa) => tarefa.id === tarefaSelecionadaId) ??
      todasTarefas?.find((tarefa) => tarefa.id === tarefaSelecionadaId))
    : undefined;

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
    atualizarTarefaLocal(tarefaFinalizada);

    return {
      pontosPossiveis: pontuacao.pontos_possiveis,
      pontosObtidos: pontuacao.pontos_ganhos,
      saldoAtual: pontuacao.saldo_atual,
    };
  }

  async function reabrirTarefaSelecionada() {
    if (!tarefaSelecionada) throw new Error("Tarefa não encontrada.");
    const tarefaReaberta = await reabrirTarefa(tarefaSelecionada.id);
    atualizarTarefaLocal(tarefaReaberta);
    // Recarrega saldo e contagem de tarefas em aberto.
    setTentativa((atual) => atual + 1);
  }

  function continuarAposFinalizacao() {
    setTarefaSelecionadaId(undefined);
    setTentativa((atual) => atual + 1);
  }

  async function salvarEdicao(dados: TarefaAtualizar) {
    if (!tarefaSelecionada) throw new Error("Tarefa não encontrada.");
    const tarefaAtualizada = await editarTarefa(tarefaSelecionada.id, dados);
    atualizarTarefaLocal(tarefaAtualizada);
    setEditando(false);
    setTentativa((atual) => atual + 1);
  }

  if (!contextoAtual || !casa || !usuarioAtual || !todasTarefas) {
    const erro = erroContexto;
    return (
      <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
        <View style={[estiloPagina, styles.feedback]}>
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

  const chaveCalendario = `${casa.id}-${casa.timezone}-${usuarioAtual.id}`;
  const tarefasFiltradas = ordenarTarefas(tarefas ?? [], prazo);
  const tarefasVisiveis = tarefasFiltradas.slice(0, listaVisivel.limite);

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
      <ScrollView
        ref={scrollRef}
        contentContainerStyle={estiloPagina}
        scrollEventThrottle={16}
        onScroll={({ nativeEvent }) => {
          if (!tarefaSelecionadaId && !restaurarPosicaoLista.current) {
            posicaoLista.current = nativeEvent.contentOffset.y;
          }
        }}
        onContentSizeChange={() => {
          if (!tarefaSelecionadaId && restaurarPosicaoLista.current) {
            scrollRef.current?.scrollTo({
              y: posicaoLista.current,
              animated: false,
            });
            restaurarPosicaoLista.current = false;
          }
        }}
      >
        {erroContexto && (
          <View style={[styles.errorNotice, styles.pageNotice]}>
            <Text style={styles.emptyText}>
              Não foi possível atualizar os dados da aba: {erroContexto}
            </Text>
            <Text style={styles.emptyText}>
              Exibindo dados da última consulta bem-sucedida.
            </Text>
            <MotionPressable
              accessibilityRole="button"
              onPress={() => setTentativa((atual) => atual + 1)}
              style={styles.retryButton}
            >
              <Text style={styles.retryButtonText}>Tentar novamente</Text>
            </MotionPressable>
          </View>
        )}
        {erroFiltroAtual && erroFiltroAtual !== erroContexto && (
          <View style={[styles.errorNotice, styles.pageNotice]}>
            <Text style={styles.emptyText}>{erroFiltroAtual}</Text>
            {tarefas && (
              <Text style={styles.emptyText}>
                Exibindo tarefas da última consulta bem-sucedida.
              </Text>
            )}
            <MotionPressable
              accessibilityRole="button"
              onPress={() => setTentativa((atual) => atual + 1)}
              style={styles.retryButton}
            >
              <Text style={styles.retryButtonText}>Tentar novamente</Text>
            </MotionPressable>
          </View>
        )}
        {tarefaSelecionada && atualizando && (
          <View
            style={[styles.errorNotice, styles.pageNotice]}
            accessibilityLiveRegion="polite"
          >
            <Text style={styles.emptyText}>Atualizando dados da aba…</Text>
          </View>
        )}
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
            onReabrir={
              podeReabrirTarefa(
                tarefaSelecionada,
                usuarioAtual.id,
                casa.fk_usuario_id,
              )
                ? reabrirTarefaSelecionada
                : undefined
            }
            onContinuar={continuarAposFinalizacao}
          />
        ) : (
          <Animated.View
            entering={FadeIn.duration(220).reduceMotion(ReduceMotion.System)}
            style={[styles.content, telaPequena && styles.contentSmall]}
          >
            <CalendarioTarefas
              key={chaveCalendario}
              casa={casa}
              moradores={moradores}
              tarefas={todasTarefas}
              usuarioAtualId={usuarioAtual.id}
              diaSelecionado={
                selecaoCalendario?.chave === chaveCalendario
                  ? selecaoCalendario.dia
                  : dataNoFuso(new Date(), casa.timezone)
              }
              onSelecionarDia={(dia) =>
                setSelecaoCalendario({ chave: chaveCalendario, dia })
              }
              onSelecionarTarefa={setTarefaSelecionadaId}
              somenteMinhas={responsavel === usuarioAtual.id}
              onSomenteMinhasChange={(valor) =>
                setFiltros((atuais) => ({
                  ...atuais,
                  responsavel: valor ? usuarioAtual.id : "todos",
                }))
              }
            />
            <View style={styles.hero}>
              <View style={styles.heroCopy}>
                <Text style={styles.houseName}>{casa.nome}</Text>
                <Text
                  accessibilityRole="header"
                  style={[styles.title, telaPequena && styles.titleSmall]}
                >
                  TAREFAS DA CASA
                </Text>
                <Text style={styles.subtitle}>
                  Organize o combinado, veja quem ficou responsável e acompanhe
                  cada prazo.
                </Text>
                <View style={styles.heroActions}>
                  <MotionPressable
                    accessibilityRole="button"
                    accessibilityState={{
                      disabled: atualizando,
                      busy: atualizando,
                    }}
                    disabled={atualizando}
                    onPress={() => setTentativa((atual) => atual + 1)}
                    style={styles.retryButton}
                  >
                    <Text style={styles.retryButtonText}>
                      {atualizando ? "Atualizando…" : "Atualizar"}
                    </Text>
                  </MotionPressable>
                </View>
              </View>
              <View style={styles.statCard}>
                <Text style={styles.statValue}>{tarefasEmAberto}</Text>
                <Text style={styles.statLabel}>TAREFAS EM ABERTO</Text>
              </View>
            </View>

            <View style={styles.filtersSection}>
              <MotionPressable
                accessibilityRole="button"
                accessibilityState={{ expanded: filtrosAbertos }}
                onPress={() => setFiltrosAbertos((aberto) => !aberto)}
                style={styles.filtersToggle}
              >
                <Text style={styles.filterPillText}>
                  {`Filtros${filtrosAtivos ? ` (${quantidadeFiltros})` : ""} ${filtrosAbertos ? "▴" : "▾"}`}
                </Text>
              </MotionPressable>
              {filtrosAbertos && (
                <View
                  style={[styles.filtersCard, telaPequena && styles.cardSmall]}
                >
                  <View style={styles.filterGroup}>
                    <Text style={styles.filterLabel}>STATUS</Text>
                    <View style={styles.filterOptions}>
                      <FilterPill
                        label="Todos"
                        selected={filtros.estado === "todos"}
                        onPress={() =>
                          setFiltros((atuais) => ({
                            ...atuais,
                            estado: "todos",
                          }))
                        }
                      />
                      <FilterPill
                        label="Em aberto"
                        selected={filtros.estado === "em_aberto"}
                        onPress={() =>
                          setFiltros((atuais) => ({
                            ...atuais,
                            estado: "em_aberto",
                          }))
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
              )}
            </View>

            <View style={styles.listHeading}>
              <Text
                style={[
                  styles.sectionTitle,
                  telaPequena && styles.sectionTitleSmall,
                ]}
              >
                TAREFAS
              </Text>
              <Animated.Text
                key={`${tarefasVisiveis.length}:${tarefasFiltradas.length}`}
                accessibilityLiveRegion="polite"
                entering={FadeIn.duration(160).reduceMotion(
                  ReduceMotion.System,
                )}
                style={styles.resultCount}
              >
                Exibindo {tarefasVisiveis.length} de {tarefasFiltradas.length}{" "}
                resultados
              </Animated.Text>
            </View>

            {!tarefas && !erroFiltroAtual && (
              <View style={styles.errorNotice} accessibilityLiveRegion="polite">
                <Text style={styles.emptyText}>
                  Buscando tarefas para este filtro…
                </Text>
              </View>
            )}

            {tarefasFiltradas.length ? (
              <View style={styles.taskGrid}>
                {tarefasVisiveis.map((tarefa, index) => {
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
                        style={[
                          styles.taskCard,
                          telaPequena && styles.cardSmall,
                        ]}
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

                        <Text
                          style={[
                            styles.taskTitle,
                            telaPequena && styles.taskTitleSmall,
                          ]}
                        >
                          {tarefa.nome.toUpperCase()}
                        </Text>
                        <Text numberOfLines={2} style={styles.taskDescription}>
                          {tarefa.descricao || "Sem descrição."}
                        </Text>

                        <View style={styles.taskMeta}>
                          <View style={styles.deadline}>
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
            ) : tarefas ? (
              <Animated.View
                entering={FadeInDown.duration(220).reduceMotion(
                  ReduceMotion.System,
                )}
                exiting={FadeOut.duration(140).reduceMotion(
                  ReduceMotion.System,
                )}
                style={[styles.emptyCard, telaPequena && styles.cardSmall]}
              >
                <Text style={styles.emptyTitle}>NENHUMA TAREFA POR AQUI</Text>
                <Text style={styles.emptyText}>
                  Ajuste os filtros para ver outras tarefas da casa.
                </Text>
              </Animated.View>
            ) : null}
            {tarefasVisiveis.length < tarefasFiltradas.length && (
              <MotionPressable
                accessibilityRole="button"
                onPress={() =>
                  setListaVisivel((atual) => ({
                    ...atual,
                    limite: atual.limite + 12,
                  }))
                }
                style={[styles.retryButton, styles.loadMoreButton]}
              >
                <Text style={styles.retryButtonText}>Carregar mais</Text>
              </MotionPressable>
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
  pageSmall: {
    paddingHorizontal: Spacing.three,
    paddingTop: Platform.OS === "web" ? 160 : Spacing.three,
  },
  content: {
    width: "100%",
    maxWidth: 1280,
    alignSelf: "center",
    gap: 40,
  },
  contentSmall: { gap: Spacing.four },
  cardSmall: { padding: Spacing.three, borderRadius: 24 },
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
  heroActions: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  houseName: { color: Caldera.ember, fontSize: 14, fontWeight: "500" },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 64,
    lineHeight: 62,
    letterSpacing: 1.28,
  },
  titleSmall: { fontSize: 40, lineHeight: 44, letterSpacing: 0.8 },
  subtitle: {
    color: Caldera.obsidian,
    fontSize: 18,
    lineHeight: 28,
    fontWeight: "500",
    maxWidth: 620,
  },
  statCard: {
    flexShrink: 1,
    alignSelf: "center",
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.three,
    borderRadius: 24,
    backgroundColor: Caldera.ember,
    paddingHorizontal: Spacing.four,
    padding: Spacing.three,
  },
  statLabel: {
    color: Caldera.obsidian,
    fontSize: 14,
    fontWeight: "500",
    flexShrink: 1,
  },
  statValue: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 40,
    lineHeight: 44,
  },
  filtersSection: { gap: Spacing.three },
  filtersToggle: {
    alignSelf: "flex-start",
    minHeight: 44,
    justifyContent: "center",
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    backgroundColor: Caldera.limestone,
    paddingHorizontal: Spacing.three,
    paddingVertical: 10,
  },
  filtersCard: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.four,
  },
  filterGroup: { gap: 12 },
  filterLabel: { color: Caldera.obsidian, fontSize: 12, fontWeight: "500" },
  filterOptions: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  filterPill: {
    maxWidth: "100%",
    minHeight: 44,
    justifyContent: "center",
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.three,
    paddingVertical: 10,
  },
  filterPillText: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  listHeading: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    alignItems: "flex-end",
    gap: Spacing.three,
  },
  sectionTitle: {
    maxWidth: "100%",
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 48,
    lineHeight: 48,
    letterSpacing: 0.96,
  },
  sectionTitleSmall: { fontSize: 32, lineHeight: 36, letterSpacing: 0.64 },
  resultCount: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  taskGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "flex-start",
    gap: Spacing.four,
  },
  taskCardSlot: {
    minWidth: 0,
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 320,
  },
  taskCard: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.three,
  },
  taskTopRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    alignItems: "center",
    gap: Spacing.two,
  },
  statusBadge: {
    maxWidth: "100%",
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
  taskTitleSmall: { fontSize: 28, lineHeight: 32, letterSpacing: 0.56 },
  taskDescription: {
    color: Caldera.obsidian,
    fontSize: 16,
    lineHeight: 24,
    fontWeight: "500",
  },
  taskMeta: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    alignItems: "flex-end",
    gap: Spacing.three,
  },
  deadline: { flexShrink: 1, minWidth: 0, maxWidth: "100%" },
  metaLabel: {
    color: Caldera.obsidian,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: "500",
  },
  metaValue: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  avatars: { flexDirection: "row", flexWrap: "wrap", maxWidth: "100%" },
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
    gap: Spacing.two,
  },
  pageNotice: { width: "100%", maxWidth: 1280, alignSelf: "center" },
  retryButton: {
    backgroundColor: Caldera.ember,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.two,
  },
  retryButtonText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  loadMoreButton: {
    alignSelf: "center",
    minHeight: 44,
    justifyContent: "center",
  },
});
