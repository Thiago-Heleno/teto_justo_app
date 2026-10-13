import { useFocusEffect } from "expo-router";
import { useCallback, useRef, useState } from "react";
import { ActivityIndicator, Modal, StyleSheet, Text, View } from "react-native";

import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import { ErroApi } from "@/services/api";
import {
  listarMoradoresCasa,
  removerMoradorCasa,
  type Casa,
  type MoradorCasa,
} from "@/services/casas-api";

export function MoradoresCasa({
  casa,
  usuarioId,
}: {
  casa: Casa;
  usuarioId?: string;
}) {
  const [moradores, setMoradores] = useState<MoradorCasa[] | null>(null);
  const [erro, setErro] = useState<string>();
  const [tentativa, setTentativa] = useState(0);
  const [selecionado, setSelecionado] = useState<MoradorCasa | null>(null);
  const [removendo, setRemovendo] = useState(false);
  const [semPermissao, setSemPermissao] = useState(false);
  const requisicao = useRef<AbortController | null>(null);
  const emAndamento = useRef(false);
  const administrador = usuarioId === casa.fk_usuario_id && !semPermissao;

  useFocusEffect(
    useCallback(() => {
      const controlador = new AbortController();
      requisicao.current = controlador;
      emAndamento.current = false;
      setMoradores(null);
      setErro(undefined);
      setSelecionado(null);
      setRemovendo(false);
      setSemPermissao(false);
      listarMoradoresCasa(casa.id, controlador.signal)
        .then((lista) => {
          if (!controlador.signal.aborted) setMoradores(lista);
        })
        .catch((falha) => {
          if (controlador.signal.aborted) return;
          setErro(
            falha instanceof TypeError
              ? "Não foi possível carregar os moradores. Verifique a conexão e tente novamente."
              : falha instanceof Error
                ? falha.message
                : "Não foi possível carregar os moradores.",
          );
        });
      return () => controlador.abort();
      // A tentativa permite atualizar a lista sem mudar de aba.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [casa.id, tentativa]),
  );

  async function confirmarRemocao() {
    const controlador = requisicao.current;
    if (
      !administrador ||
      !selecionado ||
      selecionado.id === casa.fk_usuario_id ||
      emAndamento.current ||
      !controlador ||
      controlador.signal.aborted
    )
      return;
    emAndamento.current = true;
    setRemovendo(true);
    setErro(undefined);
    try {
      await removerMoradorCasa(casa.id, selecionado.id, controlador.signal);
      if (!controlador.signal.aborted) {
        setMoradores(
          (lista) =>
            lista?.filter((morador) => morador.id !== selecionado.id) ?? null,
        );
      }
    } catch (falha) {
      if (controlador.signal.aborted) return;
      if (falha instanceof ErroApi && falha.status === 403)
        setSemPermissao(true);
      setErro(
        falha instanceof TypeError
          ? "Não foi possível confirmar a remoção. Verifique a conexão e atualize a lista antes de tentar novamente."
          : falha instanceof Error
            ? falha.message
            : "Não foi possível remover o morador.",
      );
    } finally {
      if (!controlador.signal.aborted) {
        emAndamento.current = false;
        setRemovendo(false);
        setSelecionado(null);
      }
    }
  }

  return (
    <View style={styles.card}>
      <Text accessibilityRole="header" style={styles.title}>
        MORADORES DA CASA
      </Text>
      {!moradores && !erro && (
        <ActivityIndicator
          accessibilityLabel="Carregando moradores"
          color={Caldera.obsidian}
        />
      )}
      {erro && (
        <Text accessibilityRole="alert" style={styles.error}>
          {erro}
        </Text>
      )}
      {moradores?.length === 0 && (
        <Text style={styles.role}>Nenhum morador encontrado.</Text>
      )}
      {moradores?.map((morador) => (
        <View key={morador.id} style={styles.row}>
          <View style={styles.identity}>
            <Text style={styles.name}>{morador.nome}</Text>
            <Text style={styles.role}>
              {morador.id === casa.fk_usuario_id
                ? "Proprietário · Administrador"
                : "Morador"}
            </Text>
          </View>
          {administrador && morador.id !== casa.fk_usuario_id && (
            <MotionPressable
              accessibilityRole="button"
              accessibilityLabel={`Remover ${morador.nome}`}
              accessibilityState={{ disabled: removendo }}
              disabled={removendo}
              onPress={() => setSelecionado(morador)}
              style={styles.button}
            >
              <Text style={styles.error}>Remover</Text>
            </MotionPressable>
          )}
        </View>
      ))}
      {(moradores || erro) && (
        <MotionPressable
          accessibilityRole="button"
          accessibilityState={{ disabled: removendo }}
          disabled={removendo}
          onPress={() => setTentativa((valor) => valor + 1)}
          style={styles.button}
        >
          <Text style={styles.buttonText}>
            {moradores ? "Atualizar moradores" : "Tentar novamente"}
          </Text>
        </MotionPressable>
      )}
      <Modal
        transparent
        animationType="fade"
        visible={Boolean(selecionado && administrador)}
        onRequestClose={() => {
          if (!removendo) setSelecionado(null);
        }}
      >
        <View style={styles.backdrop}>
          <View accessibilityViewIsModal style={styles.modalCard}>
            <Text accessibilityRole="header" style={styles.title}>
              Remover morador?
            </Text>
            <Text style={styles.name}>
              {selecionado?.nome} perderá o acesso a esta casa. Para voltar,
              precisará de um novo convite.
            </Text>
            <View style={styles.actions}>
              <MotionPressable
                accessibilityRole="button"
                disabled={removendo}
                accessibilityState={{ disabled: removendo }}
                onPress={() => setSelecionado(null)}
                style={styles.button}
              >
                <Text style={styles.buttonText}>Cancelar</Text>
              </MotionPressable>
              <MotionPressable
                accessibilityRole="button"
                disabled={removendo}
                accessibilityState={{ disabled: removendo, busy: removendo }}
                onPress={() => void confirmarRemocao()}
                style={styles.button}
              >
                <Text style={styles.error}>
                  {removendo ? "Removendo…" : "Confirmar remoção"}
                </Text>
              </MotionPressable>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    width: "100%",
    padding: Spacing.four,
    gap: Spacing.three,
    borderRadius: 40,
    backgroundColor: Caldera.limestone,
  },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 32,
    lineHeight: 36,
    letterSpacing: 0.64,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    gap: Spacing.three,
    padding: Spacing.three,
    borderRadius: 24,
    backgroundColor: Caldera.pumice,
  },
  identity: { flex: 1, minWidth: 140, gap: 4 },
  name: {
    color: Caldera.obsidian,
    fontSize: 18,
    lineHeight: 26,
    fontWeight: "500",
  },
  role: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  button: {
    alignSelf: "flex-start",
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
  },
  buttonText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  error: { color: "#a32316", lineHeight: 22 },
  backdrop: {
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
  actions: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.three },
});
