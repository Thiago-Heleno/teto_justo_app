import { useState } from "react";
import { StyleSheet, Text, TextInput, View } from "react-native";
import Animated, { FadeInRight, ReduceMotion } from "react-native-reanimated";

import { MotionPressable } from "@/components/motion-pressable";
import { pesosTarefa, type PesoTarefa } from "@/constants/tarefa";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import type { Morador, Tarefa, TarefaAtualizar } from "@/services/tarefas-api";
import {
  dataTarefaParaCampo,
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
  const [dataFim, setDataFim] = useState(dataTarefaParaCampo(tarefa.data_fim));
  const [responsavel, setResponsavel] = useState(
    tarefa.usuarios_atribuidos[0] ?? "",
  );
  const [erros, setErros] = useState<ErrosEdicaoTarefa>({});
  const [salvando, setSalvando] = useState(false);
  const [erroEnvio, setErroEnvio] = useState<string>();

  async function salvar() {
    const resultado = prepararEdicaoTarefa(
      { nome, descricao, peso, dataFim, responsavel },
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