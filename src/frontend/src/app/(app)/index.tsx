import { Link, useFocusEffect } from "expo-router";
import { useCallback, useRef, useState } from "react";
import {
  Modal,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  View,
  useWindowDimensions,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useStore } from "zustand";

import { ConvidarMorador } from "@/components/convidar-morador";
import { DetalhesCasa } from "@/components/detalhes-casa";
import { MotionPressable } from "@/components/motion-pressable";
import { MoradoresCasa } from "@/components/moradores-casa";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import { ErroApi } from "@/services/api";
import { sair } from "@/services/autenticacao-api";
import { sairDaCasa } from "@/services/casas-api";
import {
  limparCasaAposSaida,
  sessao,
  trocarCasa,
} from "@/services/sessao-store";
import { carregarUsuarioAtual } from "@/services/tarefas-api";

export default function HomeScreen() {
  const { width } = useWindowDimensions();
  const telaPequena = width < 600;
  const casa = useStore(sessao, (estado) => estado.casaAtiva);
  const [erro, setErro] = useState<string>();
  const [usuarioId, setUsuarioId] = useState<string>();
  const [erroIdentidade, setErroIdentidade] = useState(false);
  const [tentativaIdentidade, setTentativaIdentidade] = useState(0);
  const [confirmacaoAberta, setConfirmacaoAberta] = useState(false);
  const [saindo, setSaindo] = useState(false);
  const [saindoDaCasa, setSaindoDaCasa] = useState(false);
  const [detalhesAbertos, setDetalhesAbertos] = useState(false);
  const envioEmAndamento = useRef(false);
  const ocupado = saindo || saindoDaCasa;
  const podeSairDaCasa = Boolean(
    casa && usuarioId && usuarioId !== casa.fk_usuario_id,
  );

  useFocusEffect(
    useCallback(() => {
      const controlador = new AbortController();
      setUsuarioId(undefined);
      setErroIdentidade(false);
      carregarUsuarioAtual(controlador.signal)
        .then((usuario) => {
          if (!controlador.signal.aborted) setUsuarioId(usuario.id);
        })
        .catch(() => {
          if (!controlador.signal.aborted) setErroIdentidade(true);
        });
      return () => {
        controlador.abort();
        setUsuarioId(undefined);
        setConfirmacaoAberta(false);
      };
      // A nova tentativa precisa refazer a consulta mesmo sem mudar de aba.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [tentativaIdentidade]),
  );

  async function fazerLogout() {
    if (envioEmAndamento.current) return;
    envioEmAndamento.current = true;
    setSaindo(true);
    setErro(undefined);
    try {
      await sair();
    } catch (falha) {
      setErro(
        falha instanceof Error ? falha.message : "Não foi possível sair.",
      );
    } finally {
      envioEmAndamento.current = false;
      setSaindo(false);
    }
  }

  async function confirmarSaidaDaCasa() {
    if (envioEmAndamento.current || !casa || !podeSairDaCasa) return;
    const token = sessao.getState().token;
    if (!token) return;
    envioEmAndamento.current = true;
    setSaindoDaCasa(true);
    setErro(undefined);
    try {
      await sairDaCasa(casa.id);
      await limparCasaAposSaida(casa.id, token);
    } catch (falha) {
      if (falha instanceof ErroApi && falha.status === 404) {
        await limparCasaAposSaida(casa.id, token);
      } else if (!(falha instanceof ErroApi && falha.status === 401)) {
        setErro(
          falha instanceof ErroApi && falha.status === 409
            ? `${falha.message} Conclua ou reatribua suas tarefas antes de sair.`
            : falha instanceof TypeError
              ? "Não foi possível confirmar sua saída. Verifique a conexão e atualize suas casas antes de tentar novamente."
              : falha instanceof Error
                ? falha.message
                : "Não foi possível sair desta casa.",
        );
      }
    } finally {
      envioEmAndamento.current = false;
      setSaindoDaCasa(false);
      setConfirmacaoAberta(false);
    }
  }

  return (
    <SafeAreaView style={styles.container} edges={["top", "left", "right"]}>
      <ScrollView
        contentContainerStyle={[styles.page, telaPequena && styles.pageSmall]}
      >
        <View style={styles.content}>
          <View style={[styles.hero, telaPequena && styles.heroSmall]}>
            <View style={styles.heroCopy}>
              <Text style={styles.eyebrow}>TETO JUSTO · CASA ATIVA</Text>
              <Text
                accessibilityRole="header"
                style={[styles.title, telaPequena && styles.titleSmall]}
              >
                SUA CASA
              </Text>
              <Text style={styles.description}>
                Acompanhe as tarefas da casa e a contribuição de cada morador.
              </Text>
            </View>
            {casa && (
              <View style={[styles.houseCard, telaPequena && styles.cardSmall]}>
                <Text style={styles.houseLabel}>VOCÊ ESTÁ EM</Text>
                <Text
                  style={[
                    styles.houseName,
                    telaPequena && styles.houseNameSmall,
                  ]}
                >
                  {casa.nome}
                </Text>
                <Text style={styles.houseAddress}>{casa.endereco}</Text>
              </View>
            )}
          </View>

          <View style={[styles.card, telaPequena && styles.cardSmall]}>
            <Text accessibilityRole="header" style={styles.sectionTitle}>
              DIA A DIA DA CASA
            </Text>
            <Text style={styles.body}>
              Veja o que precisa ser feito e consulte as informações da casa.
            </Text>
            <View style={styles.actions}>
              <Link href="/tarefas" asChild>
                <MotionPressable
                  accessibilityRole="button"
                  style={[styles.button, styles.primaryButton]}
                >
                  <Text style={styles.buttonText}>Ver tarefas →</Text>
                </MotionPressable>
              </Link>
              <Link href="/gerenciar-casa" asChild>
                <MotionPressable
                  accessibilityRole="button"
                  disabled={ocupado}
                  accessibilityState={{ disabled: ocupado }}
                  style={[styles.button, ocupado && styles.disabled]}
                >
                  <Text style={styles.buttonText}>Gerenciar casa</Text>
                </MotionPressable>
              </Link>
              <Link href="/rotatividades" asChild>
                <MotionPressable
                  accessibilityRole="button"
                  disabled={ocupado}
                  accessibilityState={{ disabled: ocupado }}
                  style={[styles.button, ocupado && styles.disabled]}
                >
                  <Text style={styles.buttonText}>Regras de rodízio</Text>
                </MotionPressable>
              </Link>
              {casa && !detalhesAbertos && (
                <MotionPressable
                  accessibilityRole="button"
                  onPress={() => setDetalhesAbertos(true)}
                  style={styles.button}
                >
                  <Text style={styles.buttonText}>Detalhes da casa</Text>
                </MotionPressable>
              )}
              {casa && usuarioId && !ocupado && (
                <ConvidarMorador casa={casa} usuarioId={usuarioId} />
              )}
            </View>
          </View>

          {casa && detalhesAbertos && (
            <DetalhesCasa
              key={`detalhes-${casa.id}`}
              casaId={casa.id}
              onFechar={() => setDetalhesAbertos(false)}
            />
          )}
          {erroIdentidade && (
            <View style={[styles.card, telaPequena && styles.cardSmall]}>
              <Text accessibilityRole="alert" style={styles.error}>
                Não foi possível verificar seu acesso às ações da casa.
              </Text>
              <MotionPressable
                accessibilityRole="button"
                onPress={() => setTentativaIdentidade((valor) => valor + 1)}
                style={styles.button}
              >
                <Text style={styles.buttonText}>
                  Verificar acesso novamente
                </Text>
              </MotionPressable>
            </View>
          )}
          {casa && (
            <MoradoresCasa
              key={`moradores-${casa.id}`}
              casa={casa}
              usuarioId={usuarioId}
            />
          )}

          <View style={[styles.card, telaPequena && styles.cardSmall]}>
            <Text accessibilityRole="header" style={styles.sectionTitle}>
              ACESSO
            </Text>
            <Text style={styles.body}>
              Escolha outra casa ou encerre seu acesso quando precisar.
            </Text>
            {erro && (
              <Text accessibilityRole="alert" style={styles.error}>
                {erro}
              </Text>
            )}
            <View style={styles.actions}>
              <MotionPressable
                accessibilityRole="button"
                accessibilityState={{ disabled: ocupado }}
                disabled={ocupado}
                onPress={trocarCasa}
                style={[styles.button, ocupado && styles.disabled]}
              >
                <Text style={styles.buttonText}>Trocar de casa</Text>
              </MotionPressable>
              {podeSairDaCasa && (
                <MotionPressable
                  accessibilityRole="button"
                  accessibilityState={{ disabled: ocupado, busy: saindoDaCasa }}
                  disabled={ocupado}
                  onPress={() => setConfirmacaoAberta(true)}
                  style={[styles.button, ocupado && styles.disabled]}
                >
                  <Text style={styles.buttonText}>Sair desta casa</Text>
                </MotionPressable>
              )}
              <MotionPressable
                accessibilityRole="button"
                accessibilityState={{ disabled: ocupado, busy: saindo }}
                onPress={() => void fazerLogout()}
                disabled={ocupado}
                style={[styles.button, ocupado && styles.disabled]}
              >
                <Text style={styles.buttonText}>
                  {saindo ? "Saindo…" : "Sair da conta"}
                </Text>
              </MotionPressable>
            </View>
          </View>
        </View>
      </ScrollView>
      <Modal
        animationType="fade"
        onRequestClose={() => {
          if (!ocupado) setConfirmacaoAberta(false);
        }}
        transparent
        visible={confirmacaoAberta && podeSairDaCasa}
      >
        <View style={styles.modalBackdrop}>
          <View accessibilityViewIsModal style={styles.modalCard}>
            <Text accessibilityRole="header" style={styles.modalTitle}>
              SAIR DESTA CASA?
            </Text>
            <Text style={styles.body}>
              Você perderá o acesso às tarefas desta casa. Para voltar, será
              necessário receber um novo convite.
            </Text>
            <View style={styles.modalActions}>
              <MotionPressable
                accessibilityRole="button"
                accessibilityState={{ disabled: ocupado }}
                disabled={ocupado}
                onPress={() => setConfirmacaoAberta(false)}
                style={[styles.button, ocupado && styles.disabled]}
              >
                <Text style={styles.buttonText}>Cancelar</Text>
              </MotionPressable>
              <MotionPressable
                accessibilityRole="button"
                accessibilityState={{ disabled: ocupado, busy: saindoDaCasa }}
                disabled={ocupado}
                onPress={() => void confirmarSaidaDaCasa()}
                style={[
                  styles.button,
                  styles.primaryButton,
                  ocupado && styles.disabled,
                ]}
              >
                <Text style={styles.buttonText}>
                  {saindoDaCasa ? "Saindo…" : "Sair desta casa"}
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
  container: { flex: 1, backgroundColor: Caldera.pumice },
  page: {
    flexGrow: 1,
    paddingHorizontal: Spacing.four,
    paddingTop: Platform.OS === "web" ? 112 : Spacing.four,
    paddingBottom: Spacing.six,
  },
  pageSmall: {
    paddingHorizontal: Spacing.three,
    paddingTop: Platform.OS === "web" ? 160 : Spacing.three,
  },
  content: {
    width: "100%",
    maxWidth: 1280,
    alignSelf: "center",
    gap: Spacing.four,
  },
  hero: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.four },
  heroSmall: { flexDirection: "column", flexWrap: "nowrap" },
  heroCopy: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 320,
    justifyContent: "center",
    gap: Spacing.three,
  },
  eyebrow: { color: Caldera.ember, fontSize: 14, fontWeight: "500" },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 64,
    lineHeight: 64,
    letterSpacing: 1.28,
  },
  titleSmall: { fontSize: 48, lineHeight: 50, letterSpacing: 0.96 },
  description: {
    color: Caldera.obsidian,
    fontSize: 18,
    lineHeight: 28,
    fontWeight: "500",
    maxWidth: 620,
  },
  houseCard: {
    flexGrow: 1,
    flexShrink: 1,
    flexBasis: 280,
    minWidth: 0,
    borderRadius: 40,
    backgroundColor: Caldera.ember,
    padding: Spacing.five,
    gap: Spacing.three,
  },
  houseLabel: { color: Caldera.chalk, fontSize: 14, fontWeight: "500" },
  houseName: {
    color: Caldera.chalk,
    fontFamily: CompactFont,
    fontSize: 48,
    lineHeight: 52,
  },
  houseNameSmall: { fontSize: 40, lineHeight: 44 },
  houseAddress: {
    color: Caldera.chalk,
    fontSize: 16,
    lineHeight: 24,
    fontWeight: "500",
  },
  card: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.three,
  },
  cardSmall: { padding: Spacing.three, borderRadius: 24 },
  sectionTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 32,
    lineHeight: 36,
    letterSpacing: 0.64,
  },
  body: {
    color: Caldera.obsidian,
    fontSize: 16,
    lineHeight: 24,
    fontWeight: "500",
  },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.three },
  button: {
    alignSelf: "flex-start",
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
  },
  primaryButton: { backgroundColor: Caldera.ember, borderColor: Caldera.ember },
  buttonText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  disabled: { opacity: 0.6 },
  error: { color: "#a32316", lineHeight: 22 },
  modalBackdrop: {
    flex: 1,
    justifyContent: "center",
    padding: Spacing.four,
    backgroundColor: "#0008",
  },
  modalCard: {
    width: "100%",
    maxWidth: 520,
    alignSelf: "center",
    gap: Spacing.four,
    padding: Spacing.five,
    borderRadius: 40,
    backgroundColor: Caldera.limestone,
  },
  modalTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 32,
    lineHeight: 36,
  },
  modalActions: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.three },
});
