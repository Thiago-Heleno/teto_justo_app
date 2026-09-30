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
import { carregarPlacar, type Placar } from "@/services/tarefas-api";
import {
  periodosPlacar,
  resumirPlacar,
  type PeriodoPlacar,
} from "@/utils/placar";

const numero = new Intl.NumberFormat("pt-BR");

export default function PontuacaoScreen() {
  const [placar, setPlacar] = useState<Placar>();
  const [periodo, setPeriodo] = useState<PeriodoPlacar>("semanal");
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
        .then(() => carregarPlacar(controlador.signal))
        .then((dados) => {
          if (!controlador.signal.aborted) setPlacar(dados);
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
          <View style={styles.hero}>
            <View style={styles.heroCopy}>
              <Text style={styles.eyebrow}>CADA TAREFA CONTA</Text>
              <Text
                accessibilityRole="header"
                style={[styles.title, width < 600 && styles.titleSmall]}
              >
                PONTUAÇÃO DA CASA
              </Text>
              <Text style={styles.subtitle}>
                Acompanhe os pontos e a contribuição de cada morador para a
                casa.
              </Text>
            </View>
            {resumo && (
              <View style={styles.statCard}>
                <Text style={styles.statLabel}>
                  TOTAL DA CASA · {rotulo.toUpperCase()}
                </Text>
                <Text style={styles.statValue}>
                  {numero.format(resumo.total)}
                </Text>
                <Text style={styles.statLabel}>
                  pontos de {resumo.moradores.length} moradores
                </Text>
              </View>
            )}
          </View>

          <View style={styles.card}>
            <View style={styles.sectionRow}>
              <Text accessibilityRole="header" style={styles.sectionTitle}>
                PERÍODO
              </Text>
              <MotionPressable
                accessibilityRole="button"
                accessibilityState={{ disabled: carregando }}
                disabled={carregando}
                onPress={() => setTentativa((valor) => valor + 1)}
                style={styles.action}
              >
                <Text style={styles.body}>
                  {carregando ? "Atualizando…" : "Atualizar"}
                </Text>
              </MotionPressable>
            </View>
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
            <Text style={styles.caption}>
              Semana, mês e ano atuais. O acumulado representa o saldo total de
              cada morador.
            </Text>
            {placar && (
              <Text style={styles.caption}>
                Períodos calculados no fuso {placar.fuso_horario}.
              </Text>
            )}
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
              <Text accessibilityRole="header" style={styles.sectionTitle}>
                CLASSIFICAÇÃO
              </Text>
              <Text style={styles.caption}>
                Maior pontuação primeiro. Pontuações iguais compartilham a mesma
                posição.
              </Text>
              {resumo.moradores.length === 0 ? (
                <Text style={styles.body}>
                  Ainda não há moradores no placar desta casa.
                </Text>
              ) : (
                resumo.moradores.map((morador) => (
                  <View key={morador.usuario_id} style={styles.resident}>
                    <View
                      style={[
                        styles.position,
                        morador.posicao === 1 && styles.positionFirst,
                      ]}
                    >
                      <Text style={styles.body}>{morador.posicao}º</Text>
                    </View>
                    <View style={styles.residentCopy}>
                      <Text style={styles.name}>{morador.nome}</Text>
                      <Text style={styles.caption}>
                        Saldo acumulado: {numero.format(morador.acumulado)} pts
                      </Text>
                    </View>
                    <View style={styles.pointsBlock}>
                      <Text style={styles.points}>
                        {numero.format(morador.pontos)}
                      </Text>
                      <Text style={styles.caption}>
                        pontos · {rotulo.toLowerCase()}
                      </Text>
                    </View>
                  </View>
                ))
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
  content: { width: "100%", maxWidth: 1280, alignSelf: "center", gap: 32 },
  hero: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.four },
  heroCopy: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 320,
    justifyContent: "center",
    gap: Spacing.three,
  },
  eyebrow: { color: Caldera.ember, fontSize: 14, fontWeight: "500" },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 64,
    lineHeight: 64,
    letterSpacing: 1.28,
  },
  titleSmall: { fontSize: 48, lineHeight: 50, letterSpacing: 0.96 },
  subtitle: {
    color: Caldera.obsidian,
    fontSize: 18,
    lineHeight: 28,
    fontWeight: "500",
    maxWidth: 620,
  },
  statCard: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 240,
    borderRadius: 40,
    backgroundColor: Caldera.ember,
    padding: Spacing.five,
    justifyContent: "space-between",
    gap: Spacing.three,
  },
  statLabel: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  statValue: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 80,
    lineHeight: 88,
  },
  card: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.four,
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
    fontSize: 32,
    lineHeight: 36,
    letterSpacing: 0.64,
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
    flexWrap: "wrap",
    alignItems: "center",
    gap: Spacing.three,
    backgroundColor: Caldera.pumice,
    borderRadius: 40,
    padding: Spacing.four,
  },
  position: {
    width: 48,
    height: 48,
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
  pointsBlock: { gap: 4 },
  points: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 40,
    lineHeight: 44,
  },
});
