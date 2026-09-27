import { useState } from "react";
import { StyleSheet, Text, TextInput, View } from "react-native";
import Animated, { FadeInRight, ReduceMotion } from "react-native-reanimated";

import { MotionPressable } from "@/components/motion-pressable";
import { pesosTarefa, prazosTarefa, type PesoTarefa, type PrazoDias } from "@/constants/tarefa";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import type { Morador, Tarefa, TarefaAtualizar } from "@/services/tarefas-api";
import {
  prepararEdicaoTarefa,
  type ErrosEdicaoTarefa,
} from "@/utils/edicao-tarefa";

type Props = {
  tarefa: Tarefa;
  moradores: Morador[];
  onCancelar: () => void;
  onSalvar: (dados: TarefaAtualizar) => Promise<void>;
};

function ErroCampo({ mensagem }: { mensagem?: string }) {
  if (!mensagem) return null;
  return (
    <Text accessibilityLiveRegion="polite" style={styles.errorText}>
      Atenção: {mensagem}
    </Text>
  );
}

export function EditarTarefa({
  tarefa,
  moradores,
  onCancelar,
  onSalvar,
}: Props) {
  const [nome, setNome] = useState(tarefa.nome);
  const [descricao, setDescricao] = useState(tarefa.descricao ?? "");
  const [peso, setPeso] = useState<PesoTarefa>(tarefa.peso as PesoTarefa);
  const [prazoDias, setPrazoDias] = useState<PrazoDias | null>((tarefa.prazo_dias ?? null) as PrazoDias | null);
  const [atrasoMaximo, setAtrasoMaximo] = useState(tarefa.atraso_maximo);
  const [dataFixa, setDataFixa] = useState(tarefa.data_fixa ?? "");
  const [responsavel, setResponsavel] = useState(
    tarefa.usuarios_atribuidos[0] ?? "",
  );
  const [erros, setErros] = useState<ErrosEdicaoTarefa>({});
  const [salvando, setSalvando] = useState(false);
  const [erroEnvio, setErroEnvio] = useState<string>();

  async function salvar() {
    const resultado = prepararEdicaoTarefa(
      { nome, descricao, peso, prazoDias, atrasoMaximo, dataFixa, responsavel },
      tarefa,
      moradores,
    );
    setErros(resultado.erros);
    if (!resultado.dados) return;

    setSalvando(true);
    setErroEnvio(undefined);
    try {
      await onSalvar(resultado.dados);
    } catch (erro: unknown) {
      setErroEnvio(
        erro instanceof Error
          ? erro.message
          : "Não foi possível editar a tarefa.",
      );
    } finally {
      setSalvando(false);
    }
  }

  return (
    <Animated.View
      entering={FadeInRight.duration(260).reduceMotion(ReduceMotion.System)}
      style={styles.container}
    >
      <Text style={styles.eyebrow}>EDIÇÃO DE TAREFA</Text>
      <Text accessibilityRole="header" style={styles.title}>
        EDITAR TAREFA
      </Text>
      <Text style={styles.help}>Campos com * são obrigatórios.</Text>

      <View style={styles.card}>
        <View style={styles.field}>
          <Text style={styles.label}>Nome *</Text>
          <TextInput
            accessibilityLabel="Nome da tarefa, obrigatório"
            onChangeText={(valor) => {
              setNome(valor);
              setErros((atuais) => ({ ...atuais, nome: undefined }));
            }}
            placeholderTextColor={Caldera.obsidian}
            selectionColor={Caldera.ember}
            style={styles.input}
            value={nome}
          />
          <ErroCampo mensagem={erros.nome} />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Descrição</Text>
          <TextInput
            accessibilityLabel="Descrição da tarefa"
            multiline
            onChangeText={setDescricao}
            selectionColor={Caldera.ember}
            style={[styles.input, styles.description]}
            textAlignVertical="top"
            value={descricao}
          />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Peso *</Text>
          <View accessibilityRole="radiogroup" style={styles.options}>
            {pesosTarefa.map((opcao) => (
              <MotionPressable
                accessibilityRole="radio"
                accessibilityState={{ checked: peso === opcao }}
                key={opcao}
                onPress={() => setPeso(opcao)}
                style={[styles.option, peso === opcao && styles.selected]}
              >
                <Text style={styles.optionText}>{opcao}</Text>
              </MotionPressable>
            ))}
          </View>
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Prazo *</Text>
          <View accessibilityRole="radiogroup" style={styles.options}>
            {prazosTarefa.map((opcao) => (
              <MotionPressable
                accessibilityRole="radio"
                accessibilityState={{ checked: prazoDias === opcao }}
                key={opcao}
                onPress={() => setPrazoDias(opcao)}
                style={[styles.option, prazoDias === opcao && styles.selected]}
              >
                <Text style={styles.optionText}>{opcao} {opcao === 1 ? "dia" : "dias"}</Text>
              </MotionPressable>
            ))}
          </View>
          <ErroCampo mensagem={erros.prazoDias} />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Tolerância após o prazo</Text>
          <View accessibilityRole="radiogroup" style={styles.options}>
            {prazosTarefa.map((opcao) => (
              <MotionPressable
                accessibilityRole="radio"
                accessibilityState={{ checked: atrasoMaximo === opcao }}
                key={opcao}
                onPress={() => setAtrasoMaximo(opcao)}
                style={[styles.option, atrasoMaximo === opcao && styles.selected]}
              >
                <Text style={styles.optionText}>{opcao} {opcao === 1 ? "dia" : "dias"}</Text>
              </MotionPressable>
            ))}
          </View>
          <ErroCampo mensagem={erros.atrasoMaximo} />
        </View>

        {tarefa.tipo === "unitaria" && tarefa.modo_prazo === "dia_fixo" && (
          <View style={styles.field}>
            <Text style={styles.label}>Data do vencimento</Text>
            <Text style={styles.help}>Use o formato AAAA-MM-DD.</Text>
            <TextInput
              accessibilityLabel="Data do vencimento no formato ano, mês e dia"
              autoCapitalize="none"
              inputMode="numeric"
              onChangeText={setDataFixa}
              placeholder="2026-10-01"
              placeholderTextColor={Caldera.obsidian}
              selectionColor={Caldera.ember}
              style={styles.input}
              value={dataFixa}
            />
            <ErroCampo mensagem={erros.dataFixa} />
          </View>
        )}

        <View style={styles.field}>
          <Text style={styles.label}>Responsável *</Text>
          <View accessibilityRole="radiogroup" style={styles.options}>
            {moradores.map((morador) => (
              <MotionPressable
                accessibilityRole="radio"
                accessibilityState={{ checked: responsavel === morador.id }}
                key={morador.id}
                onPress={() => {
                  setResponsavel(morador.id);
                  setErros((atuais) => ({ ...atuais, responsavel: undefined }));
                }}
                style={[
                  styles.option,
                  responsavel === morador.id && styles.selected,
                ]}
              >
                <Text style={styles.optionText}>{morador.nome}</Text>
              </MotionPressable>
            ))}
          </View>
          <ErroCampo mensagem={erros.responsavel} />
        </View>

        {erroEnvio && (
          <Text accessibilityLiveRegion="polite" style={styles.errorText}>
            {erroEnvio}
          </Text>
        )}

        <View style={styles.actions}>
          <MotionPressable
            accessibilityRole="button"
            disabled={salvando}
            onPress={() => void salvar()}
            style={[styles.saveButton, salvando && styles.disabled]}
          >
            <Text style={styles.saveText}>
              {salvando ? "Salvando..." : "Salvar alterações"}
            </Text>
          </MotionPressable>
          <MotionPressable
            accessibilityRole="button"
            disabled={salvando}
            onPress={onCancelar}
            style={styles.cancelButton}
          >
            <Text style={styles.cancelText}>Cancelar</Text>
          </MotionPressable>
        </View>
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: "100%",
    maxWidth: 1040,
    alignSelf: "center",
    gap: Spacing.three,
  },
  eyebrow: { color: Caldera.ember, fontSize: 12, fontWeight: "500" },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 48,
    lineHeight: 48,
    letterSpacing: 0.96,
  },
  help: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  card: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.four,
  },
  field: { gap: Spacing.two },
  label: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  input: {
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 20,
    color: Caldera.obsidian,
    fontSize: 16,
    fontWeight: "500",
    paddingHorizontal: Spacing.three,
    paddingVertical: 12,
  },
  description: { minHeight: 112 },
  options: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  option: {
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.three,
    paddingVertical: 10,
  },
  selected: { backgroundColor: Caldera.ember },
  optionText: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  errorText: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  saveButton: {
    backgroundColor: Caldera.ember,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
  },
  disabled: { opacity: 0.6 },
  saveText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  cancelButton: {
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
  },
  cancelText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
});
