import {
  Check,
  CircleDollarSign,
  Pencil,
  Plus,
  RefreshCw,
  ScrollText,
  Trash2,
  Undo2,
} from "lucide-react-native";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useStore } from "zustand";

import { Avatar } from "@/components/avatar";
import { BotaoVoltar } from "@/components/botao-voltar";
import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import { listarMoradoresCasa, type MoradorCasa } from "@/services/casas-api";
import {
  aplicarMultaCasa,
  atualizarRegraCasa,
  criarRegraCasa,
  definirMultaPaga,
  excluirMultaCasa,
  excluirRegraCasa,
  listarMultasCasa,
  listarRegrasCasa,
  type MultaCasa,
  type RegraCasa,
} from "@/services/regras-casa-api";
import { sessao } from "@/services/sessao-store";
import { carregarUsuarioAtual } from "@/services/tarefas-api";
import {
  centavosParaEntrada,
  filtrarMultas,
  formatarCentavos,
  resumirMultas,
  valorParaCentavos,
  type FiltroMultas,
} from "@/utils/regras-casa";

type AbaVisao = "regras" | "multas";

type Dialogo =
  | { tipo: "regra"; regra?: RegraCasa }
  | { tipo: "multa"; regraIdInicial?: string }
  | { tipo: "excluir-regra"; regra: RegraCasa }
  | { tipo: "excluir-multa"; multa: MultaCasa };

const dataHora = new Intl.DateTimeFormat("pt-BR", {
  dateStyle: "short",
  timeStyle: "short",
});

function mensagemErro(erro: unknown) {
  return erro instanceof Error
    ? erro.message
    : "Não foi possível concluir a operação.";
}

function formatarData(valor: string | null) {
  if (!valor) return "";
  const data = new Date(valor);
  return Number.isNaN(data.getTime()) ? valor : dataHora.format(data);
}

