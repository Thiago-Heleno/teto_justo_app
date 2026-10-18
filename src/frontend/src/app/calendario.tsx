import { Link, useFocusEffect } from "expo-router";
import { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useStore } from "zustand";

import { MotionPressable } from "@/components/motion-pressable";
import { rotulosEstado } from "@/constants/tarefa";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import {
  carregarCasa,
  listarMoradoresCasa,
  type Casa,
  type MoradorCasa,
} from "@/services/casas-api";
import { sessao } from "@/services/sessao-store";
import { carregarTarefas, type Tarefa } from "@/services/tarefas-api";
import {
  agruparTarefasAtivas,
  dataNoFuso,
  diasDoMes,
  mudarMes,
} from "@/utils/calendario-tarefas";

type DadosCalendario = {
  casa: Casa;
  moradores: MoradorCasa[];
  tarefas: Tarefa[];
};

function contarTarefas(quantidade: number) {
  return `${quantidade} ${quantidade === 1 ? "tarefa ativa" : "tarefas ativas"}`;
}

export default function CalendarioScreen() {
  const { casaAtiva, token } = useStore(sessao);
  const casaId = casaAtiva?.id;
  const [dados, setDados] = useState<DadosCalendario>();
  const [erro, setErro] = useState<string>();
  const [carregando, setCarregando] = useState(true);
  const [tentativa, setTentativa] = useState(0);

  useFocusEffect(
    useCallback(() => {
      const controlador = new AbortController();
      setCarregando(true);
      setErro(undefined);
      if (casaId && token) {
        void Promise.all([
          carregarCasa(casaId, controlador.signal),
          listarMoradoresCasa(casaId, controlador.signal),
          carregarTarefas(
            { estado: "todos", responsavel: "todos", prazo: "todos" },
            controlador.signal,
          ),
        ])
          .then(([casa, moradores, tarefas]) => {
            if (!controlador.signal.aborted)
              setDados({ casa, moradores, tarefas });
          })
          .catch((falha: unknown) => {
            if (!controlador.signal.aborted) {
              setDados(undefined);
              setErro(
                falha instanceof TypeError
                  ? "Não foi possível conectar. Verifique sua conexão e tente novamente."
                  : falha instanceof Error
                    ? falha.message
                    : "Não foi possível carregar o calendário.",
              );
            }
          })
          .finally(() => {
            if (!controlador.signal.aborted) setCarregando(false);
          });
      }
      return () => controlador.abort();
      // A tentativa permite atualizar sem sair da tela.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [casaId, token, tentativa]),
  );

  return (
    <SafeAreaView style={styles.safe} edges={["top", "left", "right"]}>
      <ScrollView contentContainerStyle={styles.page}>
        <View style={styles.topRow}>
          <Link href="/tarefas" asChild>
            <MotionPressable style={styles.button} accessibilityRole="link">
              <Text style={styles.body}>← Tarefas</Text>
            </MotionPressable>
          </Link>
          <MotionPressable
            accessibilityRole="button"
            accessibilityState={{ disabled: carregando, busy: carregando }}
            disabled={carregando}
            onPress={() => setTentativa((atual) => atual + 1)}
            style={[styles.button, carregando && styles.disabled]}
          >
            <Text style={styles.body}>Atualizar</Text>
          </MotionPressable>
        </View>
        <View style={styles.heading}>
          <Text style={styles.eyebrow}>{casaAtiva?.nome}</Text>
          <Text accessibilityRole="header" style={styles.title}>
            CALENDÁRIO
          </Text>
          <Text style={styles.body}>
            Tarefas pendentes e atrasadas, organizadas pelo prazo.
          </Text>
        </View>
        {carregando && (
          <ActivityIndicator
            color={Caldera.ember}
            accessibilityLabel="Carregando calendário"
          />
        )}
        {erro && (
          <View style={styles.card}>
            <Text accessibilityRole="alert" style={styles.body}>
              {erro}
            </Text>
            <MotionPressable
              accessibilityRole="button"
              onPress={() => setTentativa((atual) => atual + 1)}
              style={styles.button}
            >
              <Text style={styles.body}>Tentar novamente</Text>
            </MotionPressable>
          </View>
        )}
        {dados && dados.casa.id === casaId && (
          <Calendario
            key={`${dados.casa.id}-${dados.casa.timezone}`}
            {...dados}
          />
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function Calendario({ casa, moradores, tarefas }: DadosCalendario) {
  const { width } = useWindowDimensions();
  const compacto = width < 600;
  const hoje = dataNoFuso(new Date(), casa.timezone);
  const [selecionado, setSelecionado] = useState(hoje);
  const mes = selecionado.slice(0, 7);
  const porDia = useMemo(
    () => agruparTarefasAtivas(tarefas, casa.timezone),
    [tarefas, casa.timezone],
  );
  const dias = diasDoMes(mes);
  const tarefasDoDia = porDia.get(selecionado) ?? [];
  const quantidadeMes = dias.reduce(
    (total, dia) => total + (dia ? (porDia.get(dia)?.length ?? 0) : 0),
    0,
  );
  const nomeMes = new Date(`${mes}-01T12:00:00Z`).toLocaleDateString("pt-BR", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
  const formatadorDia = new Intl.DateTimeFormat("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  });

  return (
    <>
      <Text style={styles.caption}>Horários da casa · {casa.timezone}</Text>
      <View style={[styles.layout, width >= 1000 && styles.layoutWide]}>
        <View style={[styles.card, styles.calendar]}>
          <View style={styles.monthHeader}>
            <Text
              accessibilityRole="header"
              accessibilityLiveRegion="polite"
              style={styles.sectionTitle}
            >
              {nomeMes.toUpperCase()}
            </Text>
            <View style={styles.controls}>
              <MotionPressable
                accessibilityRole="button"
                accessibilityLabel="Mês anterior"
                onPress={() => setSelecionado(`${mudarMes(mes, -1)}-01`)}
                style={styles.arrow}
              >
                <Text style={styles.arrowText}>‹</Text>
              </MotionPressable>
              <MotionPressable
                accessibilityRole="button"
                onPress={() =>
                  setSelecionado(dataNoFuso(new Date(), casa.timezone))
                }
                style={styles.button}
              >
                <Text style={styles.body}>Hoje</Text>
              </MotionPressable>
              <MotionPressable
                accessibilityRole="button"
                accessibilityLabel="Próximo mês"
                onPress={() => setSelecionado(`${mudarMes(mes, 1)}-01`)}
                style={styles.arrow}
              >
                <Text style={styles.arrowText}>›</Text>
              </MotionPressable>
            </View>
          </View>
          <Text style={styles.caption}>
            {contarTarefas(quantidadeMes)} neste mês. Selecione um dia.
          </Text>
          <View style={styles.week}>
            {["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"].map((dia) => (
              <Text key={dia} style={styles.weekday}>
                {dia}
              </Text>
            ))}
          </View>
          <View style={styles.grid}>
            {dias.map((dia, indice) => {
              const tarefasData = dia ? (porDia.get(dia) ?? []) : [];
              const selecionada = dia === selecionado;
              return (
                <View key={dia ?? `vazio-${indice}`} style={styles.daySlot}>
                  {dia && (
                    <MotionPressable
                      accessibilityRole="button"
                      accessibilityLabel={`${formatadorDia.format(new Date(`${dia}T12:00:00Z`))}${dia === hoje ? ", hoje" : ""}, ${contarTarefas(tarefasData.length)}`}
                      accessibilityState={{ selected: selecionada }}
                      onPress={() => setSelecionado(dia)}
                      style={[
                        styles.day,
                        compacto && styles.dayCompact,
                        dia === hoje && styles.today,
                        selecionada && styles.selectedDay,
                      ]}
                    >
                      <Text style={styles.dayNumber}>
                        {Number(dia.slice(-2))}
                      </Text>
                      {compacto ? (
                        tarefasData.length > 0 && (
                          <Text style={styles.dayCount}>
                            {tarefasData.length}
                          </Text>
                        )
                      ) : (
                        <>
                          {tarefasData.slice(0, 2).map((tarefa) => (
                            <Text
                              key={tarefa.id}
                              numberOfLines={1}
                              style={styles.dayTask}
                            >
                              {tarefa.nome}
                            </Text>
                          ))}
                          {tarefasData.length > 2 && (
                            <Text style={styles.caption}>
                              +{tarefasData.length - 2}
                            </Text>
                          )}
                        </>
                      )}
                    </MotionPressable>
                  )}
                </View>
              );
            })}
          </View>
        </View>
        <View style={[styles.card, styles.agenda]}>
          <Text style={styles.eyebrow}>TAREFAS DO DIA</Text>
          <Text
            accessibilityRole="header"
            accessibilityLiveRegion="polite"
            style={styles.sectionTitle}
          >
            {formatadorDia.format(new Date(`${selecionado}T12:00:00Z`))}
          </Text>
          {tarefasDoDia.length === 0 ? (
            <Text style={styles.body}>
              {porDia.size === 0
                ? "Nenhuma tarefa ativa na casa."
                : "Nenhuma tarefa ativa para este dia."}
            </Text>
          ) : (
            tarefasDoDia.map((tarefa) => {
              const responsaveis = tarefa.usuarios_atribuidos.map(
                (id) =>
                  moradores.find((morador) => morador.id === id)?.nome ??
                  "Morador indisponível",
              );
              const horario = tarefa.data_fixa
                ? "23:59"
                : new Date(tarefa.data_fim).toLocaleTimeString("pt-BR", {
                    timeZone: casa.timezone,
                    hour: "2-digit",
                    minute: "2-digit",
                    hour12: false,
                  });
              return (
                <View key={tarefa.id} style={styles.task}>
                  <View style={styles.taskHeader}>
                    <Text style={styles.caption}>Até {horario}</Text>
                    <Text
                      style={[
                        styles.status,
                        tarefa.estado_atual === "atrasada" && styles.overdue,
                      ]}
                    >
                      {rotulosEstado[tarefa.estado_atual]}
                    </Text>
                  </View>
                  <Text style={styles.taskName}>{tarefa.nome}</Text>
                  <Text style={styles.body}>
                    Responsável: {responsaveis.join(", ") || "Sem responsável"}
                  </Text>
                  {tarefa.descricao && (
                    <Text style={styles.body}>{tarefa.descricao}</Text>
                  )}
                </View>
              );
            })
          )}
        </View>
      </View>
    </>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Caldera.pumice },
  page: {
    flexGrow: 1,
    width: "100%",
    maxWidth: 1280,
    alignSelf: "center",
    padding: Spacing.three,
    paddingBottom: Spacing.six,
    gap: Spacing.four,
  },
  topRow: { flexDirection: "row", justifyContent: "space-between", gap: 8 },
  heading: { gap: Spacing.two },
  title: {
    fontFamily: CompactFont,
    fontSize: 48,
    lineHeight: 52,
    letterSpacing: 0.96,
    color: Caldera.obsidian,
  },
  eyebrow: { color: Caldera.obsidian, fontSize: 12, fontWeight: "500" },
  body: {
    color: Caldera.obsidian,
    fontSize: 16,
    lineHeight: 24,
    fontWeight: "500",
  },
  caption: { color: Caldera.obsidian, fontSize: 12, lineHeight: 18 },
  button: {
    minHeight: 44,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    borderRadius: 800,
    borderWidth: 1,
    borderColor: Caldera.obsidian,
    alignSelf: "flex-start",
    justifyContent: "center",
  },
  disabled: { opacity: 0.5 },
  layout: { gap: Spacing.four, alignItems: "stretch" },
  layoutWide: { flexDirection: "row", alignItems: "flex-start" },
  card: {
    backgroundColor: Caldera.limestone,
    borderRadius: 24,
    padding: Spacing.three,
    gap: Spacing.three,
  },
  calendar: { flex: 2, minWidth: 0 },
  agenda: { flex: 1, minWidth: 0 },
  monthHeader: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: Spacing.three,
  },
  sectionTitle: {
    fontFamily: CompactFont,
    fontSize: 26,
    lineHeight: 32,
    color: Caldera.obsidian,
    flexShrink: 1,
  },
  controls: { flexDirection: "row", gap: Spacing.two, alignItems: "center" },
  arrow: {
    width: 44,
    height: 44,
    borderRadius: 800,
    backgroundColor: Caldera.pumice,
    alignItems: "center",
    justifyContent: "center",
  },
  arrowText: { color: Caldera.obsidian, fontSize: 28, lineHeight: 32 },
  week: { flexDirection: "row" },
  weekday: {
    flex: 1,
    color: Caldera.obsidian,
    fontSize: 12,
    textAlign: "center",
  },
  grid: { flexDirection: "row", flexWrap: "wrap" },
  daySlot: { width: `${100 / 7}%`, padding: 2 },
  day: {
    minHeight: 118,
    padding: 4,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: Caldera.pumice,
    gap: 4,
  },
  dayCompact: { minHeight: 64, alignItems: "center" },
  today: { borderColor: Caldera.obsidian },
  selectedDay: {
    backgroundColor: Caldera.ember,
    borderColor: Caldera.obsidian,
  },
  dayNumber: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  dayCount: {
    backgroundColor: Caldera.obsidian,
    color: Caldera.chalk,
    borderRadius: 8,
    minWidth: 18,
    textAlign: "center",
    fontSize: 11,
    lineHeight: 16,
    overflow: "hidden",
  },
  dayTask: {
    backgroundColor: Caldera.sulfur,
    borderRadius: 4,
    paddingHorizontal: 3,
    color: Caldera.obsidian,
    fontSize: 12,
    lineHeight: 18,
  },
  task: {
    borderTopWidth: 1,
    borderColor: Caldera.pumice,
    paddingTop: Spacing.three,
    gap: Spacing.two,
  },
  taskHeader: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: Spacing.two,
  },
  taskName: {
    color: Caldera.obsidian,
    fontSize: 18,
    lineHeight: 26,
    fontWeight: "500",
  },
  status: {
    borderRadius: 800,
    paddingHorizontal: Spacing.two,
    paddingVertical: 4,
    backgroundColor: Caldera.sulfur,
    color: Caldera.obsidian,
    fontSize: 12,
    fontWeight: "500",
    overflow: "hidden",
  },
  overdue: { backgroundColor: Caldera.obsidian, color: Caldera.chalk },
});
