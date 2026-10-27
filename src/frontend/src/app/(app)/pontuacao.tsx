import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import {
  ActivityIndicator,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import {
  carregarExtrato,
  carregarPlacar,
  carregarUsuarioAtual,
  type Extrato,
  type Placar,
} from "@/services/tarefas-api";
import {
  periodosPlacar,
  resumirPlacar,
  type PeriodoPlacar,
} from "@/utils/placar";

const numero = new Intl.NumberFormat("pt-BR");
const dataHora = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

export default function PontuacaoScreen() {
  const [placar, setPlacar] = useState<Placar>();
  const [usuarioId, setUsuarioId] = useState<string>();
  const [extrato, setExtrato] = useState<Extrato>();
  const [periodo, setPeriodo] = useState<PeriodoPlacar>("semanal");
  const [ajudaAberta, setAjudaAberta] = useState(false);
  const [movimentacoesVisiveis, setMovimentacoesVisiveis] = useState(5);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string>();
  const [tentativa, setTentativa] = useState(0);
  const { width } = useWindowDimensions();

  useFocusEffect(
    useCallback(() => {
      const controlador = new AbortController();
      setCarregando(true);
      setErro(undefined);
      // Promise.resolve também captura erro síncrono de configuração da API.
      Promise.resolve()
        .then(() =>
          Promise.all([
            carregarPlacar(controlador.signal),
            carregarExtrato(controlador.signal),
            carregarUsuarioAtual(controlador.signal).catch(() => undefined),
          ]),
        )
        .then(([dadosPlacar, dadosExtrato, usuario]) => {
          if (controlador.signal.aborted) return;
          setPlacar(dadosPlacar);
          setUsuarioId(usuario?.id);
          setExtrato(dadosExtrato);
        })
        .catch((falha: unknown) => {
          if (!controlador.signal.aborted) {
            setErro(
              falha instanceof Error
                ? falha.message
                : "Não foi possível carregar a pontuação.",
            );
          }
        })
        .finally(() => {
          if (!controlador.signal.aborted) setCarregando(false);
        });
      return () => controlador.abort();
      // Atualizar recria a consulta mesmo quando a aba continua em foco.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [tentativa]),
  );

  const resumo = placar ? resumirPlacar(placar, periodo) : undefined;
  const rotulo = periodosPlacar.find(
    (opcao) => opcao.valor === periodo,
  )!.rotulo;

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
      <ScrollView
        contentContainerStyle={[
          styles.page,
          Platform.OS === "web" && width < 600 && styles.pageSmallWeb,
        ]}
      >
        <View style={styles.content}>
          <View style={styles.sectionRow}>
            <View style={styles.headerCopy}>
              <Text accessibilityRole="header" style={styles.title}>
                PONTUAÇÃO
              </Text>
              {resumo && (
                <Text style={styles.body}>
                  Total da casa: {numero.format(resumo.total)} pts ·{" "}
                  {rotulo.toLowerCase()}
                </Text>
              )}
            </View>
            <MotionPressable
              accessibilityRole="button"
              accessibilityState={{ disabled: carregando, busy: carregando }}
              disabled={carregando}
              onPress={() => setTentativa((valor) => valor + 1)}
              style={styles.action}
            >
              <Text style={styles.body}>
                {carregando ? "Atualizando…" : "Atualizar"}
              </Text>
            </MotionPressable>
          </View>

          {carregando && (
            <View style={styles.notice} accessibilityLiveRegion="polite">
              <ActivityIndicator color={Caldera.obsidian} />
              <Text style={styles.body}>Buscando a pontuação da casa…</Text>
            </View>
          )}
          {erro && (
            <View style={styles.card} accessibilityLiveRegion="polite">
              <Text accessibilityRole="header" style={styles.sectionTitle}>
                NÃO FOI POSSÍVEL ATUALIZAR
              </Text>
              <Text style={styles.body}>{erro}</Text>
              {placar && (
                <Text style={styles.caption}>
                  Os pontos abaixo são da última consulta bem-sucedida.
                </Text>
              )}
              <MotionPressable
                accessibilityRole="button"
                onPress={() => setTentativa((valor) => valor + 1)}
                style={styles.action}
              >
                <Text style={styles.body}>Tentar novamente</Text>
              </MotionPressable>
            </View>
          )}

          {resumo && (
            <View style={styles.card}>
              <View style={styles.sectionRow}>
                <Text accessibilityRole="header" style={styles.sectionTitle}>
                  PLACAR DA CASA
                </Text>
                <MotionPressable
                  accessibilityRole="button"
                  accessibilityState={{ expanded: ajudaAberta }}
                  onPress={() => setAjudaAberta((aberta) => !aberta)}
                  style={styles.helpAction}
                >
                  <Text style={styles.caption}>Como funciona</Text>
                </MotionPressable>
              </View>
              {ajudaAberta && (
                <Text style={styles.caption}>
                  Semana, mês e ano atuais, no fuso {placar?.fuso_horario}. O
                  acumulado soma todo o histórico, incluindo estornos por
                  reabertura. A maior pontuação aparece primeiro e empates
                  compartilham a mesma posição. O período altera apenas o placar
                  e o total da casa.
                </Text>
              )}
              <View style={styles.pills}>
                {periodosPlacar.map((opcao) => (
                  <MotionPressable
                    key={opcao.valor}
                    accessibilityRole="button"
                    accessibilityState={{ selected: periodo === opcao.valor }}
                    onPress={() => setPeriodo(opcao.valor)}
                    style={[
                      styles.pill,
                      periodo === opcao.valor && styles.pillSelected,
                    ]}
                  >
                    <Text style={styles.body}>{opcao.rotulo}</Text>
                  </MotionPressable>
                ))}
              </View>
              {resumo.moradores.length === 0 ? (
                <Text style={styles.body}>
                  Ainda não há moradores no placar desta casa.
                </Text>
              ) : (
                resumo.moradores.map((morador) => (
                  <View
                    key={morador.usuario_id}
                    style={[
                      styles.resident,
                      morador.usuario_id === usuarioId &&
                        styles.residentCurrent,
                    ]}
                  >
                    <View
                      style={[
                        styles.position,
                        morador.posicao === 1 && styles.positionFirst,
                      ]}
                    >
                      <Text style={styles.body}>{morador.posicao}º</Text>
                    </View>
                    <Text style={[styles.name, styles.residentName]}>
                      {morador.nome}
                      {morador.usuario_id === usuarioId ? " · Você" : ""}
                    </Text>
                    <Text style={styles.points}>
                      {numero.format(morador.pontos)}{" "}
                      <Text style={styles.caption}>pts</Text>
                    </Text>
                  </View>
                ))
              )}
            </View>
          )}

          {extrato && (
            <View style={styles.card}>
              <Text accessibilityRole="header" style={styles.sectionTitle}>
                MOVIMENTAÇÕES RECENTES
              </Text>
              {extrato.eventos.length === 0 ? (
                <Text style={styles.body}>
                  Ainda não há movimentações de pontos nesta casa.
                </Text>
              ) : (
                extrato.eventos
                  .slice(0, movimentacoesVisiveis)
                  .map((evento) => {
                    const nome = placar?.moradores.find(
                      (morador) => morador.usuario_id === evento.fk_usuario_id,
                    )?.nome;
                    return (
                      <View key={evento.id} style={styles.eventRow}>
                        <View style={styles.residentCopy}>
                          <Text style={styles.name}>
                            {evento.tipo === "reversal"
                              ? "Estorno por reabertura"
                              : "Tarefa concluída"}
                            {nome ? ` · ${nome}` : ""}
                          </Text>
                          <Text style={styles.body} numberOfLines={2}>
                            {evento.nome_tarefa?.trim() || "Tarefa sem nome disponível"}
                          </Text>
                          <Text style={styles.caption}>
                            {dataHora.format(new Date(evento.criado_em))}
                          </Text>
                        </View>
                        <Text style={styles.name}>
                          {evento.pontuacao > 0 ? "+" : ""}
                          {numero.format(evento.pontuacao)} pts
                        </Text>
                      </View>
                    );
                  })
              )}
              {extrato.eventos.length > movimentacoesVisiveis && (
                <MotionPressable
                  accessibilityRole="button"
                  accessibilityLabel="Ver mais movimentações"
                  onPress={() =>
                    setMovimentacoesVisiveis((quantidade) => quantidade + 5)
                  }
                  style={styles.action}
                >
                  <Text style={styles.body}>Ver mais</Text>
                </MotionPressable>
              )}
              {extrato.total >
                Math.min(movimentacoesVisiveis, extrato.eventos.length) && (
                <Text style={styles.caption} accessibilityLiveRegion="polite">
                  Mostrando as{" "}
                  {Math.min(movimentacoesVisiveis, extrato.eventos.length)}{" "}
                  movimentações mais recentes de {extrato.total}.
                </Text>
              )}
            </View>
          )}
        </View>
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
  pageSmallWeb: { paddingTop: 160, paddingHorizontal: Spacing.three },
  content: {
    width: "100%",
    maxWidth: 1280,
    alignSelf: "center",
    gap: Spacing.four,
  },
  headerCopy: { flexShrink: 1, gap: Spacing.two },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 40,
    lineHeight: 44,
    letterSpacing: 0.8,
  },
  card: {
    backgroundColor: Caldera.limestone,
    borderRadius: 24,
    padding: Spacing.three,
    gap: Spacing.three,
  },
  sectionRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    alignItems: "center",
    gap: Spacing.three,
  },
  sectionTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 28,
    lineHeight: 32,
    letterSpacing: 0.56,
  },
  body: {
    color: Caldera.obsidian,
    fontSize: 16,
    lineHeight: 24,
    fontWeight: "500",
  },
  caption: {
    color: Caldera.obsidian,
    fontSize: 12,
    lineHeight: 18,
    fontWeight: "500",
  },
  action: {
    alignSelf: "flex-start",
    backgroundColor: Caldera.ember,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
  },
  helpAction: { minHeight: 44, justifyContent: "center" },
  pills: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  pill: {
    borderRadius: 800,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    paddingHorizontal: Spacing.three,
    paddingVertical: 10,
  },
  pillSelected: { backgroundColor: Caldera.ember },
  notice: { flexDirection: "row", alignItems: "center", gap: Spacing.three },
  resident: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.two,
    backgroundColor: Caldera.pumice,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "transparent",
    padding: Spacing.three,
  },
  residentCurrent: { borderColor: Caldera.obsidian },
  residentName: { flex: 1, minWidth: 0 },
  position: {
    width: 36,
    height: 36,
    borderRadius: 800,
    backgroundColor: Caldera.limestone,
    alignItems: "center",
    justifyContent: "center",
  },
  positionFirst: { backgroundColor: Caldera.sulfur },
  residentCopy: { flexGrow: 1, flexShrink: 1, flexBasis: 140, gap: 4 },
  name: {
    color: Caldera.obsidian,
    fontSize: 18,
    lineHeight: 26,
    fontWeight: "500",
  },
  eventRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: Spacing.three,
    backgroundColor: Caldera.pumice,
    borderRadius: 24,
    padding: Spacing.three,
  },
  points: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 28,
    lineHeight: 32,
  },
});