export default function RegrasCasaScreen() {
  const { width } = useWindowDimensions();
  const compacto = width < 720;
  const casa = useStore(sessao, (estado) => estado.casaAtiva);
  const casaId = casa?.id;

  const [aba, setAba] = useState<AbaVisao>("regras");
  const [filtroMultas, setFiltroMultas] = useState<FiltroMultas>("pendentes");
  const [versao, setVersao] = useState(0);

  const [resultadoUsuario, setResultadoUsuario] = useState<{
    casaId: string;
    usuarioId: string;
  }>();
  const [resultadoMoradores, setResultadoMoradores] = useState<{
    casaId: string;
    versao: number;
    moradores: MoradorCasa[];
  }>();
  const [resultadoRegras, setResultadoRegras] = useState<{
    casaId: string;
    versao: number;
    regras: RegraCasa[];
  }>();
  const [resultadoMultas, setResultadoMultas] = useState<{
    casaId: string;
    versao: number;
    multas: MultaCasa[];
  }>();

  const [falhaRegras, setFalhaRegras] = useState<{
    casaId: string;
    versao: number;
    mensagem: string;
  }>();
  const [falhaMultas, setFalhaMultas] = useState<{
    casaId: string;
    versao: number;
    mensagem: string;
  }>();

  const [erroAcao, setErroAcao] = useState<string>();
  const [aviso, setAviso] = useState<string>();
  const [ocupado, setOcupado] = useState(false);
  const emEnvio = useRef(false);

  const [dialogo, setDialogo] = useState<Dialogo | null>(null);
  const [tituloRegra, setTituloRegra] = useState("");
  const [descricaoRegra, setDescricaoRegra] = useState("");
  const [valorRegra, setValorRegra] = useState("");
  const [regraAtiva, setRegraAtiva] = useState(true);
  const [regraSelecionadaId, setRegraSelecionadaId] = useState("");
  const [moradorSelecionadoId, setMoradorSelecionadoId] = useState("");
  const [observacaoMulta, setObservacaoMulta] = useState("");

  const usuarioId =
    resultadoUsuario && resultadoUsuario.casaId === casaId
      ? resultadoUsuario.usuarioId
      : undefined;
  const administrador = Boolean(casa && usuarioId === casa.fk_usuario_id);

  const moradores = useMemo(
    () =>
      resultadoMoradores &&
      resultadoMoradores.casaId === casaId &&
      resultadoMoradores.versao === versao
        ? resultadoMoradores.moradores
        : [],
    [resultadoMoradores, casaId, versao],
  );
  const moradoresPorId = useMemo(
    () => new Map(moradores.map((morador) => [morador.id, morador])),
    [moradores],
  );

  const regras = useMemo(
    () =>
      resultadoRegras &&
      resultadoRegras.casaId === casaId &&
      resultadoRegras.versao === versao
        ? resultadoRegras.regras
        : null,
    [resultadoRegras, casaId, versao],
  );
  const multas = useMemo(
    () =>
      resultadoMultas &&
      resultadoMultas.casaId === casaId &&
      resultadoMultas.versao === versao
        ? resultadoMultas.multas
        : null,
    [resultadoMultas, casaId, versao],
  );

  const erroRegras =
    falhaRegras &&
    falhaRegras.casaId === casaId &&
    falhaRegras.versao === versao
      ? falhaRegras.mensagem
      : undefined;
  const erroMultas =
    falhaMultas &&
    falhaMultas.casaId === casaId &&
    falhaMultas.versao === versao
      ? falhaMultas.mensagem
      : undefined;

  const regrasAtivas = useMemo(
    () => (regras ?? []).filter((regra) => regra.ativa),
    [regras],
  );
  const resumo = useMemo(
    () => resumirMultas(multas ?? [], usuarioId),
    [multas, usuarioId],
  );
  const multasFiltradas = useMemo(
    () => filtrarMultas(multas ?? [], filtroMultas),
    [multas, filtroMultas],
  );

  useEffect(() => {
    const controlador = new AbortController();
    if (casaId) {
      void carregarUsuarioAtual(controlador.signal)
        .then((usuario) => {
          if (!controlador.signal.aborted) {
            setResultadoUsuario({ casaId, usuarioId: usuario.id });
          }
        })
        .catch(() => {});
    }
    return () => controlador.abort();
  }, [casaId]);

  useEffect(() => {
    const controlador = new AbortController();
    if (casaId) {
      void listarMoradoresCasa(casaId, controlador.signal)
        .then((lista) => {
          if (!controlador.signal.aborted) {
            setResultadoMoradores({ casaId, versao, moradores: lista });
          }
        })
        .catch(() => {});
    }
    return () => controlador.abort();
  }, [casaId, versao]);

  useEffect(() => {
    const controlador = new AbortController();
    if (casaId) {
      void listarRegrasCasa(casaId, controlador.signal)
        .then((lista) => {
          if (!controlador.signal.aborted) {
            setResultadoRegras({ casaId, versao, regras: lista });
          }
        })
        .catch((erro) => {
          if (!controlador.signal.aborted) {
            setFalhaRegras({
              casaId,
              versao,
              mensagem: mensagemErro(erro),
            });
          }
        });
    }
    return () => controlador.abort();
  }, [casaId, versao]);

  useEffect(() => {
    const controlador = new AbortController();
    if (casaId) {
      void listarMultasCasa(casaId, controlador.signal)
        .then((lista) => {
          if (!controlador.signal.aborted) {
            setResultadoMultas({ casaId, versao, multas: lista });
          }
        })
        .catch((erro) => {
          if (!controlador.signal.aborted) {
            setFalhaMultas({
              casaId,
              versao,
              mensagem: mensagemErro(erro),
            });
          }
        });
    }
    return () => controlador.abort();
  }, [casaId, versao]);

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

  function abrirDialogoRegra(regra?: RegraCasa) {
    setTituloRegra(regra?.titulo ?? "");
    setDescricaoRegra(regra?.descricao ?? "");
    setValorRegra(regra ? centavosParaEntrada(regra.valor_multa_centavos) : "");
    setRegraAtiva(regra?.ativa ?? true);
    setErroAcao(undefined);
    setDialogo({ tipo: "regra", regra });
  }

  function abrirDialogoMulta(regraIdInicial?: string) {
    const primeiraAtiva =
      regrasAtivas.find((regra) => regra.id === regraIdInicial) ??
      regrasAtivas[0];
    setRegraSelecionadaId(primeiraAtiva?.id ?? "");
    setMoradorSelecionadoId(moradores[0]?.id ?? "");
    setObservacaoMulta("");
    setErroAcao(undefined);
    setDialogo({ tipo: "multa", regraIdInicial });
  }

  function confirmarDialogo() {
    if (!dialogo || !casaId) return;

    if (dialogo.tipo === "excluir-regra") {
      if (!administrador) return;
      void executar(
        () => excluirRegraCasa(dialogo.regra.id),
        () => {
          setVersao((valor) => valor + 1);
          setAviso("Regra excluída.");
        },
      );
      return;
    }

    if (dialogo.tipo === "excluir-multa") {
      if (!administrador) return;
      void executar(
        () => excluirMultaCasa(dialogo.multa.id),
        () => {
          setVersao((valor) => valor + 1);
          setAviso("Multa excluída.");
        },
      );
      return;
    }

    if (dialogo.tipo === "regra") {
      if (!administrador) return;
      if (!tituloRegra.trim()) {
        setErroAcao("Informe o título da regra.");
        return;
      }
      const centavos = valorParaCentavos(valorRegra);
      if (centavos === null) {
        setErroAcao(
          "Informe um valor de multa válido maior que zero (ex.: 25,00).",
        );
        return;
      }
      void executar(
        () =>
          dialogo.regra
            ? atualizarRegraCasa(dialogo.regra.id, {
                titulo: tituloRegra,
                descricao: descricaoRegra,
                valor_multa_centavos: centavos,
                ativa: regraAtiva,
              })
            : criarRegraCasa({
                fk_casa_id: casaId,
                titulo: tituloRegra,
                descricao: descricaoRegra,
                valor_multa_centavos: centavos,
              }),
        () => {
          setVersao((valor) => valor + 1);
          setAviso(dialogo.regra ? "Regra atualizada." : "Regra criada.");
        },
      );
      return;
    }

    if (dialogo.tipo === "multa") {
      if (!administrador) return;
      if (!regraSelecionadaId) {
        setErroAcao("Selecione a regra descumprida.");
        return;
      }
      if (!moradorSelecionadoId) {
        setErroAcao("Selecione o morador multado.");
        return;
      }
      void executar(
        () =>
          aplicarMultaCasa({
            fk_casa_id: casaId,
            fk_regra_id: regraSelecionadaId,
            fk_usuario_multado_id: moradorSelecionadoId,
            observacao: observacaoMulta,
          }),
        () => {
          setVersao((valor) => valor + 1);
          setAba("multas");
          setFiltroMultas("pendentes");
          setAviso("Multa aplicada.");
        },
      );
    }
  }

  function alternarPagamento(multa: MultaCasa) {
    if (!administrador) return;
    void executar(
      () => definirMultaPaga(multa.id, !multa.paga),
      () => {
        setVersao((valor) => valor + 1);
        setAviso(
          multa.paga
            ? "Pagamento desmarcado. Multa retornou para pendente."
            : "Multa marcada como paga.",
        );
      },
    );
  }

  const regraSelecionada = regrasAtivas.find(
    (regra) => regra.id === regraSelecionadaId,
  );
  const exclusao =
    dialogo?.tipo === "excluir-regra" || dialogo?.tipo === "excluir-multa";
  const tituloDialogo =
    dialogo?.tipo === "excluir-regra"
      ? "EXCLUIR REGRA?"
      : dialogo?.tipo === "excluir-multa"
        ? "EXCLUIR MULTA?"
        : dialogo?.tipo === "multa"
          ? "APLICAR MULTA"
          : dialogo?.regra
            ? "EDITAR REGRA"
            : "NOVA REGRA";

  return (
    <SafeAreaView style={styles.safe} edges={["top", "left", "right"]}>
      <ScrollView
        contentContainerStyle={[styles.page, compacto && styles.pageSmall]}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.content}>
          <BotaoVoltar />

          <View style={styles.heading}>
            <View style={styles.headingCopy}>
              <Text
                accessibilityRole="header"
                style={[styles.title, compacto && styles.titleSmall]}
              >
                REGRAS E MULTAS
              </Text>
              <Text style={styles.body}>
                Consulte os combinados da casa, valores de multa e pendências de
                pagamento.
              </Text>
            </View>
            <MotionPressable
              accessibilityRole="button"
              accessibilityLabel="Atualizar regras e multas"
              disabled={ocupado}
              onPress={() => {
                setErroAcao(undefined);
                setAviso(undefined);
                setVersao((valor) => valor + 1);
              }}
              style={[styles.secondaryButton, ocupado && styles.disabled]}
            >
              <RefreshCw color={Caldera.obsidian} size={18} />
              <Text style={styles.buttonText}>Atualizar</Text>
            </MotionPressable>
          </View>

          {aviso && (
            <Text accessibilityLiveRegion="polite" style={styles.success}>
              {aviso}
            </Text>
          )}
          {erroAcao && !dialogo && (
            <Text accessibilityRole="alert" style={styles.error}>
              {erroAcao}
            </Text>
          )}
          {erroRegras && (
            <Text accessibilityRole="alert" style={styles.error}>
              {erroRegras}
            </Text>
          )}
          {erroMultas && (
            <Text accessibilityRole="alert" style={styles.error}>
              {erroMultas}
            </Text>
          )}

          <View
            style={[styles.summaryRow, compacto && styles.summaryRowCompact]}
          >
            <View style={[styles.statCard, compacto && styles.cardSmall]}>
              <Text style={styles.statLabel}>TOTAL PENDENTE DA CASA</Text>
              <Text
                style={[styles.statValue, compacto && styles.statValueSmall]}
              >
                {formatarCentavos(resumo.totalPendenteCentavos)}
              </Text>
              <Text style={styles.statCaption}>
                {resumo.quantidadePendentes} multa(s) em aberto ·{" "}
                {formatarCentavos(resumo.totalPagoCentavos)} quitado(s)
              </Text>
            </View>
            <View
              style={[
                styles.card,
                styles.summaryCard,
                compacto && styles.cardSmall,
              ]}
            >
              <Text style={styles.eyebrow}>SUAS PENDÊNCIAS</Text>
              <Text style={styles.sectionValue}>
                {formatarCentavos(resumo.minhasPendentesCentavos)}
              </Text>
              <Text style={styles.meta}>
                {resumo.minhasPendentesCount > 0
                  ? `${resumo.minhasPendentesCount} multa(s) pendente(s) no seu nome`
                  : "Nenhuma multa pendente no seu nome"}
              </Text>
              <Text style={styles.meta}>
                {regrasAtivas.length} regra(s) ativa(s) na casa
              </Text>
            </View>
          </View>

          <View style={styles.tabsRow}>
            <MotionPressable
              accessibilityRole="button"
              accessibilityState={{ selected: aba === "regras" }}
              onPress={() => setAba("regras")}
              style={[
                styles.tabPill,
                aba === "regras" && styles.tabPillSelected,
              ]}
            >
              <ScrollText color={Caldera.obsidian} size={18} />
              <Text style={styles.buttonText}>
                Regras da casa ({regras?.length ?? 0})
              </Text>
            </MotionPressable>
            <MotionPressable
              accessibilityRole="button"
              accessibilityState={{ selected: aba === "multas" }}
              onPress={() => setAba("multas")}
              style={[
                styles.tabPill,
                aba === "multas" && styles.tabPillSelected,
              ]}
            >
              <CircleDollarSign color={Caldera.obsidian} size={18} />
              <Text style={styles.buttonText}>
                Multas ({resumo.quantidadePendentes} pendentes)
              </Text>
            </MotionPressable>
          </View>

          {aba === "regras" ? (
            <View style={styles.section}>
              <View style={styles.sectionHeader}>
                <View style={styles.sectionHeaderCopy}>
                  <Text accessibilityRole="header" style={styles.sectionTitle}>
                    REGRAS VIGENTES
                  </Text>
                  <Text style={styles.meta}>
                    {administrador
                      ? "Crie regras, ajuste o valor da multa ou pause quando necessário."
                      : "Apenas o administrador pode criar, editar ou aplicar multas."}
                  </Text>
                </View>
                {administrador && (
                  <MotionPressable
                    accessibilityRole="button"
                    disabled={ocupado}
                    onPress={() => abrirDialogoRegra()}
                    style={[styles.primaryButton, ocupado && styles.disabled]}
                  >
                    <Plus color={Caldera.obsidian} size={18} />
                    <Text style={styles.buttonText}>Nova regra</Text>
                  </MotionPressable>
                )}
              </View>

              {regras === null && !erroRegras && (
                <ActivityIndicator
                  accessibilityLabel="Carregando regras da casa"
                  color={Caldera.ember}
                />
              )}

              {regras?.length === 0 && (
                <View style={[styles.card, compacto && styles.cardSmall]}>
                  <Text style={styles.sectionTitle}>
                    NENHUMA REGRA CADASTRADA
                  </Text>
                  <Text style={styles.body}>
                    {administrador
                      ? "Cadastre a primeira regra com multa para organizar os combinados da casa."
                      : "O administrador ainda não cadastrou regras com multa nesta casa."}
                  </Text>
                </View>
              )}

              {regras?.map((regra) => (
                <View
                  key={regra.id}
                  style={[styles.card, compacto && styles.cardSmall]}
                >
                  <View style={styles.cardTopRow}>
                    <View
                      style={[
                        styles.badge,
                        regra.ativa ? styles.badgeSulfur : styles.badgePumice,
                      ]}
                    >
                      <Text style={styles.badgeText}>
                        {regra.ativa ? "Ativa" : "Pausada"}
                      </Text>
                    </View>
                    <Text style={styles.fineAmount}>
                      Multa: {formatarCentavos(regra.valor_multa_centavos)}
                    </Text>
                  </View>
                  <Text style={styles.cardHeadline}>{regra.titulo}</Text>
                  <Text style={styles.body}>
                    {regra.descricao || "Sem descrição adicional."}
                  </Text>
                  {administrador && (
                    <View style={styles.actionsRow}>
                      <MotionPressable
                        accessibilityRole="button"
                        accessibilityLabel={`Aplicar multa de ${regra.titulo}`}
                        disabled={
                          ocupado || !regra.ativa || moradores.length === 0
                        }
                        onPress={() => abrirDialogoMulta(regra.id)}
                        style={[
                          styles.primaryButton,
                          (ocupado || !regra.ativa || moradores.length === 0) &&
                            styles.disabled,
                        ]}
                      >
                        <CircleDollarSign color={Caldera.obsidian} size={18} />
                        <Text style={styles.buttonText}>Aplicar multa</Text>
                      </MotionPressable>
                      <MotionPressable
                        accessibilityRole="button"
                        accessibilityLabel={`Editar ${regra.titulo}`}
                        disabled={ocupado}
                        onPress={() => abrirDialogoRegra(regra)}
                        style={[
                          styles.secondaryButton,
                          ocupado && styles.disabled,
                        ]}
                      >
                        <Pencil color={Caldera.obsidian} size={18} />
                        <Text style={styles.buttonText}>Editar</Text>
                      </MotionPressable>
                      <MotionPressable
                        accessibilityRole="button"
                        accessibilityLabel={`Excluir ${regra.titulo}`}
                        disabled={ocupado}
                        onPress={() => {
                          setErroAcao(undefined);
                          setDialogo({ tipo: "excluir-regra", regra });
                        }}
                        style={[
                          styles.secondaryButton,
                          ocupado && styles.disabled,
                        ]}
                      >
                        <Trash2 color={Caldera.obsidian} size={18} />
                        <Text style={styles.buttonText}>Excluir</Text>
                      </MotionPressable>
                    </View>
                  )}
                </View>
              ))}
            </View>
          ) : (
            <View style={styles.section}>
              <View style={styles.sectionHeader}>
                <View style={styles.sectionHeaderCopy}>
                  <Text accessibilityRole="header" style={styles.sectionTitle}>
                    HISTÓRICO DE MULTAS
                  </Text>
                  <Text style={styles.meta}>
                    Acompanhe infrações registradas e pagamentos confirmados.
                  </Text>
                </View>
                {administrador && (
                  <MotionPressable
                    accessibilityRole="button"
                    disabled={
                      ocupado ||
                      regrasAtivas.length === 0 ||
                      moradores.length === 0
                    }
                    onPress={() => abrirDialogoMulta()}
                    style={[
                      styles.primaryButton,
                      (ocupado ||
                        regrasAtivas.length === 0 ||
                        moradores.length === 0) &&
                        styles.disabled,
                    ]}
                  >
                    <Plus color={Caldera.obsidian} size={18} />
                    <Text style={styles.buttonText}>Aplicar multa</Text>
                  </MotionPressable>
                )}
              </View>

              <View style={styles.tabsRow}>
                {(
                  [
                    { valor: "pendentes", rotulo: "Pendentes" },
                    { valor: "pagas", rotulo: "Pagas" },
                    { valor: "todas", rotulo: "Todas" },
                  ] as const
                ).map((opcao) => (
                  <MotionPressable
                    key={opcao.valor}
                    accessibilityRole="button"
                    accessibilityState={{
                      selected: filtroMultas === opcao.valor,
                    }}
                    onPress={() => setFiltroMultas(opcao.valor)}
                    style={[
                      styles.filterPill,
                      filtroMultas === opcao.valor && styles.tabPillSelected,
                    ]}
                  >
                    <Text style={styles.buttonText}>{opcao.rotulo}</Text>
                  </MotionPressable>
                ))}
              </View>

              {multas === null && !erroMultas && (
                <ActivityIndicator
                  accessibilityLabel="Carregando multas da casa"
                  color={Caldera.ember}
                />
              )}

              {multas !== null && multasFiltradas.length === 0 && (
                <View style={[styles.card, compacto && styles.cardSmall]}>
                  <Text style={styles.sectionTitle}>
                    NENHUMA MULTA NESTE FILTRO
                  </Text>
                  <Text style={styles.body}>
                    {filtroMultas === "pendentes"
                      ? "Não há multas pendentes de pagamento."
                      : filtroMultas === "pagas"
                        ? "Nenhuma multa paga registrada ainda."
                        : "Nenhuma multa foi aplicada nesta casa até o momento."}
                  </Text>
                </View>
              )}

              {multasFiltradas.map((multa) => {
                const multado = moradoresPorId.get(multa.fk_usuario_multado_id);
                const nomeMultado = multado?.nome ?? "Morador";
                const ehUsuarioAtual =
                  multa.fk_usuario_multado_id === usuarioId;

                return (
                  <View
                    key={multa.id}
                    style={[styles.card, compacto && styles.cardSmall]}
                  >
                    <View style={styles.fineHeader}>
                      <View style={styles.residentInfo}>
                        <Avatar
                          nome={nomeMultado}
                          foto={multado?.foto}
                          tamanho={40}
                        />
                        <View style={styles.residentCopy}>
                          <Text style={styles.residentName}>
                            {nomeMultado}
                            {ehUsuarioAtual ? " · Você" : ""}
                          </Text>
                          <Text style={styles.meta}>
                            Aplicada em {formatarData(multa.criado_em)}
                          </Text>
                        </View>
                      </View>
                      <Text style={styles.fineValue}>
                        {formatarCentavos(multa.valor_centavos)}
                      </Text>
                    </View>

                    <View style={styles.cardTopRow}>
                      <View
                        style={[
                          styles.badge,
                          multa.paga ? styles.badgePumice : styles.badgeSulfur,
                        ]}
                      >
                        <Text style={styles.badgeText}>
                          {multa.paga ? "Paga" : "Pendente"}
                        </Text>
                      </View>
                      {multa.paga && multa.pago_em && (
                        <Text style={styles.meta}>
                          Quitada em {formatarData(multa.pago_em)}
                        </Text>
                      )}
                    </View>

                    <Text style={styles.cardHeadline}>
                      {multa.titulo_regra}
                    </Text>
                    {multa.observacao && (
                      <Text style={styles.body}>{multa.observacao}</Text>
                    )}

                    {administrador && (
                      <View style={styles.actionsRow}>
                        <MotionPressable
                          accessibilityRole="button"
                          disabled={ocupado}
                          onPress={() => alternarPagamento(multa)}
                          style={[
                            multa.paga
                              ? styles.secondaryButton
                              : styles.primaryButton,
                            ocupado && styles.disabled,
                          ]}
                        >
                          {multa.paga ? (
                            <Undo2 color={Caldera.obsidian} size={18} />
                          ) : (
                            <Check color={Caldera.obsidian} size={18} />
                          )}
                          <Text style={styles.buttonText}>
                            {multa.paga
                              ? "Desmarcar pagamento"
                              : "Marcar como paga"}
                          </Text>
                        </MotionPressable>
                        <MotionPressable
                          accessibilityRole="button"
                          accessibilityLabel={`Excluir multa de ${nomeMultado}`}
                          disabled={ocupado}
                          onPress={() => {
                            setErroAcao(undefined);
                            setDialogo({ tipo: "excluir-multa", multa });
                          }}
                          style={[
                            styles.secondaryButton,
                            ocupado && styles.disabled,
                          ]}
                        >
                          <Trash2 color={Caldera.obsidian} size={18} />
                          <Text style={styles.buttonText}>Excluir</Text>
                        </MotionPressable>
                      </View>
                    )}
                  </View>
                );
              })}
            </View>
          )}
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
          <ScrollView
            contentContainerStyle={styles.modalScroll}
            keyboardShouldPersistTaps="handled"
          >
            <View accessibilityViewIsModal style={styles.dialogCard}>
              <Text accessibilityRole="header" style={styles.sectionTitle}>
                {tituloDialogo}
              </Text>

              {exclusao && (
                <Text style={styles.body}>
                  {dialogo?.tipo === "excluir-regra"
                    ? `Excluir a regra "${dialogo.regra.titulo}"? Se já houver multas vinculadas, pause a regra em Editar.`
                    : `Excluir esta multa de ${
                        dialogo?.tipo === "excluir-multa"
                          ? formatarCentavos(dialogo.multa.valor_centavos)
                          : ""
                      }? Esta ação não pode ser desfeita.`}
                </Text>
              )}

              {dialogo?.tipo === "regra" && (
                <>
                  <Text style={styles.fieldLabel}>Título da regra</Text>
                  <TextInput
                    accessibilityLabel="Título da regra"
                    placeholder="Ex.: Silêncio após as 22h"
                    placeholderTextColor="#666"
                    editable={!ocupado}
                    value={tituloRegra}
                    onChangeText={setTituloRegra}
                    style={styles.dialogInput}
                  />
                  <Text style={styles.fieldLabel}>Descrição (opcional)</Text>
                  <TextInput
                    accessibilityLabel="Descrição da regra"
                    placeholder="Detalhe quando a regra se aplica"
                    placeholderTextColor="#666"
                    multiline
                    editable={!ocupado}
                    value={descricaoRegra}
                    onChangeText={setDescricaoRegra}
                    style={[styles.dialogInput, styles.multilineInput]}
                  />
                  <Text style={styles.fieldLabel}>Valor da multa (R$)</Text>
                  <TextInput
                    accessibilityLabel="Valor da multa em reais"
                    placeholder="Ex.: 25,00"
                    placeholderTextColor="#666"
                    keyboardType="decimal-pad"
                    editable={!ocupado}
                    value={valorRegra}
                    onChangeText={setValorRegra}
                    style={styles.dialogInput}
                  />
                  {dialogo.regra && (
                    <View style={styles.switchRow}>
                      <Text style={styles.fieldLabel}>Regra ativa</Text>
                      <Switch
                        accessibilityLabel="Regra ativa"
                        disabled={ocupado}
                        value={regraAtiva}
                        onValueChange={setRegraAtiva}
                      />
                    </View>
                  )}
                </>
              )}

              {dialogo?.tipo === "multa" && (
                <>
                  <Text style={styles.fieldLabel}>Regra descumprida</Text>
                  <View style={styles.choicesWrap}>
                    {regrasAtivas.map((regra) => {
                      const selecionada = regra.id === regraSelecionadaId;
                      return (
                        <MotionPressable
                          key={regra.id}
                          accessibilityRole="radio"
                          accessibilityState={{
                            checked: selecionada,
                            disabled: ocupado,
                          }}
                          disabled={ocupado}
                          onPress={() => setRegraSelecionadaId(regra.id)}
                          style={[
                            styles.choicePill,
                            selecionada && styles.choicePillSelected,
                          ]}
                        >
                          <Text style={styles.choiceText}>
                            {regra.titulo} ·{" "}
                            {formatarCentavos(regra.valor_multa_centavos)}
                          </Text>
                        </MotionPressable>
                      );
                    })}
                  </View>

                  {regraSelecionada && (
                    <Text style={styles.meta}>
                      Valor da multa:{" "}
                      {formatarCentavos(regraSelecionada.valor_multa_centavos)}
                    </Text>
                  )}

                  <Text style={styles.fieldLabel}>Morador</Text>
                  <View style={styles.choicesWrap}>
                    {moradores.map((morador) => {
                      const selecionado = morador.id === moradorSelecionadoId;
                      return (
                        <MotionPressable
                          key={morador.id}
                          accessibilityRole="radio"
                          accessibilityState={{
                            checked: selecionado,
                            disabled: ocupado,
                          }}
                          disabled={ocupado}
                          onPress={() => setMoradorSelecionadoId(morador.id)}
                          style={[
                            styles.choicePill,
                            selecionado && styles.choicePillSelected,
                          ]}
                        >
                          <Text style={styles.choiceText}>{morador.nome}</Text>
                        </MotionPressable>
                      );
                    })}
                  </View>

                  <Text style={styles.fieldLabel}>Observação (opcional)</Text>
                  <TextInput
                    accessibilityLabel="Observação da multa"
                    placeholder="Ex.: Louça acumulada desde ontem"
                    placeholderTextColor="#666"
                    multiline
                    editable={!ocupado}
                    value={observacaoMulta}
                    onChangeText={setObservacaoMulta}
                    style={[styles.dialogInput, styles.multilineInput]}
                  />
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
                  onPress={confirmarDialogo}
                  style={[styles.primaryButton, ocupado && styles.disabled]}
                >
                  <Text style={styles.buttonText}>
                    {ocupado
                      ? "Salvando…"
                      : exclusao
                        ? "Excluir"
                        : dialogo?.tipo === "multa"
                          ? "Aplicar multa"
                          : "Salvar"}
                  </Text>
                </MotionPressable>
              </View>
            </View>
          </ScrollView>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Caldera.pumice },
  page: { flexGrow: 1, padding: Spacing.four, paddingBottom: Spacing.six },
  pageSmall: { padding: Spacing.three, paddingBottom: Spacing.six },
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
    gap: Spacing.three,
    alignItems: "flex-end",
  },
  headingCopy: { flex: 1, minWidth: 260, gap: Spacing.two },
  eyebrow: { color: Caldera.ember, fontSize: 14, fontWeight: "500" },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 56,
    lineHeight: 60,
    letterSpacing: 1.12,
  },
  titleSmall: { fontSize: 40, lineHeight: 44, letterSpacing: 0.8 },
  body: {
    color: Caldera.obsidian,
    fontSize: 16,
    fontWeight: "500",
    lineHeight: 24,
  },
  summaryRow: {
    flexDirection: "row",
    gap: Spacing.three,
    alignItems: "stretch",
  },
  summaryRowCompact: { flexDirection: "column" },
  statCard: {
    flex: 1,
    backgroundColor: Caldera.ember,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.two,
    justifyContent: "center",
  },
  statLabel: { color: Caldera.chalk, fontSize: 14, fontWeight: "500" },
  statValue: {
    color: Caldera.chalk,
    fontFamily: CompactFont,
    fontSize: 52,
    lineHeight: 56,
    letterSpacing: 1,
  },
  statValueSmall: { fontSize: 40, lineHeight: 44 },
  statCaption: {
    color: Caldera.chalk,
    fontSize: 14,
    fontWeight: "500",
    lineHeight: 20,
  },
  summaryCard: { flex: 1, justifyContent: "center" },
  sectionValue: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 40,
    lineHeight: 44,
    letterSpacing: 0.8,
  },
  tabsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: Spacing.two,
    alignItems: "center",
  },
  tabPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.two,
    backgroundColor: Caldera.limestone,
    borderRadius: 800,
    paddingVertical: 12,
    paddingHorizontal: Spacing.four,
  },
  filterPill: {
    backgroundColor: Caldera.limestone,
    borderRadius: 800,
    paddingVertical: 10,
    paddingHorizontal: Spacing.three,
  },
  tabPillSelected: { backgroundColor: Caldera.ember },
  section: { gap: Spacing.three },
  sectionHeader: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    alignItems: "center",
    gap: Spacing.three,
  },
  sectionHeaderCopy: { flex: 1, minWidth: 240, gap: 4 },
  sectionTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 30,
    lineHeight: 34,
    letterSpacing: 0.6,
  },
  card: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.three,
  },
  cardSmall: { borderRadius: 24, padding: Spacing.three },
  cardTopRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: Spacing.two,
  },
  badge: {
    borderRadius: 800,
    paddingVertical: 4,
    paddingHorizontal: 12,
    alignSelf: "flex-start",
  },
  badgeSulfur: { backgroundColor: Caldera.sulfur },
  badgePumice: { backgroundColor: Caldera.pumice },
  badgeText: { color: Caldera.obsidian, fontSize: 13, fontWeight: "500" },
  fineAmount: { color: Caldera.ember, fontSize: 16, fontWeight: "500" },
  cardHeadline: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 28,
    lineHeight: 32,
    letterSpacing: 0.56,
  },
  actionsRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: Spacing.two,
    alignItems: "center",
  },
  fineHeader: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
    alignItems: "center",
    gap: Spacing.two,
  },
  residentInfo: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.two,
    flex: 1,
    minWidth: 180,
  },
  residentCopy: { flex: 1, minWidth: 0, gap: 2 },
  residentName: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  fineValue: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 32,
    lineHeight: 36,
    letterSpacing: 0.64,
  },
  meta: { color: "#555", fontSize: 14, fontWeight: "500", lineHeight: 20 },
  primaryButton: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: Spacing.two,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
    borderRadius: 800,
    backgroundColor: Caldera.ember,
  },
  secondaryButton: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: Spacing.two,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
    borderRadius: 800,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
  },
  buttonText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  success: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  error: { color: "#a32316", fontSize: 14, fontWeight: "500", lineHeight: 22 },
  disabled: { opacity: 0.55 },
  backdrop: {
    flex: 1,
    backgroundColor: "#0008",
    justifyContent: "center",
    padding: Spacing.three,
  },
  modalScroll: {
    flexGrow: 1,
    justifyContent: "center",
  },
  dialogCard: {
    alignSelf: "center",
    width: "100%",
    maxWidth: 560,
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.three,
  },
  fieldLabel: { color: Caldera.obsidian, fontSize: 15, fontWeight: "500" },
  dialogInput: {
    minHeight: 50,
    borderRadius: 16,
    backgroundColor: Caldera.pumice,
    paddingHorizontal: Spacing.three,
    paddingVertical: 12,
    color: Caldera.obsidian,
    fontSize: 16,
    fontWeight: "500",
  },
  multilineInput: { minHeight: 84, textAlignVertical: "top" },
  switchRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  choicesWrap: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  choicePill: {
    borderRadius: 800,
    paddingVertical: 10,
    paddingHorizontal: Spacing.three,
    backgroundColor: Caldera.pumice,
  },
  choicePillSelected: { backgroundColor: Caldera.ember },
  choiceText: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  dialogActions: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "flex-end",
    gap: Spacing.two,
    marginTop: Spacing.one,
  },
});
