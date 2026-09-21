import { useState } from "react";
import {
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { DetalheTarefa } from "@/components/detalhe-tarefa";
import { opcoesEstadoTarefa, rotulosEstado } from "@/constants/tarefa";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import {
  casaDemonstracao,
  moradoresDemonstracao,
  tarefasDemonstracao,
  usuarioDemonstracaoId,
} from "@/data/tarefa-demonstracao";
import {
  filtrarTarefas,
  formatarPrazo,
  type FiltrosTarefa,
  type FiltroPrazo,
} from "@/utils/filtros-tarefa";

type FilterPillProps = {
  label: string;
  selected: boolean;
  onPress: () => void;
};

function FilterPill({ label, selected, onPress }: FilterPillProps) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected }}
      onPress={onPress}
      style={({ pressed }) => [
        styles.filterPill,
        selected && styles.filterPillSelected,
        pressed && styles.pressed,
      ]}
    >
      <Text style={styles.filterPillText}>{label}</Text>
    </Pressable>
  );
}

const opcoesPrazo: { valor: FiltroPrazo; rotulo: string }[] = [
  { valor: "todos", rotulo: "Qualquer prazo" },
  { valor: "hoje", rotulo: "Hoje" },
  { valor: "sete_dias", rotulo: "Próximos 7 dias" },
  { valor: "atrasadas", rotulo: "Prazo vencido" },
];

