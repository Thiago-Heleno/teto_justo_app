import { useCallback, useState } from "react";
import { useFocusEffect } from "expo-router";
import { ArrowLeft, ArrowRight, TrendingUp } from "lucide-react-native";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Line, Polyline, Text as SvgText } from "react-native-svg";

import { Avatar } from "@/components/avatar";
import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import { carregarDesempenho, type Desempenho } from "@/services/tarefas-api";
import {
  escalaPontos,
  posicaoDia,
  proporcaoPontos,
  resumirDia,
  rotuloDia,
  temSerieDiaria,
} from "@/utils/grafico-desempenho";
import type { PeriodoPlacar, resumirPlacar } from "@/utils/placar";

const numero = new Intl.NumberFormat("pt-BR");
const altura = 184;

type Props = {
  periodo: PeriodoPlacar;
  rotulo: string;
  tentativa: number;
  resumo?: ReturnType<typeof resumirPlacar>;
  fotos: Map<string, string | null | undefined>;
  usuarioId?: string;
};

type Consulta =
  | { estado: "carregando" }
  | { estado: "erro"; mensagem: string }
  | { estado: "pronto"; dados: Desempenho };

export function GraficoDesempenho({
  periodo,
  rotulo,
  tentativa,
  resumo,
  fotos,
  usuarioId,
}: Props) {
  const [consulta, setConsulta] = useState<Consulta>({ estado: "carregando" });
  const [reconsulta, setReconsulta] = useState(0);
  const [selecionado, setSelecionado] = useState<string>();
  const [diaSelecionado, setDiaSelecionado] = useState<string>();
  const [largura, setLargura] = useState(0);
  const diario = temSerieDiaria(periodo);

  useFocusEffect(
    useCallback(() => {
      if (!temSerieDiaria(periodo)) return;
      const controlador = new AbortController();
      setConsulta({ estado: "carregando" });
      Promise.resolve()
        .then(() => carregarDesempenho(periodo, controlador.signal))
        .then((dados) => {
          if (!controlador.signal.aborted)
            setConsulta({ estado: "pronto", dados });
        })
        .catch((erro: unknown) => {
          if (!controlador.signal.aborted)
            setConsulta({
              estado: "erro",
              mensagem:
                erro instanceof Error
                  ? erro.message
                  : "Não foi possível carregar o desempenho.",
            });
        });
      return () => controlador.abort();
    }, [periodo, tentativa, reconsulta]),
  );

  const dados = consulta.estado === "pronto" ? consulta.dados : undefined;
  const series = diario ? (dados?.moradores ?? []) : [];
  const { datas, indice, totais: totaisDia } = resumirDia(series, diaSelecionado);
  const totais = diario ? totaisDia : (resumo?.moradores ?? []);
  const destaque =
    totais.find((morador) => morador.usuario_id === selecionado) ??
    totais.find((morador) => morador.usuario_id === usuarioId) ??
    totais[0];
  const totalCasa = totais.reduce((soma, morador) => soma + morador.pontos, 0);
  const escala = escalaPontos(
    diario
      ? series.flatMap((morador) => morador.serie.map((p) => p.acumulado))
      : totais.map((morador) => morador.pontos),
  );
  const zero = proporcaoPontos(0, escala);
  const margemEsquerda = 52;
  const margemDireita = 14;
  const larguraUtil = Math.max(1, largura - margemEsquerda - margemDireita);
  const x = (i: number) =>
    margemEsquerda + posicaoDia(i, datas.length) * larguraUtil;
  const y = (pontos: number) =>
    14 + (1 - proporcaoPontos(pontos, escala)) * 142;
  const marcas = [...new Set([escala.maximo, 0, escala.minimo])];
  const rotulosEixo = marcas.filter(
    (valor) => valor === 0 || Math.abs(y(valor) - y(0)) >= 16,
  );
  const datasEixo = [
    ...new Set([0, Math.floor((datas.length - 1) / 2), datas.length - 1]),
  ];

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <View style={styles.headerCopy}>
          <Text style={styles.caption}>
            A CASA EM NÚMEROS · {rotulo.toUpperCase()}
          </Text>
          <Text accessibilityRole="header" style={styles.title}>
            DESEMPENHO GERAL
          </Text>
          <Text style={styles.body}>
            {diario
              ? "Evolução dos pontos dos moradores"
              : "Comparação dos pontos no período"}
          </Text>
        </View>
        <View style={styles.icon}>
          <TrendingUp size={24} color={Caldera.obsidian} />
        </View>
      </View>

      {diario && consulta.estado === "carregando" ? (
        <View style={styles.notice} accessibilityLiveRegion="polite">
          <ActivityIndicator color={Caldera.obsidian} />
          <Text style={styles.body}>Carregando a evolução da casa…</Text>
        </View>
      ) : diario && consulta.estado === "erro" ? (
        <View style={styles.notice} accessibilityLiveRegion="polite">
          <Text style={styles.body}>{consulta.mensagem}</Text>
          <MotionPressable
            accessibilityRole="button"
            style={styles.retry}
            onPress={() => setReconsulta((valor) => valor + 1)}
          >
            <Text style={styles.body}>Tentar novamente</Text>
          </MotionPressable>
        </View>
      ) : !diario && !resumo ? (
        <Text style={styles.body}>Aguardando o placar da casa.</Text>
      ) : totais.length === 0 ? (
        <Text style={styles.body}>Ainda não há moradores para comparar.</Text>
      ) : (
        <>
          <View style={styles.feature} accessibilityLiveRegion="polite">
            <View style={styles.headerCopy}>
              <Text style={styles.caption}>
                {diario
                  ? "TOTAL ATÉ A DATA SELECIONADA"
                  : "TOTAL DA CASA NO PERÍODO"}
              </Text>
              <Text style={styles.metric}>
                {numero.format(totalCasa)} <Text style={styles.body}>pts</Text>
              </Text>
            </View>
            {diario && datas[indice] && (
              <View style={styles.dateTag}>
                <Text style={styles.body}>{rotuloDia(datas[indice])}</Text>
              </View>
            )}
          </View>
          {diario && datas.length > 0 && (
            <>
              <View
                onLayout={(evento) =>
                  setLargura(evento.nativeEvent.layout.width)
                }
              >
                {largura > 90 && (
                  <Svg width={largura} height={altura} accessible={false}>
                    {marcas.map((valor) => (
                      <Line
                        key={valor}
                        x1={margemEsquerda}
                        x2={largura - margemDireita}
                        y1={y(valor)}
                        y2={y(valor)}
                        stroke={Caldera.obsidian}
                        strokeOpacity={valor === 0 ? 0.45 : 0.15}
                        strokeDasharray={valor === 0 ? undefined : "2 4"}
                      />
                    ))}
                    {rotulosEixo.map((valor) => (
                      <SvgText
                        key={valor}
                        x={margemEsquerda - 8}
                        y={y(valor) + 4}
                        fontSize={10}
                        textAnchor="end"
                        fill={Caldera.obsidian}
                      >
                        {numero.format(valor)}
                      </SvgText>
                    ))}
                    {datasEixo.map((i) => (
                      <SvgText
                        key={i}
                        x={x(i)}
                        y={altura - 5}
                        fontSize={10}
                        textAnchor={
                          datas.length === 1
                            ? "middle"
                            : i === 0
                              ? "start"
                              : i === datas.length - 1
                                ? "end"
                                : "middle"
                        }
                        fill={Caldera.obsidian}
                      >
                        {rotuloDia(datas[i])}
                      </SvgText>
                    ))}
                    <Line
                      x1={x(indice)}
                      x2={x(indice)}
                      y1={8}
                      y2={162}
                      stroke={Caldera.obsidian}
                      strokeOpacity={0.45}
                      strokeDasharray="3 4"
                    />
                    {[...series]
                      .sort(
                        (a, b) =>
                          Number(a.usuario_id === destaque?.usuario_id) -
                          Number(b.usuario_id === destaque?.usuario_id),
                      )
                      .map((morador) => {
                        const ativo =
                          morador.usuario_id === destaque?.usuario_id;
                        const cor = ativo ? Caldera.ember : Caldera.obsidian;
                        const ponto = morador.serie[indice];
                        return (
                          <Serie
                            key={morador.usuario_id}
                            ativo={ativo}
                            cor={cor}
                            pontos={morador.serie
                              .map((p, i) => `${x(i)},${y(p.acumulado)}`)
                              .join(" ")}
                            cx={x(indice)}
                            cy={y(ponto.acumulado)}
                          />
                        );
                      })}
                  </Svg>
                )}
              </View>
              <View style={styles.dateControls}>
                <MotionPressable
                  accessibilityRole="button"
                  accessibilityLabel="Dia anterior"
                  accessibilityState={{ disabled: indice <= 0 }}
                  disabled={indice <= 0}
                  onPress={() => setDiaSelecionado(datas[indice - 1])}
                  style={[styles.arrow, indice <= 0 && styles.disabled]}
                >
                  <ArrowLeft size={18} color={Caldera.obsidian} />
                </MotionPressable>
                <MotionPressable
                  accessibilityRole="button"
                  accessibilityLabel="Voltar ao último dia"
                  onPress={() => setDiaSelecionado(undefined)}
                  style={styles.dateCenter}
                >
                  <Text style={styles.body}>
                    {rotuloDia(datas[indice])} · {indice + 1}/{datas.length}
                  </Text>
                  <Text style={styles.caption}>Ir ao último dia</Text>
                </MotionPressable>
                <MotionPressable
                  accessibilityRole="button"
                  accessibilityLabel="Próximo dia"
                  accessibilityState={{ disabled: indice >= datas.length - 1 }}
                  disabled={indice >= datas.length - 1}
                  onPress={() => setDiaSelecionado(datas[indice + 1])}
                  style={[
                    styles.arrow,
                    indice >= datas.length - 1 && styles.disabled,
                  ]}
                >
                  <ArrowRight size={18} color={Caldera.obsidian} />
                </MotionPressable>
              </View>
            </>
          )}
          <Text style={styles.caption}>
            {diario
              ? "Toque em um morador para destacar sua curva. Os valores são acumulados desde o início do período."
              : "Toque em um morador para destacar sua barra. A linha marca zero; estornos podem deixar o total negativo."}
          </Text>
          {totais.map((morador) => {
            const ativo = morador.usuario_id === destaque?.usuario_id;
            const fim = proporcaoPontos(morador.pontos, escala);
            return (
              <MotionPressable
                key={morador.usuario_id}
                accessibilityRole="button"
                accessibilityState={{ selected: ativo }}
                accessibilityLabel={`${morador.nome}, ${numero.format(morador.pontos)} pontos${morador.usuario_id === usuarioId ? ", você" : ""}`}
                onPress={() => setSelecionado(morador.usuario_id)}
                style={[styles.resident, ativo && styles.residentSelected]}
              >
                <View style={styles.residentRow}>
                  <View
                    style={[
                      styles.dot,
                      {
                        backgroundColor: ativo
                          ? Caldera.ember
                          : Caldera.obsidian,
                      },
                    ]}
                  />
                  <Avatar
                    nome={morador.nome}
                    foto={fotos.get(morador.usuario_id)}
                    tamanho={36}
                  />
                  <Text style={[styles.body, styles.residentName]}>
                    {morador.nome}
                    {morador.usuario_id === usuarioId ? " · Você" : ""}
                  </Text>
                  <Text style={styles.points}>
                    {numero.format(morador.pontos)}{" "}
                    <Text style={styles.caption}>pts</Text>
                  </Text>
                </View>
                {!diario && (
                  <View style={styles.track}>
                    <View
                      style={[
                        styles.bar,
                        {
                          left: `${Math.min(zero, fim) * 100}%`,
                          width: `${Math.abs(fim - zero) * 100}%`,
                          backgroundColor: ativo
                            ? Caldera.ember
                            : Caldera.obsidian,
                        },
                      ]}
                    />
                    <View style={[styles.zero, { left: `${zero * 100}%` }]} />
                  </View>
                )}
              </MotionPressable>
            );
          })}
          {totais.every((morador) => morador.pontos === 0) && (
            <Text style={styles.caption}>
              Todos os moradores estão com zero pontos nesta{" "}
              {diario ? "data" : "seleção"}.
            </Text>
          )}
          {!diario && (
            <Text style={styles.caption}>
              O histórico diário não está disponível para este período. Os
              totais vêm do placar da casa.
            </Text>
          )}
        </>
      )}
    </View>
  );
}

