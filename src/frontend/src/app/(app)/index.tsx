import { Link, useFocusEffect } from "expo-router";
import { useCallback, useRef, useState } from "react";
import {
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useStore } from "zustand";

import { ConvidarMorador } from "@/components/convidar-morador";
import { DetalhesCasa } from "@/components/detalhes-casa";
import { MoradoresCasa } from "@/components/moradores-casa";
import { Caldera } from "@/constants/theme";
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
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.page}>
        <View style={styles.content}>
          <Text style={styles.brand}>TETO JUSTO</Text>
          <Text accessibilityRole="header" style={styles.title}>
            {casa?.nome ?? "Sua casa, em dia."}
          </Text>
          <Text style={styles.description}>
            Acompanhe as tarefas da casa e a contribuição de cada morador.
          </Text>
          <Link href="/tarefas" style={styles.link}>
            Ver tarefas
          </Link>
          {casa && !detalhesAbertos && (
            <Pressable
              accessibilityRole="button"
              onPress={() => setDetalhesAbertos(true)}
              style={styles.button}
            >
              <Text style={styles.buttonText}>Detalhes da casa</Text>
            </Pressable>
          )}
          {casa && detalhesAbertos && (
            <DetalhesCasa
              key={`detalhes-${casa.id}`}
              casaId={casa.id}
              onFechar={() => setDetalhesAbertos(false)}
            />
          )}
          {erroIdentidade && (
            <View style={styles.verificacao}>
              <Text accessibilityRole="alert" style={styles.error}>
                Não foi possível verificar seu acesso às ações da casa.
              </Text>
              <Pressable
                accessibilityRole="button"
                onPress={() => setTentativaIdentidade((valor) => valor + 1)}
                style={styles.button}
              >
                <Text style={styles.buttonText}>
                  Verificar acesso novamente
                </Text>
              </Pressable>
            </View>
          )}
          {casa && usuarioId && !ocupado && (
            <ConvidarMorador casa={casa} usuarioId={usuarioId} />
          )}
          {casa && (
            <MoradoresCasa
              key={`moradores-${casa.id}`}
              casa={casa}
              usuarioId={usuarioId}
            />
          )}
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ disabled: ocupado }}
            disabled={ocupado}
            onPress={trocarCasa}
            style={styles.button}
          >
            <Text style={styles.buttonText}>Trocar de casa</Text>
          </Pressable>
          {podeSairDaCasa && (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ disabled: ocupado, busy: saindoDaCasa }}
              disabled={ocupado}
              onPress={() => setConfirmacaoAberta(true)}
              style={styles.button}
            >
              <Text style={styles.buttonText}>Sair desta casa</Text>
            </Pressable>
          )}
          {erro && (
            <Text accessibilityRole="alert" style={styles.error}>
              {erro}
            </Text>
          )}
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ disabled: ocupado, busy: saindo }}
            onPress={() => void fazerLogout()}
            disabled={ocupado}
            style={styles.button}
          >
            <Text style={styles.buttonText}>
              {saindo ? "Saindo…" : "Sair da conta"}
            </Text>
          </Pressable>
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
              Sair desta casa?
            </Text>
            <Text style={styles.description}>
              Você perderá o acesso às tarefas desta casa. Para voltar, será
              necessário receber um novo convite.
            </Text>
            <View style={styles.modalActions}>
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ disabled: ocupado }}
                disabled={ocupado}
                onPress={() => setConfirmacaoAberta(false)}
                style={styles.button}
              >
                <Text style={styles.buttonText}>Cancelar</Text>
              </Pressable>
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ disabled: ocupado, busy: saindoDaCasa }}
                disabled={ocupado}
                onPress={() => void confirmarSaidaDaCasa()}
                style={styles.button}
              >
                <Text style={styles.buttonText}>
                  {saindoDaCasa ? "Saindo…" : "Sair desta casa"}
                </Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Caldera.limestone },
  page: {
    flexGrow: 1,
    justifyContent: "center",
    padding: 32,
    paddingTop: Platform.OS === "web" ? 128 : 32,
  },
  content: { width: "100%", maxWidth: 760, alignSelf: "center", gap: 24 },
  brand: { color: Caldera.ember, fontWeight: "800", letterSpacing: 2 },
  title: { color: Caldera.obsidian, fontSize: 36, fontWeight: "800" },
  description: { color: "#555", fontSize: 18, lineHeight: 28 },
  link: { color: Caldera.plasmaViolet, fontWeight: "700", fontSize: 18 },
  button: {
    alignSelf: "flex-start",
    borderWidth: 1,
    borderColor: Caldera.obsidian,
    borderRadius: 12,
    padding: 16,
  },
  buttonText: { color: Caldera.obsidian, fontWeight: "600" },
  verificacao: { gap: 12 },
  error: { color: "#a32316" },
  modalBackdrop: {
    flex: 1,
    justifyContent: "center",
    padding: 24,
    backgroundColor: "#0008",
  },
  modalCard: {
    width: "100%",
    maxWidth: 520,
    alignSelf: "center",
    gap: 20,
    padding: 24,
    borderRadius: 20,
    backgroundColor: Caldera.limestone,
  },
  modalTitle: { color: Caldera.obsidian, fontSize: 24, fontWeight: "800" },
  modalActions: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
});