export default function TarefasScreen() {
  const [tarefas, setTarefas] = useState(() =>
    tarefasDemonstracao.map((tarefa) => ({ ...tarefa })),
  );
  const [filtros, setFiltros] = useState<FiltrosTarefa>({
    estado: "todos",
    responsavel: "todos",
    prazo: "todos",
  });
  const [tarefaSelecionadaId, setTarefaSelecionadaId] = useState<string>();

  const tarefaSelecionada = tarefas.find(
    (tarefa) => tarefa.id === tarefaSelecionadaId,
  );
  const tarefasFiltradas = filtrarTarefas(tarefas, filtros);
  const tarefasEmAberto = tarefas.filter(
    (tarefa) => tarefa.estado_atual !== "finalizado",
  ).length;

  function concluirTarefa(id: string) {
    setTarefas((atuais) =>
      atuais.map((tarefa) =>
        tarefa.id === id ? { ...tarefa, estado_atual: "finalizado" } : tarefa,
      ),
    );
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
      <ScrollView contentContainerStyle={styles.page}>
        {tarefaSelecionada ? (
          <DetalheTarefa
            tarefa={tarefaSelecionada}
            moradores={moradoresDemonstracao}
            usuarioAtualId={usuarioDemonstracaoId}
            onVoltar={() => setTarefaSelecionadaId(undefined)}
            onConcluir={concluirTarefa}
          />
        ) : (
          <View style={styles.content}>
            <View style={styles.hero}>
              <View style={styles.heroCopy}>
                <Text style={styles.houseName}>{casaDemonstracao.nome}</Text>
                <Text accessibilityRole="header" style={styles.title}>
                  TAREFAS DA CASA
                </Text>
                <Text style={styles.subtitle}>
                  Organize o combinado, veja quem ficou responsável e acompanhe
                  cada prazo.
                </Text>
              </View>
              <View style={styles.statCard}>
                <Text style={styles.statLabel}>EM ABERTO</Text>
                <Text style={styles.statValue}>{tarefasEmAberto}</Text>
                <Text style={styles.statCaption}>tarefas pedem atenção</Text>
              </View>
            </View>

            <View style={styles.filtersCard}>
              <View style={styles.filterGroup}>
                <Text style={styles.filterLabel}>STATUS</Text>
                <View style={styles.filterOptions}>
                  <FilterPill
                    label="Todos"
                    selected={filtros.estado === "todos"}
                    onPress={() =>
                      setFiltros((atuais) => ({ ...atuais, estado: "todos" }))
                    }
                  />
                  {opcoesEstadoTarefa.map((opcao) => (
                    <FilterPill
                      key={opcao.valor}
                      label={opcao.rotulo}
                      selected={filtros.estado === opcao.valor}
                      onPress={() =>
                        setFiltros((atuais) => ({
                          ...atuais,
                          estado: opcao.valor,
                        }))
                      }
                    />
                  ))}
                </View>
              </View>

              <View style={styles.filterGroup}>
                <Text style={styles.filterLabel}>RESPONSÁVEL</Text>
                <View style={styles.filterOptions}>
                  <FilterPill
                    label="Todos"
                    selected={filtros.responsavel === "todos"}
                    onPress={() =>
                      setFiltros((atuais) => ({
                        ...atuais,
                        responsavel: "todos",
                      }))
                    }
                  />
                  {moradoresDemonstracao.map((morador) => (
                    <FilterPill
                      key={morador.id}
                      label={
                        morador.id === usuarioDemonstracaoId
                          ? `${morador.nome} (você)`
                          : morador.nome
                      }
                      selected={filtros.responsavel === morador.id}
                      onPress={() =>
                        setFiltros((atuais) => ({
                          ...atuais,
                          responsavel: morador.id,
                        }))
                      }
                    />
                  ))}
                </View>
              </View>

              <View style={styles.filterGroup}>
                <Text style={styles.filterLabel}>PRAZO</Text>
                <View style={styles.filterOptions}>
                  {opcoesPrazo.map((opcao) => (
                    <FilterPill
                      key={opcao.valor}
                      label={opcao.rotulo}
                      selected={filtros.prazo === opcao.valor}
                      onPress={() =>
                        setFiltros((atuais) => ({
                          ...atuais,
                          prazo: opcao.valor,
                        }))
                      }
                    />
                  ))}
                </View>
              </View>
            </View>

            <View style={styles.listHeading}>
              <Text style={styles.sectionTitle}>TAREFAS</Text>
              <Text accessibilityLiveRegion="polite" style={styles.resultCount}>
                {tarefasFiltradas.length} resultado(s)
              </Text>
            </View>

            {tarefasFiltradas.length ? (
              <View style={styles.taskGrid}>
                {tarefasFiltradas.map((tarefa) => {
                  const responsaveis = moradoresDemonstracao.filter((morador) =>
                    tarefa.usuarios_atribuidos.includes(morador.id),
                  );
                  const finalizada = tarefa.estado_atual === "finalizado";

                  return (
                    <Pressable
                      key={tarefa.id}
                      accessibilityRole="button"
                      accessibilityLabel={`Ver detalhes de ${tarefa.nome}`}
                      onPress={() => setTarefaSelecionadaId(tarefa.id)}
                      style={({ pressed }) => [
                        styles.taskCard,
                        pressed && styles.pressed,
                      ]}
                    >
                      <View style={styles.taskTopRow}>
                        <View
                          style={[
                            styles.statusBadge,
                            finalizada && styles.statusBadgeFinished,
                          ]}
                        >
                          <Text
                            style={[
                              styles.statusText,
                              finalizada && styles.statusTextFinished,
                            ]}
                          >
                            {rotulosEstado[tarefa.estado_atual]}
                          </Text>
                        </View>
                        <Text style={styles.weight}>PESO {tarefa.peso}</Text>
                      </View>

                      <Text style={styles.taskTitle}>
                        {tarefa.nome.toUpperCase()}
                      </Text>
                      <Text numberOfLines={2} style={styles.taskDescription}>
                        {tarefa.descricao}
                      </Text>

                      <View style={styles.taskMeta}>
                        <View>
                          <Text style={styles.metaLabel}>PRAZO</Text>
                          <Text style={styles.metaValue}>
                            {formatarPrazo(tarefa.data_fim)}
                          </Text>
                        </View>
                        <View style={styles.avatars}>
                          {responsaveis.map((morador) => (
                            <View key={morador.id} style={styles.avatar}>
                              <Text style={styles.avatarText}>
                                {morador.iniciais}
                              </Text>
                            </View>
                          ))}
                        </View>
                      </View>

                      <Text style={styles.detailsLink}>Ver detalhes →</Text>
                    </Pressable>
                  );
                })}
              </View>
            ) : (
              <View style={styles.emptyCard}>
                <Text style={styles.emptyTitle}>NENHUMA TAREFA POR AQUI</Text>
                <Text style={styles.emptyText}>
                  Ajuste os filtros para ver outras tarefas da casa.
                </Text>
              </View>
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Caldera.pumice },
  page: {
    flexGrow: 1,
    paddingHorizontal: Spacing.four,
    paddingTop: Platform.OS === "web" ? 112 : Spacing.four,
    paddingBottom: Spacing.six,
  },
  content: {
    width: "100%",
    maxWidth: 1280,
    alignSelf: "center",
    gap: 40,
  },
  hero: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "stretch",
    gap: Spacing.four,
  },
  heroCopy: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 320,
    justifyContent: "center",
    gap: Spacing.three,
  },
  houseName: { color: Caldera.ember, fontSize: 14, fontWeight: "500" },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 64,
    lineHeight: 62,
    letterSpacing: 1.28,
  },
  subtitle: {
    color: Caldera.obsidian,
    fontSize: 18,
    lineHeight: 28,
    fontWeight: "500",
    maxWidth: 620,
  },
  statCard: {
    flexGrow: 1,
    flexBasis: 240,
    maxWidth: 360,
    minHeight: 210,
    borderRadius: 40,
    backgroundColor: Caldera.ember,
    padding: Spacing.five,
    justifyContent: "space-between",
  },
  statLabel: { color: Caldera.chalk, fontSize: 14, fontWeight: "500" },
  statValue: {
    color: Caldera.chalk,
    fontFamily: CompactFont,
    fontSize: 80,
    lineHeight: 82,
  },
  statCaption: { color: Caldera.chalk, fontSize: 16, fontWeight: "500" },
  filtersCard: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.four,
  },
  filterGroup: { gap: 12 },
  filterLabel: { color: Caldera.obsidian, fontSize: 12, fontWeight: "500" },
  filterOptions: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  filterPill: {
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.three,
    paddingVertical: 10,
  },
  filterPillSelected: { backgroundColor: Caldera.ember },
  filterPillText: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  listHeading: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    gap: Spacing.three,
  },
  sectionTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 48,
    lineHeight: 48,
    letterSpacing: 0.96,
  },
  resultCount: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  taskGrid: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.four },
  taskCard: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 320,
    minHeight: 330,
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.three,
  },
  taskTopRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: Spacing.two,
  },
  statusBadge: {
    backgroundColor: Caldera.sulfur,
    borderRadius: 800,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  statusBadgeFinished: { backgroundColor: Caldera.obsidian },
  statusText: { color: Caldera.obsidian, fontSize: 12, fontWeight: "500" },
  statusTextFinished: { color: Caldera.chalk },
  weight: { color: Caldera.obsidian, fontSize: 12, fontWeight: "500" },
  taskTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 32,
    lineHeight: 34,
    letterSpacing: 0.64,
  },
  taskDescription: {
    color: Caldera.obsidian,
    fontSize: 16,
    lineHeight: 24,
    fontWeight: "500",
  },
  taskMeta: {
    marginTop: "auto",
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    gap: Spacing.three,
  },
  metaLabel: {
    color: Caldera.obsidian,
    fontSize: 12,
    lineHeight: 16,
    fontWeight: "500",
  },
  metaValue: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  avatars: { flexDirection: "row" },
  avatar: {
    width: 36,
    height: 36,
    marginLeft: -6,
    borderRadius: 18,
    borderWidth: 2,
    borderColor: Caldera.limestone,
    backgroundColor: Caldera.ember,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: { color: Caldera.obsidian, fontSize: 11, fontWeight: "500" },
  detailsLink: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  emptyCard: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: 40,
    gap: Spacing.two,
  },
  emptyTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 32,
    lineHeight: 36,
  },
  emptyText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  pressed: { opacity: 0.7 },
});
