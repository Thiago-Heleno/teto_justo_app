import { useEffect, useState } from "react";
import { TriangleAlert } from "lucide-react-native";
import { StyleSheet, Text, useWindowDimensions } from "react-native";

import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, Spacing } from "@/constants/theme";
import { reportarTarefa, type Tarefa } from "@/services/tarefas-api";
import {
  JANELA_REPORTAGEM_MS,
  podeReportarTarefa,
} from "@/utils/pode-reportar-tarefa";

type Props = {
  tarefaId: string;
  concluidaEm: string;
  politica: Tarefa["politica_reclamacao"];
  ehResponsavel: boolean;
  votosAtuais?: number;
  votosPossiveis: number;
  onReportada: (tarefa: Tarefa) => void;
};

export function BotaoReportarTarefa({
  tarefaId,
  concluidaEm,
  politica,
  ehResponsavel,
  votosAtuais,
  votosPossiveis,
  onReportada,
}: Props) {
  const { width } = useWindowDimensions();
  const [agora, setAgora] = useState(Date.now);
  const [estado, setEstado] = useState<"pronto" | "enviando" | "reportado">(
    "pronto",
  );
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
    if (estado !== "pronto") return;
    if (!podeReportarTarefa(concluidaEm, politica, ehResponsavel)) {
      setAgora(Date.now());
      return;
    }
    setEstado("enviando");
    setErro(undefined);
    try {
      const tarefa = await reportarTarefa(tarefaId, concluidaEm);
      setEstado("reportado");
      onReportada(tarefa);
    } catch (falha: unknown) {
      setEstado("pronto");
      setErro(
        falha instanceof Error
          ? falha.message
          : "Não foi possível reportar a tarefa.",
      );
    }
  }

  const rotulo = {
    pronto: "Reportar",
    enviando: "Reportando...",
    reportado: "Reportado",
  }[estado];
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
          busy: estado === "enviando",
          disabled: estado !== "pronto",
        }}
        disabled={estado !== "pronto"}
        onPress={enviar}
        style={[
          styles.button,
          width < 600 && styles.small,
          estado !== "pronto" && styles.disabled,
        ]}
      >
        <TriangleAlert color={Caldera.ember} size={18} strokeWidth={2.2} />
        <Text style={styles.label}>
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
    borderColor: Caldera.ember,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
  },
  small: { alignSelf: "stretch" },
  disabled: { opacity: 0.6 },
  label: { color: Caldera.ember, fontSize: 16, fontWeight: "500" },
  error: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
});
