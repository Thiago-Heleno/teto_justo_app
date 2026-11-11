import { useEffect, useRef, useState } from "react";
import { TriangleAlert } from "lucide-react-native";
import { StyleSheet, Text, useWindowDimensions } from "react-native";

import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, Spacing } from "@/constants/theme";
import {
  reportarTarefa,
  retirarReportTarefa,
  type Tarefa,
} from "@/services/tarefas-api";
import {
  JANELA_REPORTAGEM_MS,
  podeReportarTarefa,
} from "@/utils/pode-reportar-tarefa";

type Props = {
  tarefaId: string;
  concluidaEm: string;
  politica: Tarefa["politica_reclamacao"];
  ehResponsavel: boolean;
  usuarioReclamou: boolean;
  votosAtuais?: number;
  votosPossiveis: number;
  onReportada: (tarefa: Tarefa) => void;
};

export function BotaoReportarTarefa({
  tarefaId,
  concluidaEm,
  politica,
  ehResponsavel,
  usuarioReclamou,
  votosAtuais,
  votosPossiveis,
  onReportada,
}: Props) {
  const { width } = useWindowDimensions();
  const [agora, setAgora] = useState(Date.now);
  const [enviando, setEnviando] = useState(false);
  const requisicaoEmAndamento = useRef(false);
  const [erro, setErro] = useState<string>();
  const permitido = podeReportarTarefa(
    concluidaEm,
    politica,
    ehResponsavel,
    agora,
  );
  useEffect(() => {
    if (!permitido) return;
    const expira = Date.parse(concluidaEm) + JANELA_REPORTAGEM_MS + 1;
    const timer = setTimeout(
      () => setAgora(Date.now()),
      Math.max(0, expira - Date.now()),
    );
    return () => clearTimeout(timer);
  }, [permitido, concluidaEm]);

  if (!permitido) return null;
  async function enviar() {
    if (requisicaoEmAndamento.current) return;
    if (!podeReportarTarefa(concluidaEm, politica, ehResponsavel)) {
      setAgora(Date.now());
      return;
    }
    requisicaoEmAndamento.current = true;
    setEnviando(true);
    setErro(undefined);
    try {
      const acao = usuarioReclamou ? retirarReportTarefa : reportarTarefa;
      const tarefa = await acao(tarefaId, concluidaEm);
      onReportada(tarefa);
    } catch (falha: unknown) {
      setErro(
        falha instanceof Error
          ? falha.message
          : "Não foi possível atualizar seu voto.",
      );
    } finally {
      requisicaoEmAndamento.current = false;
      setEnviando(false);
    }
  }

  const rotulo = enviando
    ? usuarioReclamou
      ? "Retirando..."
      : "Reportando..."
    : usuarioReclamou
      ? "Reportado"
      : "Reportar";
  return (
    <>
      <MotionPressable
        accessibilityRole="button"
        accessibilityLabel={
          votosAtuais === undefined
            ? rotulo
            : `${rotulo}, ${votosAtuais} de ${votosPossiveis} votos possíveis`
        }
        accessibilityState={{
          busy: enviando,
          disabled: enviando,
          selected: usuarioReclamou,
        }}
        accessibilityHint={
          usuarioReclamou ? "Retirar meu voto" : "Reportar tarefa"
        }
        disabled={enviando}
        onPress={enviar}
        style={[
          styles.button,
          width < 600 && styles.small,
          usuarioReclamou && styles.selected,
          enviando && styles.disabled,
        ]}
      >
        <TriangleAlert
          color={usuarioReclamou ? Caldera.chalk : Caldera.obsidian}
          size={18}
          strokeWidth={2.2}
        />
        <Text style={[styles.label, usuarioReclamou && styles.selectedLabel]}>
          {rotulo}
          {votosAtuais !== undefined && ` · ${votosAtuais}/${votosPossiveis}`}
        </Text>
      </MotionPressable>
      {erro && (
        <Text accessibilityLiveRegion="polite" style={styles.error}>
          {erro}
        </Text>
      )}
    </>
  );
}

const styles = StyleSheet.create({
  button: {
    alignSelf: "flex-start",
    maxWidth: "100%",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: Spacing.two,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
  },
  small: { alignSelf: "stretch" },
  selected: { backgroundColor: Caldera.ember, borderColor: Caldera.ember },
  selectedLabel: { color: Caldera.chalk },
  disabled: { opacity: 0.6 },
  label: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  error: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
});
