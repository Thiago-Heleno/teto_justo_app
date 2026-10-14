import { Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { Caldera, CompactFont } from "@/constants/theme";

export function Acao({
  texto,
  onPress,
  disabled = false,
}: {
  texto: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled }}
      disabled={disabled}
      onPress={onPress}
      style={[styles.button, disabled && { opacity: 0.5 }]}
    >
      <Text style={styles.buttonText}>{texto}</Text>
    </Pressable>
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
            <Acao texto="Cancelar" disabled={ocupado} onPress={onCancelar} />
            <Acao
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
  safe: { flex: 1, backgroundColor: Caldera.limestone },
  page: {
    padding: 24,
    gap: 20,
    width: "100%",
    maxWidth: 900,
    alignSelf: "center",
  },
  title: {
    fontFamily: CompactFont,
    fontSize: 36,
    fontWeight: "800",
    color: Caldera.obsidian,
  },
  subtitle: { fontSize: 22, fontWeight: "700", color: Caldera.obsidian },
  text: { fontSize: 16, lineHeight: 24, color: Caldera.obsidian },
  label: { fontSize: 16, fontWeight: "700", color: Caldera.obsidian },
  card: {
    borderRadius: 24,
    padding: 24,
    gap: 16,
    backgroundColor: Caldera.pumice,
  },
  row: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 12,
    alignItems: "center",
  },
  input: {
    backgroundColor: Caldera.limestone,
    borderWidth: 1,
    borderColor: Caldera.obsidian,
    borderRadius: 12,
    padding: 14,
    color: Caldera.obsidian,
    fontSize: 16,
  },
  button: {
    borderRadius: 24,
    borderWidth: 1,
    borderColor: Caldera.obsidian,
    padding: 14,
    alignSelf: "flex-start",
  },
  buttonText: { color: Caldera.obsidian, fontWeight: "700" },
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
    borderRadius: 24,
    gap: 20,
    backgroundColor: Caldera.limestone,
  },
});
