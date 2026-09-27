import { useEffect, useState } from "react";
import { Modal, StyleSheet, Text, View } from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import Animated, {
  FadeIn,
  FadeInRight,
  FadeOut,
  ReduceMotion,
} from "react-native-reanimated";
import { scheduleOnRN } from "react-native-worklets";

import { MotionPressable } from "@/components/motion-pressable";
import { rotulosEstado } from "@/constants/tarefa";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import type { Morador, Tarefa } from "@/services/tarefas-api";
import { formatarPrazo } from "@/utils/filtros-tarefa";

type Props = {
  tarefa: Tarefa;
  moradores: Morador[];
  usuarioAtualId: string;
  onVoltar: () => void;
  onEditar?: () => void;
  onFinalizar: () => Promise<ResultadoFinalizacao>;
  onContinuar: () => void;
};

export type ResultadoFinalizacao = {
  pontosPossiveis: number;
  pontosObtidos: number;
  saldoAtual: number;
};

function iniciais(nome: string) {
  return nome
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((parte) => parte[0])
    .join("")
    .toUpperCase();
}

export function DetalheTarefa({
  tarefa,
  moradores,
  usuarioAtualId,
  onVoltar,
  onEditar,
  onFinalizar,
  onContinuar,
}: Props) {
  const [finalizando, setFinalizando] = useState(false);
  const [erroFinalizacao, setErroFinalizacao] = useState<string>();
  const [resultado, setResultado] = useState<ResultadoFinalizacao>();
  const [agora, setAgora] = useState(() => Date.now());
  useEffect(() => {
    if (!tarefa.data_inicio) return;
    const espera = new Date(tarefa.data_inicio).getTime() - agora;
    if (espera <= 0) return;
    const temporizador = setTimeout(
      () => setAgora(Date.now()),
      Math.min(espera, 2147483647),
    );
    return () => clearTimeout(temporizador);
  }, [tarefa.data_inicio, agora]);
  const responsaveis = moradores.filter((morador) =>
    tarefa.usuarios_atribuidos.includes(morador.id),
  );
  const finalizada = tarefa.estado_atual === "finalizado";
  const podeFinalizar =
    !finalizada &&
    tarefa.estado_atual !== "nao_feito" &&
    (!tarefa.data_inicio || new Date(tarefa.data_inicio).getTime() <= agora) &&
    tarefa.usuarios_atribuidos.includes(usuarioAtualId);

  async function concluirTarefa() {
    setFinalizando(true);
    setErroFinalizacao(undefined);

    try {
      setResultado(await onFinalizar());
    } catch (erro: unknown) {
      setErroFinalizacao(
        erro instanceof Error
          ? erro.message
          : "Não foi possível finalizar a tarefa.",
      );
    } finally {
      setFinalizando(false);
    }
  }
  const voltarComArraste = Gesture.Pan()
    .activeOffsetX(20)
    .failOffsetY([-20, 20])
    .onEnd((event) => {
      if (event.translationX > 96 || event.velocityX > 700) {
        scheduleOnRN(onVoltar);
      }
    });

  return (
    <GestureDetector gesture={voltarComArraste}>
      <Animated.View
        entering={FadeInRight.duration(260).reduceMotion(ReduceMotion.System)}
        exiting={FadeOut.duration(140).reduceMotion(ReduceMotion.System)}
        style={styles.container}
      >
        <MotionPressable
          accessibilityRole="button"
          onPress={onVoltar}
          style={styles.backButton}
        >
          <Text style={styles.backButtonText}>← Voltar para tarefas</Text>
        </MotionPressable>

        <View style={styles.card}>
          <View style={styles.headingRow}>
            <View style={styles.headingCopy}>
              <Text style={styles.eyebrow}>DETALHE DA TAREFA</Text>
              <Text accessibilityRole="header" style={styles.title}>
                {tarefa.nome.toUpperCase()}
              </Text>
            </View>
            <Animated.View
              key={tarefa.estado_atual}
              entering={FadeIn.duration(180).reduceMotion(ReduceMotion.System)}
              style={[
                styles.statusBadge,
                finalizada && styles.statusBadgeFinished,
              ]}
            >
              <Text
                accessibilityLiveRegion="polite"
                style={[
                  styles.statusText,
                  finalizada && styles.statusTextFinished,
                ]}
              >
                {rotulosEstado[tarefa.estado_atual]}
              </Text>
            </Animated.View>
          </View>

          <Text style={styles.description}>
            {tarefa.descricao || "Sem descrição."}
          </Text>

          <View style={styles.infoGrid}>
            <View style={styles.infoCard}>
              <Text style={styles.infoLabel}>PESO</Text>
              <Text style={styles.infoValue}>{tarefa.peso}</Text>
            </View>
            <View style={styles.infoCard}>
              <Text style={styles.infoLabel}>PRAZO</Text>
              <Text style={styles.infoValue}>
                {formatarPrazo(tarefa.data_fim, tarefa.data_fixa)}
              </Text>
            </View>
            <View style={styles.infoCard}>
              <Text style={styles.infoLabel}>STATUS</Text>
              <Animated.Text
                key={tarefa.estado_atual}
                entering={FadeIn.duration(180).reduceMotion(
                  ReduceMotion.System,
                )}
                style={styles.infoValue}
              >
                {rotulosEstado[tarefa.estado_atual]}
              </Animated.Text>
            </View>
          </View>

          <View style={styles.responsiblesSection}>
            <Text style={styles.sectionTitle}>RESPONSÁVEL</Text>
            <View style={styles.responsibles}>
              {responsaveis.map((morador) => (
                <View key={morador.id} style={styles.responsible}>
                  <View style={styles.avatar}>
                    <Text style={styles.avatarText}>
                      {iniciais(morador.nome)}
                    </Text>
                  </View>
                  <View>
                    <Text style={styles.responsibleName}>{morador.nome}</Text>
                  </View>
                </View>
              ))}
            </View>
          </View>

          {(onEditar || podeFinalizar) && (
            <View style={styles.completionSection}>
              {onEditar && (
                <MotionPressable
                  accessibilityRole="button"
                  onPress={onEditar}
                  style={styles.editButton}
                >
                  <Text style={styles.editButtonText}>Editar tarefa</Text>
                </MotionPressable>
              )}
              {podeFinalizar && (
                <MotionPressable
                  accessibilityRole="button"
                  accessibilityState={{
                    busy: finalizando,
                    disabled: finalizando,
                  }}
                  disabled={finalizando}
                  onPress={concluirTarefa}
                  style={[
                    styles.finishButton,
                    finalizando && styles.finishButtonDisabled,
                  ]}
                >
                  <Text style={styles.finishButtonText}>
                    {finalizando ? "Finalizando..." : "Finalizar tarefa"}
                  </Text>
                </MotionPressable>
              )}
              {erroFinalizacao && (
                <Text accessibilityLiveRegion="polite" style={styles.errorText}>
                  {erroFinalizacao}
                </Text>
              )}
            </View>
          )}
        </View>

        <Modal
          animationType="fade"
          onRequestClose={() => undefined}
          transparent
          visible={Boolean(resultado)}
        >
          <View style={styles.modalBackdrop}>
            <View accessibilityViewIsModal style={styles.modalCard}>
              <Text style={styles.modalEyebrow}>TAREFA CONCLUÍDA</Text>
              <Text accessibilityRole="header" style={styles.modalTitle}>
                PARABÉNS!
              </Text>
              <Text style={styles.modalBody}>
                Você finalizou {tarefa.nome}.
              </Text>

              <View style={styles.scoreCard}>
                <Text style={styles.scoreLabel}>PONTOS POSSÍVEIS</Text>
                <Text style={styles.scoreValue}>
                  {resultado?.pontosPossiveis ?? 0}
                </Text>
                <Text style={styles.scoreLabel}>PONTOS OBTIDOS</Text>
                <Text style={styles.scoreValue}>
                  +{resultado?.pontosObtidos ?? 0}
                </Text>
              </View>

              <Text style={styles.balanceText}>
                Seu saldo atual é de {resultado?.saldoAtual ?? 0} pontos.
              </Text>

              <MotionPressable
                accessibilityRole="button"
                onPress={onContinuar}
                style={styles.continueButton}
              >
                <Text style={styles.continueButtonText}>Continuar</Text>
              </MotionPressable>
            </View>
          </View>
        </Modal>
      </Animated.View>
    </GestureDetector>
  );
}

