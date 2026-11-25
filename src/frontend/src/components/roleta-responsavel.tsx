import { useEffect, useState } from "react";
import {
  AccessibilityInfo,
  Platform,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import Animated, {
  cancelAnimation,
  Easing,
  ReduceMotion,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withRepeat,
  withTiming,
} from "react-native-reanimated";
import Svg, { Circle, G, Path, Text as SvgText } from "react-native-svg";
import { scheduleOnRN } from "react-native-worklets";

import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, Spacing } from "@/constants/theme";
import { listarMoradoresCasa } from "@/services/casas-api";
import { anguloGiroRoleta, rotulosRoleta } from "@/utils/roleta";

type Candidato = { id: string; nome: string };

export type ResultadoRoleta = {
  casaId: string;
  candidatos: readonly Candidato[];
  administrador?: Candidato;
  sorteadoId?: string;
};

type Props = Omit<ResultadoRoleta, "casaId"> & {
  casaId?: string;
  onGirar?: () => void;
  salvando?: boolean;
  animarResultado?: boolean;
  nomeResponsavel?: string;
  origem?: "giro" | "balanceamento" | null;
  exibirCandidatos?: boolean;
};

const centro = 120;
const raio = 108;
const cores = [
  Caldera.ember,
  Caldera.sulfur,
  Caldera.plasmaViolet,
  Caldera.pumice,
];

function pontoNaRoda(angulo: number, distancia: number) {
  const radianos = (angulo * Math.PI) / 180;
  return {
    x: centro + distancia * Math.sin(radianos),
    y: centro - distancia * Math.cos(radianos),
  };
}