function Serie({
  ativo,
  cor,
  pontos,
  cx,
  cy,
}: {
  ativo: boolean;
  cor: string;
  pontos: string;
  cx: number;
  cy: number;
}) {
  return (
    <>
      <Polyline
        points={pontos}
        fill="none"
        stroke={cor}
        strokeWidth={ativo ? 3 : 1.5}
        strokeOpacity={ativo ? 1 : 0.4}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <Circle
        cx={cx}
        cy={cy}
        r={ativo ? 5 : 3}
        fill={cor}
        stroke={Caldera.limestone}
        strokeWidth={1.5}
      />
    </>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Caldera.limestone,
    borderRadius: 24,
    padding: Spacing.three,
    gap: Spacing.three,
  },
  header: { flexDirection: "row", alignItems: "center", gap: Spacing.two },
  headerCopy: { flex: 1, minWidth: 0, gap: Spacing.one },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 30,
    lineHeight: 34,
    letterSpacing: 0.6,
  },
  body: {
    color: Caldera.obsidian,
    fontSize: 14,
    lineHeight: 20,
    fontWeight: "500",
  },
  caption: {
    color: Caldera.obsidian,
    fontSize: 12,
    lineHeight: 18,
    fontWeight: "500",
  },
  icon: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: Caldera.sulfur,
    alignItems: "center",
    justifyContent: "center",
  },
  feature: {
    backgroundColor: Caldera.ember,
    borderRadius: 20,
    padding: Spacing.three,
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.two,
  },
  metric: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 40,
    lineHeight: 46,
  },
  dateTag: {
    backgroundColor: Caldera.limestone,
    borderRadius: 800,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  notice: { gap: Spacing.two, alignItems: "flex-start" },
  retry: { backgroundColor: Caldera.ember, borderRadius: 800, padding: 12 },
  dateControls: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: Spacing.two,
  },
  dateCenter: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 44,
  },
  arrow: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 800,
    backgroundColor: Caldera.pumice,
  },
  disabled: { opacity: 0.35 },
  resident: {
    padding: Spacing.two,
    borderRadius: 16,
    gap: Spacing.two,
    borderWidth: 1,
    borderColor: "transparent",
  },
  residentSelected: {
    backgroundColor: Caldera.pumice,
    borderColor: Caldera.obsidian,
  },
  residentRow: { flexDirection: "row", alignItems: "center", gap: Spacing.two },
  residentName: { flex: 1, minWidth: 0 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  points: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 22,
    lineHeight: 26,
  },
  track: {
    height: 10,
    backgroundColor: Caldera.pumice,
    borderRadius: 800,
    position: "relative",
  },
  bar: { position: "absolute", top: 0, bottom: 0, borderRadius: 800 },
  zero: {
    position: "absolute",
    top: -2,
    bottom: -2,
    width: 1,
    backgroundColor: Caldera.obsidian,
  },
});
