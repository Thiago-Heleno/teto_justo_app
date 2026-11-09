import { Pressable, StyleSheet, Text, View } from "react-native";

import { Caldera } from "@/constants/theme";
import type { PoliticaReclamacao } from "@/services/casas-api";

const opcoes = [
  {
    value: "nenhuma",
    title: "Sem reclamações",
    description: "Esta casa não utiliza o sistema de reclamações de tarefas.",
  },
  {
    value: "uma_reclamacao",
    title: "A cada reclamação",
    description:
      "O responsável recebe um aviso a cada reclamação. A tarefa não é reaberta.",
  },
  {
    value: "votacao",
    title: "Somente na reabertura",
    description:
      "O responsável só recebe um aviso quando a tarefa é reaberta por atingir o mínimo de reclamações.",
  },
] as const;

export function SeletorPoliticaReclamacao({
  valor,
  editavel,
  onChange,
}: {
  valor: PoliticaReclamacao;
  editavel: boolean;
  onChange: (valor: PoliticaReclamacao) => void;
}) {
  return (
    <View
      accessibilityRole="radiogroup"
      accessibilityLabel="Política de reclamações"
      style={styles.field}
    >
      <Text style={styles.label}>Política de reclamações</Text>
      <Text style={styles.optionDescription}>
        Defina como as reclamações serão tratadas e quando o responsável pela
        tarefa receberá notificações.
      </Text>
      {opcoes.map((opcao) => {
        const selecionada = valor === opcao.value;
        return (
          <Pressable
            key={opcao.value}
            accessibilityRole="radio"
            accessibilityState={{
              checked: selecionada,
              disabled: !editavel,
            }}
            disabled={!editavel}
            onPress={() => onChange(opcao.value)}
            style={[
              styles.policyOption,
              selecionada && styles.policyOptionSelected,
              !editavel && styles.dimmed,
            ]}
          >
            <View style={styles.policyHeading}>
              <View style={[styles.radio, selecionada && styles.radioSelected]}>
                {selecionada && <View style={styles.radioDot} />}
              </View>
              <Text style={styles.policyTitle}>{opcao.title}</Text>
            </View>
            <Text style={styles.optionDescription}>{opcao.description}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  field: { gap: 8 },
  optionDescription: { color: "#555", fontSize: 14, lineHeight: 21 },
  policyOption: {
    borderWidth: 1,
    borderColor: Caldera.pumice,
    borderRadius: 16,
    padding: 16,
    gap: 8,
    backgroundColor: Caldera.chalk,
  },
  policyOptionSelected: {
    borderColor: Caldera.ember,
    borderWidth: 2,
  },
  policyHeading: { flexDirection: "row", alignItems: "center", gap: 10 },
  policyTitle: { color: Caldera.obsidian, fontWeight: "700", fontSize: 15 },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    alignItems: "center",
    justifyContent: "center",
  },
  radioSelected: { borderColor: Caldera.ember },
  radioDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: Caldera.ember,
  },
  label: { color: Caldera.obsidian, fontWeight: "600", fontSize: 16 },
  dimmed: { opacity: 0.6 },
});