export function RoletaResponsavel({
  casaId,
  candidatos,
  administrador,
  sorteadoId,
  onGirar,
  salvando = false,
  animarResultado = true,
  nomeResponsavel,
  origem,
  exibirCandidatos = false,
}: Props) {
  const movimentoReduzido = useReducedMotion();
  const { width } = useWindowDimensions();
  const [listaAtualizada, setListaAtualizada] = useState<
    readonly Candidato[] | null
  >();
  const moradoresDaCasa = listaAtualizada ?? candidatos;
  const moradores =
    administrador && !moradoresDaCasa.some(({ id }) => id === administrador.id)
      ? [...moradoresDaCasa, administrador]
      : moradoresDaCasa;
  const indice = moradores.findIndex(({ id }) => id === sorteadoId);
  const nomeSorteado =
    nomeResponsavel || (indice >= 0 ? moradores.at(indice)?.nome : undefined);
  const rotulos = rotulosRoleta(moradores.map(({ nome }) => nome));
  const { primeiro, legenda } =
    (indice >= 0 ? rotulos.at(indice) : undefined) ??
    rotulosRoleta([nomeSorteado ?? ""])[0];
  const mostrarNasFatias =
    width >= 300 &&
    moradores.length <= 8 &&
    rotulos.every(
      ({ primeiro: nome }) => nome && Array.from(nome).length <= 10,
    );
  const mostrarLegenda =
    !mostrarNasFatias ||
    rotulos.some((rotulo) => rotulo.primeiro !== rotulo.legenda);
  const buscandoSorteado =
    !!casaId && !!sorteadoId && !nomeSorteado && listaAtualizada === undefined;
  const anguloFinal = anguloGiroRoleta(indice, moradores.length);
  const rotacao = useSharedValue(0);
  const [giroConcluido, setGiroConcluido] = useState<string>();
  const rodandoEnquantoAguarda =
    !movimentoReduzido &&
    moradores.length > 1 &&
    (salvando || buscandoSorteado);
  const girando =
    animarResultado &&
    !movimentoReduzido &&
    anguloFinal !== undefined &&
    sorteadoId !== giroConcluido;
  const estiloRoda = useAnimatedStyle(() => ({
    transform: [{ rotate: `${rotacao.value}deg` }],
  }));

  useEffect(() => {
    if (rodandoEnquantoAguarda) {
      rotacao.set(
        withRepeat(
          withTiming(360, {
            duration: 750,
            easing: Easing.linear,
            reduceMotion: ReduceMotion.System,
          }),
          -1,
          false,
          undefined,
          ReduceMotion.System,
        ),
      );
      return () => cancelAnimation(rotacao);
    }
    if (anguloFinal === undefined) {
      rotacao.set(0);
      return;
    }
    if (!animarResultado || movimentoReduzido) {
      rotacao.set(anguloFinal);
      return;
    }
    rotacao.set(
      withTiming(
        anguloFinal,
        {
          duration: 2000,
          easing: Easing.out(Easing.cubic),
          reduceMotion: ReduceMotion.System,
        },
        (terminou) => {
          if (terminou) scheduleOnRN(setGiroConcluido, sorteadoId);
        },
      ),
    );
    return () => cancelAnimation(rotacao);
  }, [
    anguloFinal,
    animarResultado,
    movimentoReduzido,
    rodandoEnquantoAguarda,
    rotacao,
    sorteadoId,
  ]);

  useEffect(() => {
    if (!buscandoSorteado || !casaId) return;
    const controlador = new AbortController();
    listarMoradoresCasa(casaId, controlador.signal)
      .then((moradoresAtuais) => {
        if (!controlador.signal.aborted) setListaAtualizada(moradoresAtuais);
      })
      .catch(() => {
        if (!controlador.signal.aborted) setListaAtualizada(null);
      });
    return () => controlador.abort();
  }, [buscandoSorteado, casaId]);

  const resultadoVisivel = nomeSorteado && !salvando && !girando;
  const rotuloResultado =
    origem === "balanceamento"
      ? "Responsável por balanceamento"
      : "Responsável sorteado";
  const anuncio = resultadoVisivel
    ? `${rotuloResultado}: ${nomeSorteado}`
    : undefined;
  const mensagem =
    salvando || girando
      ? "Sorteando…"
      : onGirar || resultadoVisivel
        ? undefined
        : buscandoSorteado
          ? "Buscando o nome do responsável…"
          : sorteadoId
            ? "Atribuição confirmada. O nome do responsável está indisponível."
            : undefined;

  useEffect(() => {
    if (
      Platform.OS === "ios" &&
      anuncio &&
      !salvando &&
      !girando &&
      !buscandoSorteado
    )
      AccessibilityInfo.announceForAccessibility(anuncio);
  }, [anuncio, buscandoSorteado, girando, salvando]);

  const larguraFatia = 360 / moradores.length;
  const rodaVisivel =
    moradores.length > 0 &&
    (exibirCandidatos ||
      nomeSorteado ||
      onGirar ||
      buscandoSorteado ||
      salvando);
  return (
    <View style={styles.resultado}>
      {rodaVisivel && (
        <View
          style={styles.roda}
          aria-hidden
          importantForAccessibility="no-hide-descendants"
        >
          <Animated.View style={[StyleSheet.absoluteFill, estiloRoda]}>
            <Svg width="100%" height="100%" viewBox="0 0 240 240">
              <Circle cx={centro} cy={centro} r={114} fill={Caldera.obsidian} />
              {moradores.length === 1 && (
                <Circle cx={centro} cy={centro} r={raio} fill={cores[0]} />
              )}
              {moradores.map((morador, indiceFatia) => {
                const angulo = indiceFatia * larguraFatia;
                const inicio = pontoNaRoda(angulo - larguraFatia / 2, raio);
                const fim = pontoNaRoda(angulo + larguraFatia / 2, raio);
                const rotulo = pontoNaRoda(angulo, 54);
                const inclinacao = angulo > 180 ? angulo - 270 : angulo - 90;
                const cor = cores[indiceFatia % cores.length];
                return (
                  <G key={morador.id}>
                    {moradores.length > 1 && (
                      <Path
                        d={`M ${centro} ${centro} L ${inicio.x} ${inicio.y} A ${raio} ${raio} 0 0 1 ${fim.x} ${fim.y} Z`}
                        fill={cor}
                        stroke={Caldera.limestone}
                        strokeWidth={2.5}
                      />
                    )}
                    {mostrarNasFatias && (
                      <SvgText
                        x={rotulo.x}
                        y={rotulo.y}
                        transform={`rotate(${inclinacao} ${rotulo.x} ${rotulo.y})`}
                        textAnchor="middle"
                        alignmentBaseline="middle"
                        fill={
                          cor === Caldera.plasmaViolet
                            ? Caldera.chalk
                            : Caldera.obsidian
                        }
                        fontSize={12}
                        fontFamily="sans-serif"
                        fontWeight="bold"
                      >
                        {rotulos.at(indiceFatia)?.primeiro}
                      </SvgText>
                    )}
                  </G>
                );
              })}
              <Circle cx={centro} cy={centro} r={15} fill={Caldera.obsidian} />
              <Circle cx={centro} cy={centro} r={5} fill={Caldera.sulfur} />
            </Svg>
          </Animated.View>
          <Svg
            style={StyleSheet.absoluteFill}
            width="100%"
            height="100%"
            viewBox="0 0 240 240"
          >
            <Path
              d="M 106 2 H 134 L 120 28 Z"
              fill={Caldera.ember}
              stroke={Caldera.obsidian}
              strokeWidth={2}
              strokeLinejoin="round"
            />
          </Svg>
        </View>
      )}
      {rodaVisivel && mostrarLegenda && (
        <View style={styles.legenda}>
          {moradores.map(({ id }, posicao) => (
            <View key={id} style={styles.itemLegenda}>
              <View
                style={[
                  styles.ponto,
                  { backgroundColor: cores[posicao % cores.length] },
                ]}
              />
              <Text style={styles.nomeLegenda}>
                {rotulos.at(posicao)?.legenda || `Participante ${posicao + 1}`}
              </Text>
            </View>
          ))}
        </View>
      )}
      {resultadoVisivel && (
        <View
          accessible
          accessibilityLabel={anuncio}
          accessibilityLiveRegion="polite"
          aria-live="polite"
          style={styles.destaqueResultado}
        >
          <Text style={styles.ajuda}>{rotuloResultado}</Text>
          <Text style={styles.primeiroNome}>{primeiro}</Text>
          {legenda !== primeiro && <Text style={styles.ajuda}>{legenda}</Text>}
        </View>
      )}
      {mensagem && (
        <Text
          accessibilityLiveRegion="polite"
          aria-live="polite"
          style={styles.mensagem}
        >
          {mensagem}
        </Text>
      )}
      {onGirar && (
        <MotionPressable
          accessibilityRole="button"
          accessibilityState={{ busy: salvando, disabled: salvando }}
          disabled={salvando}
          onPress={onGirar}
          style={[styles.botao, salvando && styles.botaoDesativado]}
        >
          <Text style={styles.mensagem}>Girar a roleta</Text>
        </MotionPressable>
      )}
      {nomeSorteado && moradores.length === 1 && (
        <Text style={styles.ajuda}>Há um único candidato ao sorteio.</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  resultado: { alignItems: "center", gap: Spacing.two },
  roda: { width: "100%", maxWidth: 288, aspectRatio: 1 },
  legenda: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: Spacing.two,
  },
  itemLegenda: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.one,
    maxWidth: "100%",
  },
  nomeLegenda: { color: Caldera.obsidian, flexShrink: 1 },
  ponto: {
    width: 10,
    height: 10,
    borderRadius: 5,
    borderWidth: 1,
    borderColor: Caldera.obsidian,
  },
  destaqueResultado: {
    alignSelf: "center",
    alignItems: "center",
    width: "100%",
    maxWidth: 420,
    paddingVertical: Spacing.one,
  },
  primeiroNome: {
    color: Caldera.obsidian,
    maxWidth: "100%",
    fontSize: 36,
    fontWeight: "900",
    textAlign: "center",
  },
  ajuda: { color: Caldera.obsidian, textAlign: "center" },
  botao: {
    minHeight: 44,
    justifyContent: "center",
    backgroundColor: Caldera.ember,
    borderRadius: 800,
    paddingHorizontal: Spacing.three,
  },
  botaoDesativado: { opacity: 0.6 },
  mensagem: {
    color: Caldera.obsidian,
    fontSize: 16,
    fontWeight: "600",
    textAlign: "center",
  },
});
