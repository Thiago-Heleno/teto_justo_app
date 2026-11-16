import { Link } from "expo-router";
import {
  ArrowLeft,
  Check,
  ChevronDown,
  ChevronUp,
  Pencil,
  Plus,
  RefreshCw,
  ShoppingBasket,
  Trash2,
} from "lucide-react-native";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useStore } from "zustand";

import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import {
  criarItemCompra,
  criarListaCompra,
  definirItemComprado,
  editarItemCompra,
  excluirItemCompra,
  excluirListaCompra,
  listarItensCompra,
  listarListasCompra,
  renomearListaCompra,
  type ItemCompra,
  type ListaCompra,
} from "@/services/lista-compras-api";
import { sessao } from "@/services/sessao-store";
import { carregarUsuarioAtual } from "@/services/tarefas-api";
import { agruparItensCompra, quantidadeValida } from "@/utils/lista-compras";

type Dialogo =
  | { tipo: "lista"; lista?: ListaCompra }
  | { tipo: "item"; item: ItemCompra }
  | { tipo: "excluir-lista"; lista: ListaCompra }
  | { tipo: "excluir-item"; item: ItemCompra };

function mensagemErro(erro: unknown) {
  return erro instanceof Error
    ? erro.message
    : "Não foi possível concluir a operação.";
}

