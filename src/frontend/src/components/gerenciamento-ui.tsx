import { Check, X, type LucideIcon } from "lucide-react-native";
import { Modal, StyleSheet, Text, View } from "react-native";

import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";

export function Acao({
  texto,
  icone: Icone,
  onPress,
  disabled = false,
  variante = "secundaria",
}: {
  texto: string;
  icone?: LucideIcon;
  onPress: () => void;
  disabled?: boolean;
  variante?: "primaria" | "secundaria";
}) {
  return (
    <MotionPressable
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={StyleSheet.flatten([
        styles.button,
        variante === "primaria" && styles.primaryButton,
        disabled && { opacity: 0.5 },
      ])}
    >
      {Icone && <Icone color={Caldera.obsidian} size={18} />}
      <Text style={styles.buttonText}>{texto}</Text>
    </MotionPressable>
  );
}
export function ConfirmarAcao({
  mensagem,
  ocupado,
  onCancelar,
  onConfirmar,
}: {
  mensagem: string | null;
  ocupado: boolean;
  onCancelar: () => void;
  onConfirmar: () => void;
}) {
  return (
    <Modal
      visible={Boolean(mensagem)}
      transparent
      animationType="fade"
      onRequestClose={() => {
        if (!ocupado) onCancelar();
      }}
    >
      <View style={styles.backdrop}>
        <View accessibilityViewIsModal style={styles.modal}>
          <Text style={styles.text}>{mensagem}</Text>
          <View style={styles.row}>
            <Acao
              texto="Cancelar"
              icone={X}
              disabled={ocupado}
              onPress={onCancelar}
            />
            <Acao
              icone={Check}
              texto={ocupado ? "Aguarde…" : "Confirmar"}
              disabled={ocupado}
              onPress={onConfirmar}
            />
          </View>
        </View>
      </View>
    </Modal>
  );
}
export const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Caldera.pumice },
  page: {
    flexGrow: 1,
    padding: Spacing.four,
    paddingBottom: Spacing.six,
  },
  pageSmall: {
    padding: Spacing.three,
    paddingBottom: Spacing.five,
  },
  content: {
    width: "100%",
    maxWidth: 1280,
    alignSelf: "center",
    gap: Spacing.four,
  },
  heading: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    alignItems: "flex-end",
    gap: Spacing.three,
  },
  headingCopy: {
    flexShrink: 1,
    gap: Spacing.two,
  },
  eyebrow: {
    color: Caldera.ember,
    fontSize: 14,
    fontWeight: "500",
  },
  title: {
    fontFamily: CompactFont,
    fontSize: 56,
    lineHeight: 60,
    letterSpacing: 1.12,
    color: Caldera.obsidian,
  },
  titleSmall: {
    fontSize: 36,
    lineHeight: 40,
    letterSpacing: 0.72,
  },
  subtitle: {
    fontFamily: CompactFont,
    fontSize: 28,
    lineHeight: 32,
    color: Caldera.obsidian,
  },
  text: { fontSize: 16, lineHeight: 24, color: Caldera.obsidian },
  label: { fontSize: 16, fontWeight: "700", color: Caldera.obsidian },
  card: {
    borderRadius: 32,
    padding: Spacing.four,
    gap: Spacing.three,
    backgroundColor: Caldera.limestone,
  },
  row: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
    alignItems: "center",
  },
  input: {
    backgroundColor: Caldera.pumice,
    borderWidth: 1,
    borderColor: Caldera.obsidian,
    borderRadius: 16,
    padding: 14,
    color: Caldera.obsidian,
    fontSize: 16,
  },
  button: {
    borderRadius: 800,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
    alignSelf: "flex-start",
    alignItems: "center",
    flexDirection: "row",
    gap: Spacing.two,
  },
  primaryButton: {
    backgroundColor: Caldera.ember,
    borderColor: Caldera.ember,
  },
  buttonText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  error: { color: "#a32316", fontSize: 16 },
  backdrop: {
    flex: 1,
    backgroundColor: "#0008",
    justifyContent: "center",
    padding: 24,
  },
  modal: {
    alignSelf: "center",
    width: "100%",
    maxWidth: 560,
    padding: 24,
    borderRadius: 32,
    gap: 20,
    backgroundColor: Caldera.limestone,
  },
});
