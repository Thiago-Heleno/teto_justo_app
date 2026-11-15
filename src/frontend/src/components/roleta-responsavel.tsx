import { useEffect, useState } from "react";
import {
  AccessibilityInfo,
  Platform,
  StyleSheet,
  Text,
  View,
} from "react-native";
import Animated, {
  cancelAnimation,
  Easing,
  ReduceMotion,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from "react-native-reanimated";
import Svg, { Circle, G, Path, Text as SvgText } from "react-native-svg";
import { scheduleOnRN } from "react-native-worklets";

import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, Spacing } from "@/constants/theme";
import { listarMoradoresCasa } from "@/services/casas-api";
import { anguloGiroRoleta } from "@/utils/roleta";

type Candidato = { id: string; nome: string };

export type ResultadoRoleta = {
  casaId: string;
  candidatos: readonly Candidato[];
  administrador?: Candidato;
  sorteadoId?: string;
};

type Props = ResultadoRoleta & {
  onGirar?: () => void;
  salvando?: boolean;
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
}: Props) {
  const [listaAtualizada, setListaAtualizada] = useState<
    readonly Candidato[] | null
  >();
  const moradoresDaCasa = listaAtualizada ?? candidatos;
  const moradores =
    administrador && !moradoresDaCasa.some(({ id }) => id === administrador.id)
      ? [...moradoresDaCasa, administrador]
      : moradoresDaCasa;
  const indice = moradores.findIndex(({ id }) => id === sorteadoId);
  const nomeSorteado = indice >= 0 ? moradores.at(indice)?.nome : undefined;
  const buscandoSorteado =
    !!sorteadoId && !nomeSorteado && listaAtualizada === undefined;
  const anguloFinal = anguloGiroRoleta(indice, moradores.length);
  const rotacao = useSharedValue(0);
  const [giroConcluido, setGiroConcluido] = useState(false);
  const rodandoEnquantoAguarda =
    moradores.length > 1 && (salvando || buscandoSorteado);
  const girando = anguloFinal !== undefined && !giroConcluido;
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
            reduceMotion: ReduceMotion.Never,
          }),
          -1,
          false,
          undefined,
          ReduceMotion.Never,
        ),
      );
      return () => cancelAnimation(rotacao);
    }
    if (anguloFinal === undefined) {
      rotacao.set(0);
      return;
    }
    rotacao.set(
      withTiming(
        anguloFinal,
        {
          duration: 2000,
          easing: Easing.out(Easing.cubic),
          reduceMotion: ReduceMotion.Never,
        },
        (terminou) => {
          if (terminou) scheduleOnRN(setGiroConcluido, true);
        },
      ),
    );
    return () => cancelAnimation(rotacao);
  }, [anguloFinal, rodandoEnquantoAguarda, rotacao]);

  useEffect(() => {
    if (!buscandoSorteado) return;
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

  const mensagem =
    salvando || girando
      ? "Sorteando…"
      : onGirar
        ? undefined
        : nomeSorteado
          ? `Responsável sorteado: ${nomeSorteado}`
          : buscandoSorteado
            ? "Buscando o nome do responsável…"
            : "Tarefa salva. O nome do responsável está indisponível.";

  useEffect(() => {
    if (
      Platform.OS === "ios" &&
      mensagem &&
      !salvando &&
      !girando &&
      !buscandoSorteado
    )
      AccessibilityInfo.announceForAccessibility(mensagem);
  }, [buscandoSorteado, girando, mensagem, salvando]);

  const larguraFatia = 360 / moradores.length;
  return (
    <View style={styles.resultado}>
      {moradores.length > 0 &&
        (nomeSorteado || onGirar || buscandoSorteado) && (
          <View
            style={styles.roda}
            aria-hidden
            importantForAccessibility="no-hide-descendants"
          >
            <Animated.View style={[StyleSheet.absoluteFill, estiloRoda]}>
              <Svg width="100%" height="100%" viewBox="0 0 240 240">
                {moradores.length === 1 && (
                  <Circle cx={centro} cy={centro} r={raio} fill={cores[0]} />
                )}
                {moradores.map((morador, indiceFatia) => {
                  const angulo = indiceFatia * larguraFatia;
                  const inicio = pontoNaRoda(angulo - larguraFatia / 2, raio);
                  const fim = pontoNaRoda(angulo + larguraFatia / 2, raio);
                  const rotulo = pontoNaRoda(angulo, 78);
                  const cor = cores[indiceFatia % cores.length];
                  const iniciais = morador.nome
                    .trim()
                    .split(/\s+/)
                    .slice(0, 2)
                    .map((parte) => Array.from(parte)[0])
                    .join("")
                    .toUpperCase();
                  return (
                    <G key={morador.id}>
                      {moradores.length > 1 && (
                        <Path
                          d={`M ${centro} ${centro} L ${inicio.x} ${inicio.y} A ${raio} ${raio} 0 0 1 ${fim.x} ${fim.y} Z`}
                          fill={cor}
                          stroke={Caldera.limestone}
                          strokeWidth={2}
                        />
                      )}
                      {moradores.length <= 20 && (
                        <SvgText
                          x={rotulo.x}
                          y={rotulo.y}
                          transform={`rotate(${angulo} ${rotulo.x} ${rotulo.y})`}
                          textAnchor="middle"
                          alignmentBaseline="middle"
                          fill={
                            cor === Caldera.plasmaViolet
                              ? Caldera.chalk
                              : Caldera.obsidian
                          }
                          fontSize={13}
                          fontWeight="bold"
                        >
                          {iniciais}
                        </SvgText>
                      )}
                    </G>
                  );
                })}
                <Circle
                  cx={centro}
                  cy={centro}
                  r={11}
                  fill={Caldera.obsidian}
                />
              </Svg>
            </Animated.View>
            <Svg
              style={StyleSheet.absoluteFill}
              width="100%"
              height="100%"
              viewBox="0 0 240 240"
            >
              <Path d="M 109 2 H 131 L 120 23 Z" fill={Caldera.obsidian} />
            </Svg>
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
  roda: { width: "100%", maxWidth: 240, aspectRatio: 1 },
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