const styles = StyleSheet.create({
  container: {
    width: "100%",
    maxWidth: 1040,
    alignSelf: "center",
    gap: Spacing.four,
  },
  backButton: {
    alignSelf: "flex-start",
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  backButtonText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  card: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.five,
  },
  headingRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: Spacing.three,
  },
  headingCopy: { flex: 1, minWidth: 240, gap: Spacing.two },
  eyebrow: {
    color: Caldera.ember,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: "500",
  },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 48,
    lineHeight: 48,
    letterSpacing: 0.96,
  },
  statusBadge: {
    backgroundColor: Caldera.sulfur,
    borderRadius: 800,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  statusBadgeFinished: { backgroundColor: Caldera.obsidian },
  statusText: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  statusTextFinished: { color: Caldera.chalk },
  description: {
    color: Caldera.obsidian,
    fontSize: 18,
    lineHeight: 28,
    fontWeight: "500",
    maxWidth: 720,
  },
  infoGrid: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.three },
  infoCard: {
    flexGrow: 1,
    flexBasis: 180,
    minHeight: 120,
    borderRadius: 20,
    backgroundColor: Caldera.pumice,
    padding: Spacing.three,
    justifyContent: "space-between",
    gap: Spacing.two,
  },
  infoLabel: { color: Caldera.obsidian, fontSize: 12, fontWeight: "500" },
  infoValue: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 26,
    lineHeight: 31,
  },
  responsiblesSection: { gap: Spacing.three },
  sectionTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 26,
    lineHeight: 31,
    letterSpacing: 0.52,
  },
  responsibles: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.three },
  responsible: {
    minWidth: 210,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: Caldera.ember,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  responsibleName: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  completionSection: { gap: Spacing.two, alignItems: "flex-start" },
  editButton: {
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
  },
  editButtonText: {
    color: Caldera.obsidian,
    fontSize: 16,
    fontWeight: "500",
  },
  finishButton: {
    backgroundColor: Caldera.ember,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
  },
  finishButtonDisabled: { opacity: 0.6 },
  finishButtonText: {
    color: Caldera.obsidian,
    fontSize: 16,
    fontWeight: "500",
  },
  errorText: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(7, 6, 7, 0.58)",
    alignItems: "center",
    justifyContent: "center",
    padding: Spacing.four,
  },
  modalCard: {
    width: "100%",
    maxWidth: 520,
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.three,
  },
  modalEyebrow: {
    color: Caldera.ember,
    fontSize: 12,
    fontWeight: "500",
  },
  modalTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 48,
    lineHeight: 48,
    letterSpacing: 0.96,
  },
  modalBody: {
    color: Caldera.obsidian,
    fontSize: 18,
    lineHeight: 28,
    fontWeight: "500",
  },
  scoreCard: {
    backgroundColor: Caldera.ember,
    borderRadius: 40,
    padding: Spacing.four,
    gap: Spacing.two,
  },
  scoreLabel: { color: Caldera.chalk, fontSize: 14, fontWeight: "500" },
  scoreValue: {
    color: Caldera.chalk,
    fontFamily: CompactFont,
    fontSize: 64,
    lineHeight: 64,
  },
  balanceText: {
    color: Caldera.obsidian,
    fontSize: 16,
    lineHeight: 25,
    fontWeight: "500",
  },
  continueButton: {
    alignSelf: "flex-start",
    backgroundColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
  },
  continueButtonText: {
    color: Caldera.chalk,
    fontSize: 16,
    fontWeight: "500",
  },
});
