import * as Clipboard from "expo-clipboard";
import { useFocusEffect } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { Caldera } from "@/constants/theme";
import { ErroApi } from "@/services/api";
import {
  criarConviteCasa,
  type Casa,
  type ConviteCasa,
} from "@/services/casas-api";
import { carregarUsuarioAtual } from "@/services/tarefas-api";

export function ConvidarMorador({ casa }: { casa: Casa }) {
  const [usuarioId, setUsuarioId] = useState<string>();
  const [erro, setErro] = useState<string>();
  const [tentativa, setTentativa] = useState(0);

  useFocusEffect(
    useCallback(() => {
      const controlador = new AbortController();
      setUsuarioId(undefined);
      setErro(undefined);
      carregarUsuarioAtual(controlador.signal)
        .then((usuario) => {
          if (!controlador.signal.aborted) setUsuarioId(usuario.id);
        })
        .catch(() => {
          if (!controlador.signal.aborted) {
            setErro("Não foi possível verificar seu acesso aos convites.");
          }
        });
      return () => {
        controlador.abort();
        setUsuarioId(undefined);
      };
      // A nova tentativa precisa refazer a consulta mesmo sem mudar de aba.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [tentativa]),
  );

  if (erro) {
    return (
      <View style={styles.feedback}>
        <Text accessibilityRole="alert" style={styles.error}>
          {erro}
        </Text>
        <Pressable
          accessibilityRole="button"
          onPress={() => setTentativa((valor) => valor + 1)}
          style={styles.button}
        >
          <Text style={styles.buttonText}>Verificar acesso aos convites</Text>
        </Pressable>
      </View>
    );
  }

  if (!usuarioId || usuarioId !== casa.fk_usuario_id) return null;
  return <EmissaoConvite key={casa.id} casa={casa} />;
}

function EmissaoConvite({ casa }: { casa: Casa }) {
  const [aberto, setAberto] = useState(false);
  const [convite, setConvite] = useState<ConviteCasa>();
  const [erro, setErro] = useState<string>();
  const [gerando, setGerando] = useState(false);
  const [copiando, setCopiando] = useState(false);
  const [copiado, setCopiado] = useState(false);
  const [expirado, setExpirado] = useState(false);
  const [semPermissao, setSemPermissao] = useState(false);
  const requisicao = useRef<AbortController | null>(null);
  const emAndamento = useRef(false);

  useEffect(() => () => requisicao.current?.abort(), []);

  useEffect(() => {
    if (!convite) return;
    const timer = setTimeout(
      () => setExpirado(true),
      Math.max(0, Date.parse(convite.expira_em) - Date.now()),
    );
    return () => clearTimeout(timer);
  }, [convite]);

  async function gerar() {
    if (emAndamento.current || semPermissao) return;
    emAndamento.current = true;
    requisicao.current?.abort();
    const controlador = new AbortController();
    requisicao.current = controlador;
    setAberto(true);
    setGerando(true);
    setConvite(undefined);
    setCopiado(false);
    setCopiando(false);
    setExpirado(false);
    setErro(undefined);
    try {
      const emitido = await criarConviteCasa(casa.id, controlador.signal);
      if (!controlador.signal.aborted) setConvite(emitido);
    } catch (falha) {
      if (controlador.signal.aborted) return;
      if (falha instanceof ErroApi) {
        setSemPermissao(falha.status === 403);
        setErro(falha.message);
      } else {
        setErro(
          "Não foi possível gerar o convite. Verifique sua conexão e tente novamente.",
        );
      }
    } finally {
      if (!controlador.signal.aborted) {
        emAndamento.current = false;
        setGerando(false);
      }
    }
  }

  function fechar() {
    requisicao.current?.abort();
    emAndamento.current = false;
    setAberto(false);
    setConvite(undefined);
    setErro(undefined);
  }

  async function copiar() {
    if (!convite || copiando) return;
    if (Date.parse(convite.expira_em) <= Date.now()) {
      setExpirado(true);
      return;
    }
    const signal = requisicao.current?.signal;
    setCopiando(true);
    setCopiado(false);
    setErro(undefined);
    try {
      if (Platform.OS === "web") {
        await navigator.clipboard.writeText(convite.convite);
      } else {
        await Clipboard.setStringAsync(convite.convite);
      }
      if (signal?.aborted) return;
      setCopiado(true);
    } catch {
      if (!signal?.aborted) {
        setErro(
          "Não foi possível copiar. Selecione o texto do convite e copie manualmente.",
        );
      }
    } finally {
      if (!signal?.aborted) setCopiando(false);
    }
  }

  if (!aberto) {
    if (semPermissao) return null;
    return (
      <Pressable
        accessibilityRole="button"
        onPress={() => void gerar()}
        style={[styles.button, styles.primaryButton]}
      >
        <Text style={styles.buttonText}>Convidar morador</Text>
      </Pressable>
    );
  }

  return (
    <View style={styles.card}>
      <Text accessibilityRole="header" style={styles.title}>
        Convite para {casa.nome}
      </Text>
      <Text style={styles.description}>
        Envie o convite para quem vai morar com você. Na outra conta, a pessoa
        deve escolher “Entrar por convite” na seleção de casas e colar o texto.
      </Text>
      {gerando && (
        <ActivityIndicator
          color={Caldera.obsidian}
          accessibilityLabel="Gerando convite"
        />
      )}
      {convite && (
        <>
          <Text style={styles.description}>
            Válido até {new Date(convite.expira_em).toLocaleString("pt-BR")}.{" "}
            Pode ser usado por mais de uma pessoa até expirar.
          </Text>
          {expirado ? (
            <Text accessibilityRole="alert" style={styles.error}>
              Este convite expirou. Gere um novo para convidar moradores.
            </Text>
          ) : (
            <TextInput
              accessibilityLabel="Convite gerado"
              value={convite.convite}
              readOnly
              multiline
              selectTextOnFocus
              style={styles.invitation}
            />
          )}
          {!expirado && (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{ disabled: copiando, busy: copiando }}
              disabled={copiando}
              onPress={() => void copiar()}
              style={[styles.button, styles.primaryButton]}
            >
              <Text style={styles.buttonText}>
                {copiando ? "Copiando…" : "Copiar convite"}
              </Text>
            </Pressable>
          )}
          {copiado && !expirado && (
            <Text accessibilityLiveRegion="polite" style={styles.description}>
              Convite copiado. Agora envie para o novo morador.
            </Text>
          )}
        </>
      )}
      {erro && (
        <Text accessibilityRole="alert" style={styles.error}>
          {erro}
        </Text>
      )}
      <View style={styles.actions}>
        {!gerando && !semPermissao && (!convite || expirado) && (
          <Pressable
            accessibilityRole="button"
            onPress={() => void gerar()}
            style={styles.button}
          >
            <Text style={styles.buttonText}>
              {expirado ? "Gerar novo convite" : "Tentar novamente"}
            </Text>
          </Pressable>
        )}
        <Pressable
          accessibilityRole="button"
          onPress={fechar}
          style={styles.button}
        >
          <Text style={styles.buttonText}>Fechar convite</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  feedback: { gap: 12 },
  card: {
    padding: 24,
    borderRadius: 24,
    backgroundColor: Caldera.pumice,
    gap: 16,
  },
  title: { color: Caldera.obsidian, fontSize: 23, fontWeight: "700" },
  description: { color: "#555", fontSize: 16, lineHeight: 24 },
  invitation: {
    color: Caldera.obsidian,
    backgroundColor: Caldera.limestone,
    borderColor: Caldera.obsidian,
    borderWidth: 1,
    borderRadius: 12,
    padding: 16,
    fontSize: 14,
    minHeight: 120,
    textAlignVertical: "top",
  },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  button: {
    alignSelf: "flex-start",
    borderWidth: 1,
    borderColor: Caldera.obsidian,
    borderRadius: 12,
    padding: 16,
  },
  primaryButton: { backgroundColor: Caldera.ember, borderColor: Caldera.ember },
  buttonText: { color: Caldera.obsidian, fontWeight: "600" },
  error: { color: "#a32316", lineHeight: 22 },
});
