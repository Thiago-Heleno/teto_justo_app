import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { useStore } from "zustand";

import { Acao, styles } from "@/components/gerenciamento-ui";
import { Caldera } from "@/constants/theme";
import { ErroApi } from "@/services/api";
import {
  enviarNotificacaoTeste,
  type TipoNotificacaoTeste,
} from "@/services/notificacoes";
import { sessao } from "@/services/sessao-store";
import { carregarTarefas, type Tarefa } from "@/services/tarefas-api";

const TIPOS: { valor: TipoNotificacaoTeste; nome: string }[] = [
  { valor: "tarefa_atribuida", nome: "Nova tarefa" },
  { valor: "tarefa_vence_hoje", nome: "Vencimento" },
  { valor: "tarefa_atrasada", nome: "Atraso" },
];

export function TestarNotificacoes({ usuarioId }: { usuarioId: string }) {
  const casaId = useStore(sessao, (estado) => estado.casaAtiva?.id);
  const [aberto, setAberto] = useState(false);
  return aberto ? (
    <FormularioTesteNotificacao
      key={`${usuarioId}:${casaId}`}
      usuarioId={usuarioId}
      casaId={casaId}
      onFechar={() => setAberto(false)}
    />
  ) : (
    <Acao texto="Testar notificações" onPress={() => setAberto(true)} />
  );
}

function FormularioTesteNotificacao({
  usuarioId,
  casaId,
  onFechar,
}: {
  usuarioId: string;
  casaId?: string;
  onFechar: () => void;
}) {
  const [tipo, setTipo] = useState<TipoNotificacaoTeste>("tarefa_atribuida");
  const [tarefas, setTarefas] = useState<Tarefa[]>([]);
  const [tarefaId, setTarefaId] = useState("");
  const [carregando, setCarregando] = useState(Boolean(casaId));
  const [enviando, setEnviando] = useState(false);
  const [tentativa, setTentativa] = useState(0);
  const [erro, setErro] = useState<string>();
  const [aviso, setAviso] = useState<string>();
  const emAndamento = useRef(false);

  useEffect(() => {
    if (!casaId) return;
    const controlador = new AbortController();
    carregarTarefas(
      { estado: "todos", prazo: "todos", responsavel: usuarioId },
      controlador.signal,
    )
      .then((lista) => {
        if (!controlador.signal.aborted) setTarefas(lista);
      })
      .catch((falha) => {
        if (!controlador.signal.aborted) {
          setErro(
            falha instanceof ErroApi
              ? falha.message
              : "Não foi possível carregar suas tarefas.",
          );
        }
      })
      .finally(() => {
        if (!controlador.signal.aborted) setCarregando(false);
      });
    return () => controlador.abort();
  }, [casaId, usuarioId, tentativa]);

  async function enviar() {
    if (!tarefaId || carregando || emAndamento.current) return;
    emAndamento.current = true;
    setEnviando(true);
    setErro(undefined);
    setAviso(undefined);
    try {
      const resultado = await enviarNotificacaoTeste(tipo, tarefaId);
      setAviso(
        `Envio solicitado para ${resultado.aceitos} aparelho(s). Confira se o aviso chegou no celular.` +
          (resultado.falhas + resultado.invalidos > 0
            ? " Alguns aparelhos não aceitaram o envio."
            : ""),
      );
    } catch (falha) {
      setErro(
        falha instanceof ErroApi
          ? falha.message
          : "Não foi possível enviar o teste. Verifique sua conexão.",
      );
    } finally {
      emAndamento.current = false;
      setEnviando(false);
    }
  }

  return (
    <View style={local.container}>
      <Acao
        texto="Fechar teste de notificações"
        onPress={onFechar}
        disabled={enviando}
      />
      <View style={styles.card}>
        <Text accessibilityRole="header" style={styles.subtitle}>
          Teste de notificações
        </Text>
        <Text style={styles.text}>
          Envie agora, sem esperar o horário da tarefa. O aviso chegará aos seus
          aparelhos com notificações ativadas no perfil do aplicativo.
        </Text>
        <Text style={styles.label}>Tipo de aviso</Text>
        <View style={styles.row}>
          {TIPOS.map((opcao) => (
            <Pressable
              key={opcao.valor}
              accessibilityRole="radio"
              accessibilityState={{
                checked: tipo === opcao.valor,
                disabled: enviando,
              }}
              disabled={enviando}
              onPress={() => {
                setTipo(opcao.valor);
                setAviso(undefined);
              }}
              style={[styles.button, tipo === opcao.valor && local.selecionado]}
            >
              <Text style={styles.buttonText}>
                {tipo === opcao.valor ? "✓ " : ""}
                {opcao.nome}
              </Text>
            </Pressable>
          ))}
        </View>
        <Text style={styles.label}>Uma tarefa sua nesta casa</Text>
        {!casaId && (
          <Text style={styles.text}>Selecione uma casa para testar.</Text>
        )}
        {carregando && (
          <ActivityIndicator accessibilityLabel="Carregando suas tarefas" />
        )}
        {casaId && !carregando && tarefas.length === 0 && !erro && (
          <Text style={styles.text}>
            Você não tem tarefas atribuídas nesta casa.
          </Text>
        )}
        {tarefas.length > 0 && (
          <ScrollView
            style={local.lista}
            contentContainerStyle={local.container}
            nestedScrollEnabled
          >
            {tarefas.map((tarefa) => (
              <Pressable
                key={tarefa.id}
                accessibilityRole="radio"
                accessibilityState={{
                  checked: tarefaId === tarefa.id,
                  disabled: enviando,
                }}
                disabled={enviando}
                onPress={() => {
                  setTarefaId(tarefa.id);
                  setAviso(undefined);
                }}
                style={[
                  styles.button,
                  tarefaId === tarefa.id && local.selecionado,
                ]}
              >
                <Text style={styles.buttonText}>
                  {tarefaId === tarefa.id ? "✓ " : ""}
                  {tarefa.nome}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        )}
        <Text style={styles.text}>
          {tipo === "tarefa_atribuida"
            ? "O teste não altera a tarefa. Toque no aviso para abrir os detalhes."
            : "O teste não altera prazos ou pontos. A ação Concluir na notificação conclui a tarefa de verdade, seguindo as regras normais."}
        </Text>
        {erro && (
          <Text accessibilityRole="alert" style={styles.error}>
            {erro}
          </Text>
        )}
        {aviso && (
          <Text accessibilityRole="alert" style={styles.text}>
            {aviso}
          </Text>
        )}
        <View style={styles.row}>
          <Acao
            texto={enviando ? "Enviando…" : "Enviar notificação de teste"}
            onPress={() => void enviar()}
            disabled={!tarefaId || carregando || enviando}
          />
          <Acao
            texto="Atualizar tarefas"
            onPress={() => {
              setTarefaId("");
              setTarefas([]);
              setErro(undefined);
              setAviso(undefined);
              setCarregando(true);
              setTentativa((valor) => valor + 1);
            }}
            disabled={!casaId || carregando || enviando}
          />
        </View>
      </View>
    </View>
  );
}

const local = StyleSheet.create({
  container: { gap: 12 },
  lista: { maxHeight: 200 },
  selecionado: { backgroundColor: Caldera.sulfur },
});