export default function ListaComprasScreen() {
  const { width } = useWindowDimensions();
  const compacto = width < 780;
  const casa = useStore(sessao, (estado) => estado.casaAtiva);
  const casaId = casa?.id;
  const [usuarioId, setUsuarioId] = useState<string>();
  const administrador = Boolean(casa && usuarioId === casa.fk_usuario_id);
  const [resultadoListas, setResultadoListas] = useState<{
    casaId: string;
    listas: ListaCompra[];
  }>();
  const [resultadoItens, setResultadoItens] = useState<{
    listaId: string;
    itens: ItemCompra[];
  }>();
  const [idSelecionado, setIdSelecionado] = useState<string | null>(null);
  const [versaoListas, setVersaoListas] = useState(0);
  const [versaoItens, setVersaoItens] = useState(0);
  const [erroListas, setErroListas] = useState<string>();
  const [erroItens, setErroItens] = useState<string>();
  const [erroAcao, setErroAcao] = useState<string>();
  const [aviso, setAviso] = useState<string>();
  const [ocupado, setOcupado] = useState(false);
  const emEnvio = useRef(false);
  const [nomeItem, setNomeItem] = useState("");
  const [quantidadeItem, setQuantidadeItem] = useState("1");
  const [mostrarComprados, setMostrarComprados] = useState(true);
  const [dialogo, setDialogo] = useState<Dialogo | null>(null);
  const [nomeDialogo, setNomeDialogo] = useState("");
  const [quantidadeDialogo, setQuantidadeDialogo] = useState("1");

  const listas =
    resultadoListas?.casaId === casaId ? resultadoListas.listas : null;
  const listaAtiva =
    listas?.find((lista) => lista.id === idSelecionado) ?? listas?.[0] ?? null;
  const listaId = listaAtiva?.id;
  const itens =
    resultadoItens?.listaId === listaId ? resultadoItens.itens : null;
  const { pendentes, comprados } = useMemo(
    () => agruparItensCompra(itens ?? []),
    [itens],
  );
  const progresso = itens?.length ? (comprados.length / itens.length) * 100 : 0;

  useEffect(() => {
    const controlador = new AbortController();
    setUsuarioId(undefined);
    if (casaId) {
      void carregarUsuarioAtual(controlador.signal)
        .then((usuario) => {
          if (!controlador.signal.aborted) setUsuarioId(usuario.id);
        })
        .catch(() => {});
    }
    return () => controlador.abort();
  }, [casaId]);

  useEffect(() => {
    const controlador = new AbortController();
    setResultadoListas(undefined);
    setErroListas(undefined);
    if (casaId) {
      void listarListasCompra(casaId, controlador.signal)
        .then((resposta) => {
          if (!controlador.signal.aborted)
            setResultadoListas({ casaId, listas: resposta });
        })
        .catch((erro) => {
          if (!controlador.signal.aborted) setErroListas(mensagemErro(erro));
        });
    }
    return () => controlador.abort();
  }, [casaId, versaoListas]);

  useEffect(() => {
    const controlador = new AbortController();
    setResultadoItens(undefined);
    setErroItens(undefined);
    if (listaId) {
      void listarItensCompra(listaId, controlador.signal)
        .then((resposta) => {
          if (!controlador.signal.aborted)
            setResultadoItens({ listaId, itens: resposta });
        })
        .catch((erro) => {
          if (!controlador.signal.aborted) setErroItens(mensagemErro(erro));
        });
    }
    return () => controlador.abort();
  }, [listaId, versaoItens]);

  async function executar(acao: () => Promise<unknown>, concluido: () => void) {
    if (emEnvio.current) return;
    emEnvio.current = true;
    setOcupado(true);
    setErroAcao(undefined);
    setAviso(undefined);
    try {
      await acao();
      concluido();
      setDialogo(null);
    } catch (erro) {
      setErroAcao(mensagemErro(erro));
    } finally {
      emEnvio.current = false;
      setOcupado(false);
    }
  }

  function selecionarLista(id: string) {
    setIdSelecionado(id);
    setNomeItem("");
    setQuantidadeItem("1");
    setErroAcao(undefined);
    setAviso(undefined);
  }

  function abrirDialogo(acao: Dialogo) {
    setDialogo(acao);
    setNomeDialogo(
      acao.tipo === "lista"
        ? (acao.lista?.nome ?? "")
        : acao.tipo === "item"
          ? acao.item.nome
          : "",
    );
    setQuantidadeDialogo(
      acao.tipo === "item" ? String(acao.item.quantidade) : "1",
    );
    setErroAcao(undefined);
  }

  function adicionarItem() {
    const quantidade = quantidadeValida(quantidadeItem);
    if (!listaAtiva || !nomeItem.trim() || quantidade === null) {
      setErroAcao("Informe o nome e uma quantidade inteira maior que zero.");
      return;
    }
    void executar(
      () => criarItemCompra(listaAtiva.id, nomeItem, quantidade),
      () => {
        setNomeItem("");
        setQuantidadeItem("1");
        setVersaoItens((valor) => valor + 1);
        setAviso("Produto adicionado.");
      },
    );
  }

  function salvarDialogo() {
    if (!dialogo) return;
    if (dialogo.tipo === "excluir-lista") {
      if (!administrador) return;
      void executar(
        () => excluirListaCompra(dialogo.lista.id),
        () => {
          setIdSelecionado(null);
          setVersaoListas((valor) => valor + 1);
          setAviso("Lista excluída.");
        },
      );
      return;
    }
    if (dialogo.tipo === "excluir-item") {
      void executar(
        () => excluirItemCompra(dialogo.item.id),
        () => {
          setVersaoItens((valor) => valor + 1);
          setAviso("Produto excluído.");
        },
      );
      return;
    }
    if (!nomeDialogo.trim()) {
      setErroAcao("Informe um nome.");
      return;
    }
    if (dialogo.tipo === "lista") {
      if (!casaId) return;
      void executar(
        () =>
          dialogo.lista
            ? renomearListaCompra(dialogo.lista.id, nomeDialogo)
            : criarListaCompra(casaId, nomeDialogo).then((criada) => {
                setIdSelecionado(criada.id);
              }),
        () => {
          setVersaoListas((valor) => valor + 1);
          setAviso(dialogo.lista ? "Lista renomeada." : "Lista criada.");
        },
      );
      return;
    }
    const quantidade = quantidadeValida(quantidadeDialogo);
    if (quantidade === null) {
      setErroAcao("Informe uma quantidade inteira maior que zero.");
      return;
    }
    void executar(
      () =>
        editarItemCompra(dialogo.item.id, { nome: nomeDialogo, quantidade }),
      () => {
        setVersaoItens((valor) => valor + 1);
        setAviso("Produto atualizado.");
      },
    );
  }

  function alternarCompra(item: ItemCompra) {
    void executar(
      () => definirItemComprado(item.id, !item.comprado),
      () => {
        setVersaoItens((valor) => valor + 1);
        setAviso(
          item.comprado
            ? "Produto devolvido aos pendentes."
            : "Produto marcado como comprado.",
        );
      },
    );
  }

  function linhaItem(item: ItemCompra) {
    return (
      <View key={item.id} style={styles.itemRow}>
        <MotionPressable
          accessibilityRole="checkbox"
          accessibilityLabel={`${item.nome}, quantidade ${item.quantidade}`}
          accessibilityState={{ checked: item.comprado, disabled: ocupado }}
          disabled={ocupado}
          onPress={() => alternarCompra(item)}
          style={[styles.checkbox, item.comprado && styles.checkboxChecked]}
        >
          {item.comprado && <Check color={Caldera.obsidian} size={17} />}
        </MotionPressable>
        <View style={styles.itemCopy}>
          <Text
            style={[styles.itemName, item.comprado && styles.purchasedName]}
          >
            {item.nome}
          </Text>
          <Text style={styles.meta}>Quantidade: {item.quantidade}</Text>
        </View>
        <MotionPressable
          accessibilityRole="button"
          accessibilityLabel={`Editar ${item.nome}`}
          disabled={ocupado}
          onPress={() => abrirDialogo({ tipo: "item", item })}
          style={styles.iconButton}
        >
          <Pencil color={Caldera.obsidian} size={18} />
        </MotionPressable>
        <MotionPressable
          accessibilityRole="button"
          accessibilityLabel={`Excluir ${item.nome}`}
          disabled={ocupado}
          onPress={() => abrirDialogo({ tipo: "excluir-item", item })}
          style={styles.iconButton}
        >
          <Trash2 color={Caldera.obsidian} size={18} />
        </MotionPressable>
      </View>
    );
  }

  const exclusao =
    dialogo?.tipo === "excluir-lista" || dialogo?.tipo === "excluir-item";
  const tituloDialogo =
    dialogo?.tipo === "excluir-lista"
      ? "EXCLUIR LISTA?"
      : dialogo?.tipo === "excluir-item"
        ? "EXCLUIR PRODUTO?"
        : dialogo?.tipo === "item"
          ? "EDITAR PRODUTO"
          : dialogo?.lista
            ? "RENOMEAR LISTA"
            : "NOVA LISTA";

  return (
    <SafeAreaView style={styles.safe} edges={["top", "left", "right"]}>
      <ScrollView
        contentContainerStyle={styles.page}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.content}>
          <Link href="/" asChild>
            <MotionPressable accessibilityRole="button" style={styles.backLink}>
              <ArrowLeft color={Caldera.obsidian} size={18} />
              <Text style={styles.backText}>Voltar ao início</Text>
            </MotionPressable>
          </Link>

          <View style={styles.heading}>
            <View style={styles.headingCopy}>
              <Text style={styles.eyebrow}>
                TETO JUSTO · {casa?.nome ?? "CASA"}
              </Text>
              <Text
                accessibilityRole="header"
                style={[styles.title, compacto && styles.titleSmall]}
              >
                LISTAS DE COMPRAS
              </Text>
              <Text style={styles.body}>
                Organize as compras com todos os moradores.
              </Text>
            </View>
            <ShoppingBasket color={Caldera.ember} size={compacto ? 36 : 50} />
          </View>

          {aviso && <Text style={styles.success}>{aviso}</Text>}
          {erroAcao && (
            <Text accessibilityRole="alert" style={styles.error}>
              {erroAcao}
            </Text>
          )}
          {erroListas && (
            <Text accessibilityRole="alert" style={styles.error}>
              {erroListas}
            </Text>
          )}

          <View style={[styles.workspace, compacto && styles.workspaceCompact]}>
            <View style={[styles.sidebar, compacto && styles.sidebarCompact]}>
              <View style={styles.sidebarHeader}>
                <Text style={styles.sectionTitle}>SUAS LISTAS</Text>
                <MotionPressable
                  accessibilityRole="button"
                  accessibilityLabel="Atualizar listas"
                  disabled={ocupado}
                  onPress={() => setVersaoListas((valor) => valor + 1)}
                  style={styles.iconButton}
                >
                  <RefreshCw color={Caldera.obsidian} size={19} />
                </MotionPressable>
              </View>
              {listas === null && !erroListas && (
                <ActivityIndicator
                  accessibilityLabel="Carregando listas"
                  color={Caldera.ember}
                />
              )}
              {listas !== null && (
                <ScrollView
                  horizontal={compacto}
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={[
                    styles.listSelector,
                    compacto && styles.listSelectorCompact,
                  ]}
                  nestedScrollEnabled
                >
                  {listas.map((lista) => (
                    <MotionPressable
                      key={lista.id}
                      accessibilityRole="button"
                      accessibilityState={{
                        selected: lista.id === listaAtiva?.id,
                        disabled: ocupado,
                      }}
                      disabled={ocupado}
                      onPress={() => selecionarLista(lista.id)}
                      style={[
                        styles.listPill,
                        lista.id === listaAtiva?.id && styles.listPillActive,
                      ]}
                    >
                      <Text style={styles.listPillText} numberOfLines={1}>
                        {lista.nome}
                      </Text>
                    </MotionPressable>
                  ))}
                  <MotionPressable
                    accessibilityRole="button"
                    disabled={ocupado}
                    onPress={() => abrirDialogo({ tipo: "lista" })}
                    style={styles.newListPill}
                  >
                    <Plus color={Caldera.obsidian} size={18} />
                    <Text style={styles.listPillText}>Nova lista</Text>
                  </MotionPressable>
                </ScrollView>
              )}
              {listas?.length === 0 && (
                <Text style={styles.meta}>
                  Crie a primeira lista de compras da casa.
                </Text>
              )}
            </View>

            <View
              style={[
                styles.listContent,
                compacto && styles.listContentCompact,
              ]}
            >
              {listaAtiva ? (
                <View style={styles.listCard}>
                  <View style={styles.listHeading}>
                    <View style={styles.listHeadingCopy}>
                      <Text accessibilityRole="header" style={styles.listTitle}>
                        {listaAtiva.nome}
                      </Text>
                      <Text style={styles.meta}>
                        {itens === null
                          ? "Carregando produtos…"
                          : `${comprados.length} de ${itens.length} comprados`}
                      </Text>
                    </View>
                    <View style={styles.headingActions}>
                      <MotionPressable
                        accessibilityRole="button"
                        accessibilityLabel="Renomear lista"
                        disabled={ocupado}
                        onPress={() =>
                          abrirDialogo({ tipo: "lista", lista: listaAtiva })
                        }
                        style={styles.iconButton}
                      >
                        <Pencil color={Caldera.obsidian} size={18} />
                      </MotionPressable>
                      {administrador && (
                        <MotionPressable
                          accessibilityRole="button"
                          accessibilityLabel="Excluir lista"
                          disabled={ocupado}
                          onPress={() =>
                            abrirDialogo({
                              tipo: "excluir-lista",
                              lista: listaAtiva,
                            })
                          }
                          style={styles.iconButton}
                        >
                          <Trash2 color={Caldera.obsidian} size={18} />
                        </MotionPressable>
                      )}
                      <MotionPressable
                        accessibilityRole="button"
                        accessibilityLabel="Atualizar produtos"
                        disabled={ocupado}
                        onPress={() => setVersaoItens((valor) => valor + 1)}
                        style={styles.iconButton}
                      >
                        <RefreshCw color={Caldera.obsidian} size={18} />
                      </MotionPressable>
                    </View>
                  </View>
                  <View style={styles.track}>
                    <View
                      style={[styles.progress, { width: `${progresso}%` }]}
                    />
                  </View>

                  <View
                    style={[styles.addRow, compacto && styles.addRowCompact]}
                  >
                    <TextInput
                      accessibilityLabel="Nome do produto"
                      placeholder="Adicionar produto"
                      placeholderTextColor="#666"
                      value={nomeItem}
                      onChangeText={setNomeItem}
                      editable={!ocupado}
                      returnKeyType="done"
                      onSubmitEditing={adicionarItem}
                      style={styles.nameInput}
                    />
                    <TextInput
                      accessibilityLabel="Quantidade do produto"
                      placeholder="Qtd."
                      placeholderTextColor="#666"
                      keyboardType="number-pad"
                      value={quantidadeItem}
                      onChangeText={setQuantidadeItem}
                      editable={!ocupado}
                      style={styles.quantityInput}
                    />
                    <MotionPressable
                      accessibilityRole="button"
                      accessibilityLabel="Adicionar produto"
                      disabled={ocupado}
                      onPress={adicionarItem}
                      style={[styles.addButton, ocupado && styles.disabled]}
                    >
                      <Plus color={Caldera.obsidian} size={20} />
                    </MotionPressable>
                  </View>

                  {erroItens && (
                    <Text accessibilityRole="alert" style={styles.error}>
                      {erroItens}
                    </Text>
                  )}
                  {itens === null && !erroItens && (
                    <ActivityIndicator
                      accessibilityLabel="Carregando produtos"
                      color={Caldera.ember}
                    />
                  )}
                  {itens !== null && (
                    <>
                      <Text style={styles.groupTitle}>
                        PENDENTES · {pendentes.length}
                      </Text>
                      {pendentes.length ? (
                        pendentes.map(linhaItem)
                      ) : (
                        <Text style={styles.emptyText}>
                          Nenhum produto pendente.
                        </Text>
                      )}
                      {comprados.length > 0 && (
                        <>
                          <View style={styles.divider} />
                          <MotionPressable
                            accessibilityRole="button"
                            accessibilityLabel={
                              mostrarComprados
                                ? "Ocultar produtos comprados"
                                : "Mostrar produtos comprados"
                            }
                            onPress={() =>
                              setMostrarComprados((valor) => !valor)
                            }
                            style={styles.groupToggle}
                          >
                            <Text style={styles.groupTitle}>
                              COMPRADOS · {comprados.length}
                            </Text>
                            {mostrarComprados ? (
                              <ChevronUp size={18} color={Caldera.obsidian} />
                            ) : (
                              <ChevronDown size={18} color={Caldera.obsidian} />
                            )}
                          </MotionPressable>
                          {mostrarComprados && comprados.map(linhaItem)}
                        </>
                      )}
                    </>
                  )}
                </View>
              ) : listas === null ? (
                <View style={styles.emptyCard}>
                  {erroListas ? (
                    <Text style={styles.body}>
                      Não foi possível carregar as listas. Tente atualizar.
                    </Text>
                  ) : (
                    <ActivityIndicator
                      accessibilityLabel="Carregando listas de compras"
                      color={Caldera.ember}
                    />
                  )}
                </View>
              ) : (
                <View style={styles.emptyCard}>
                  <ShoppingBasket size={36} color={Caldera.ember} />
                  <Text style={styles.sectionTitle}>
                    NENHUMA LISTA SELECIONADA
                  </Text>
                  <Text style={styles.body}>
                    {listas?.length === 0
                      ? "Crie uma lista para começar a organizar as compras."
                      : "Selecione uma lista para ver seus produtos."}
                  </Text>
                  {listas?.length === 0 && (
                    <MotionPressable
                      accessibilityRole="button"
                      onPress={() => abrirDialogo({ tipo: "lista" })}
                      style={styles.primaryButton}
                    >
                      <Plus color={Caldera.obsidian} size={18} />
                      <Text style={styles.buttonText}>
                        Criar primeira lista
                      </Text>
                    </MotionPressable>
                  )}
                </View>
              )}
            </View>
          </View>
        </View>
      </ScrollView>

      <Modal
        transparent
        animationType="fade"
        visible={dialogo !== null}
        onRequestClose={() => {
          if (!ocupado) setDialogo(null);
        }}
      >
        <View style={styles.backdrop}>
          <View accessibilityViewIsModal style={styles.dialogCard}>
            <Text accessibilityRole="header" style={styles.sectionTitle}>
              {tituloDialogo}
            </Text>
            {exclusao ? (
              <Text style={styles.body}>
                {dialogo?.tipo === "excluir-lista"
                  ? `Excluir "${dialogo.lista.nome}" e todos os seus produtos? Esta ação não pode ser desfeita.`
                  : `Excluir "${dialogo?.tipo === "excluir-item" ? dialogo.item.nome : ""}"? Esta ação não pode ser desfeita.`}
              </Text>
            ) : (
              <>
                <TextInput
                  accessibilityLabel={
                    dialogo?.tipo === "item"
                      ? "Nome do produto"
                      : "Nome da lista"
                  }
                  placeholder={
                    dialogo?.tipo === "item"
                      ? "Nome do produto"
                      : "Nome da lista"
                  }
                  placeholderTextColor="#666"
                  autoFocus
                  editable={!ocupado}
                  value={nomeDialogo}
                  onChangeText={setNomeDialogo}
                  style={styles.dialogInput}
                />
                {dialogo?.tipo === "item" && (
                  <TextInput
                    accessibilityLabel="Quantidade do produto"
                    keyboardType="number-pad"
                    value={quantidadeDialogo}
                    onChangeText={setQuantidadeDialogo}
                    editable={!ocupado}
                    style={styles.dialogInput}
                  />
                )}
              </>
            )}
            {erroAcao && (
              <Text accessibilityRole="alert" style={styles.error}>
                {erroAcao}
              </Text>
            )}
            <View style={styles.dialogActions}>
              <MotionPressable
                accessibilityRole="button"
                disabled={ocupado}
                onPress={() => {
                  setDialogo(null);
                  setErroAcao(undefined);
                }}
                style={styles.secondaryButton}
              >
                <Text style={styles.buttonText}>Cancelar</Text>
              </MotionPressable>
              <MotionPressable
                accessibilityRole="button"
                disabled={ocupado}
                onPress={salvarDialogo}
                style={[styles.primaryButton, ocupado && styles.disabled]}
              >
                <Text style={styles.buttonText}>
                  {ocupado ? "Salvando…" : exclusao ? "Excluir" : "Salvar"}
                </Text>
              </MotionPressable>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Caldera.pumice },
  page: { flexGrow: 1, padding: Spacing.four, paddingBottom: Spacing.six },
  content: {
    width: "100%",
    maxWidth: 1280,
    alignSelf: "center",
    gap: Spacing.four,
  },
  backLink: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    gap: Spacing.two,
    paddingVertical: Spacing.two,
  },
  backText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  heading: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: Spacing.three,
    alignItems: "center",
  },
  headingCopy: { flexShrink: 1, gap: Spacing.two },
  eyebrow: { color: Caldera.ember, fontSize: 14, fontWeight: "500" },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 56,
    lineHeight: 60,
    letterSpacing: 1.12,
  },
  titleSmall: { fontSize: 36, lineHeight: 40, letterSpacing: 0.72 },
  body: {
    color: Caldera.obsidian,
    fontSize: 16,
    fontWeight: "500",
    lineHeight: 24,
  },
  workspace: {
    flexDirection: "row",
    gap: Spacing.four,
    alignItems: "flex-start",
  },
  workspaceCompact: { flexDirection: "column" },
  sidebar: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    width: 270,
    padding: Spacing.four,
    gap: Spacing.three,
  },
  sidebarCompact: { width: "100%", borderRadius: 24, padding: Spacing.three },
  sidebarHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  sectionTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 30,
    lineHeight: 34,
    letterSpacing: 0.6,
  },
  listSelector: {
    flexDirection: "column",
    gap: Spacing.two,
    alignItems: "stretch",
  },
  listSelectorCompact: { flexDirection: "row", alignItems: "center" },
  listPill: {
    paddingVertical: 12,
    paddingHorizontal: Spacing.three,
    borderRadius: 800,
    backgroundColor: Caldera.pumice,
    minHeight: 44,
    justifyContent: "center",
  },
  listPillActive: { backgroundColor: Caldera.ember },
  listPillText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  newListPill: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: Spacing.one,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.three,
    minHeight: 44,
  },
  listContent: { flex: 1, minWidth: 0 },
  listContentCompact: { flex: 0, width: "100%" },
  listCard: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.three,
  },
  listHeading: {
    flexDirection: "row",
    alignItems: "flex-start",
    justifyContent: "space-between",
    gap: Spacing.two,
  },
  listHeadingCopy: { flex: 1, minWidth: 0 },
  listTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 40,
    lineHeight: 44,
    letterSpacing: 0.8,
  },
  headingActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.one,
  },
  meta: { color: "#555", fontSize: 14, fontWeight: "500" },
  iconButton: {
    width: 40,
    height: 40,
    borderRadius: 800,
    justifyContent: "center",
    alignItems: "center",
  },
  track: {
    backgroundColor: Caldera.pumice,
    height: 8,
    borderRadius: 800,
    overflow: "hidden",
  },
  progress: {
    backgroundColor: Caldera.ember,
    height: "100%",
    borderRadius: 800,
  },
  addRow: {
    flexDirection: "row",
    gap: Spacing.two,
    alignItems: "center",
    flexWrap: "nowrap",
    backgroundColor: Caldera.pumice,
    borderRadius: 20,
    padding: Spacing.two,
  },
  addRowCompact: { borderRadius: 16 },
  nameInput: {
    flex: 1,
    minWidth: 0,
    height: 44,
    paddingHorizontal: Spacing.two,
    color: Caldera.obsidian,
    fontSize: 16,
    fontWeight: "500",
  },
  quantityInput: {
    width: 66,
    height: 44,
    paddingHorizontal: Spacing.one,
    textAlign: "center",
    borderLeftWidth: 1,
    borderColor: "#aaa",
    color: Caldera.obsidian,
    fontSize: 16,
    fontWeight: "500",
  },
  addButton: {
    width: 44,
    height: 44,
    borderRadius: 800,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: Caldera.ember,
  },
  groupTitle: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  groupToggle: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    minHeight: 44,
  },
  itemRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.two,
    minHeight: 56,
  },
  checkbox: {
    width: 26,
    height: 26,
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxChecked: {
    backgroundColor: Caldera.ember,
    borderColor: Caldera.ember,
  },
  itemCopy: { flex: 1, minWidth: 0 },
  itemName: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  purchasedName: { color: "#777", textDecorationLine: "line-through" },
  divider: {
    height: 1,
    backgroundColor: Caldera.pumice,
    marginVertical: Spacing.one,
  },
  emptyText: {
    color: "#666",
    fontSize: 16,
    fontWeight: "500",
    paddingVertical: Spacing.two,
  },
  emptyCard: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.three,
    alignItems: "flex-start",
  },
  primaryButton: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: Spacing.two,
    paddingHorizontal: Spacing.four,
    minHeight: 46,
    borderRadius: 800,
    backgroundColor: Caldera.ember,
  },
  secondaryButton: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: Spacing.four,
    minHeight: 46,
    borderRadius: 800,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
  },
  buttonText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  success: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  error: { color: "#a32316", fontSize: 14, fontWeight: "500", lineHeight: 22 },
  disabled: { opacity: 0.6 },
  backdrop: {
    flex: 1,
    backgroundColor: "#0008",
    justifyContent: "center",
    padding: Spacing.three,
  },
  dialogCard: {
    alignSelf: "center",
    width: "100%",
    maxWidth: 520,
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.three,
  },
  dialogInput: {
    minHeight: 50,
    borderRadius: 16,
    backgroundColor: Caldera.pumice,
    paddingHorizontal: Spacing.three,
    color: Caldera.obsidian,
    fontSize: 16,
    fontWeight: "500",
  },
  dialogActions: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "flex-end",
    gap: Spacing.two,
  },
});
