import { useCallback, useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useStore } from "zustand";

import AppTabs from "@/components/app-tabs";
import { CriarCasa } from "@/components/criar-casa";
import { EntrarCasa } from "@/components/entrar-casa";
import { Caldera, CompactFont } from "@/constants/theme";
import { sair } from "@/services/autenticacao-api";
import { casaInicial, listarCasas, type Casa } from "@/services/casas-api";
import { selecionarCasa, sessao } from "@/services/sessao-store";

export function FluxoCasa() {
  const casaAtiva = useStore(sessao, (estado) => estado.casaAtiva);
  const [restaurar, setRestaurar] = useState(true);
  const [formulario, setFormulario] = useState<"criar" | "entrar" | null>(null);

  const selecionar = useCallback(async (casa: Casa, signal?: AbortSignal) => {
    if (await selecionarCasa(casa, signal)) {
      setRestaurar(false);
      setFormulario(null);
    }
  }, []);

  if (casaAtiva) return <AppTabs key={casaAtiva.id} />;
  if (formulario === "criar") {
    return (
      <CriarCasa onVoltar={() => setFormulario(null)} onCriada={selecionar} />
    );
  }
  if (formulario === "entrar") {
    return (
      <EntrarCasa onVoltar={() => setFormulario(null)} onEntrada={selecionar} />
    );
  }
  return (
    <SelecaoCasa
      restaurar={restaurar}
      selecionar={selecionar}
      onCriar={() => {
        setRestaurar(false);
        setFormulario("criar");
      }}
      onEntrar={() => {
        setRestaurar(false);
        setFormulario("entrar");
      }}
    />
  );
}

function SelecaoCasa({
  restaurar,
  selecionar,
  onCriar,
  onEntrar,
}: {
  restaurar: boolean;
  selecionar: (casa: Casa, signal?: AbortSignal) => Promise<void>;
  onCriar: () => void;
  onEntrar: () => void;
}) {
  const [casas, setCasas] = useState<Casa[] | null>(null);
  const [erro, setErro] = useState<string>();
  const [tentativa, setTentativa] = useState(0);
  const [ocupado, setOcupado] = useState(false);
  const emAndamento = useRef(false);
  const consulta = useRef<AbortController | null>(null);

  useEffect(() => {
    const controlador = new AbortController();
    consulta.current = controlador;
    async function carregar() {
      try {
        const lista = await listarCasas(controlador.signal);
        if (controlador.signal.aborted) return;
        const inicial = restaurar
          ? casaInicial(lista, sessao.getState().casaPreferidaId)
          : null;
        if (inicial) await selecionar(inicial, controlador.signal);
        if (!controlador.signal.aborted) setCasas(lista);
      } catch (falha) {
        if (!controlador.signal.aborted) {
          setErro(
            falha instanceof Error
              ? falha.message
              : "Não foi possível carregar suas casas.",
          );
        }
      }
    }
    void carregar();
    return () => controlador.abort();
  }, [restaurar, selecionar, tentativa]);

  function atualizar() {
    setCasas(null);
    setErro(undefined);
    setTentativa((valor) => valor + 1);
  }

  async function executar(acao: () => Promise<void>) {
    if (emAndamento.current) return;
    emAndamento.current = true;
    setOcupado(true);
    setErro(undefined);
    try {
      await acao();
    } catch (falha) {
      if (!consulta.current?.signal.aborted) {
        setErro(
          falha instanceof Error
            ? falha.message
            : "Não foi possível concluir a operação. Tente novamente.",
        );
      }
    } finally {
      emAndamento.current = false;
      if (!consulta.current?.signal.aborted) setOcupado(false);
    }
  }

  const carregando = casas === null && !erro;

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.page}>
        <View style={styles.content}>
          <Text style={styles.brand}>TETO JUSTO</Text>
          <Text accessibilityRole="header" style={styles.title}>
            ESCOLHA SUA CASA
          </Text>
          <Text style={styles.description}>
            As tarefas e a pontuação que você acompanha são da casa escolhida.
          </Text>

          {carregando && (
            <View style={styles.feedback}>
              <ActivityIndicator
                color={Caldera.obsidian}
                accessibilityLabel="Carregando suas casas"
              />
              <Text style={styles.description}>Buscando suas casas…</Text>
            </View>
          )}

          {casas?.length === 0 && (
            <View style={styles.card}>
              <Text style={styles.houseName}>Nenhuma casa por aqui ainda</Text>
              <Text style={styles.description}>
                Crie sua casa ou use o convite do administrador para entrar numa
                casa existente.
              </Text>
            </View>
          )}

          {casas?.map((casa) => (
            <Pressable
              key={casa.id}
              accessibilityRole="button"
              accessibilityLabel={`Entrar na casa ${casa.nome}, ${casa.endereco}`}
              accessibilityState={{ disabled: ocupado, busy: ocupado }}
              disabled={ocupado}
              onPress={() =>
                void executar(() => selecionar(casa, consulta.current?.signal))
              }
              style={({ pressed }) => [
                styles.card,
                styles.houseButton,
                (pressed || ocupado) && styles.dimmed,
              ]}
            >
              <Text style={styles.houseName}>{casa.nome}</Text>
              <Text style={styles.description}>{casa.endereco}</Text>
              <Text style={styles.enter}>Entrar nesta casa →</Text>
            </Pressable>
          ))}

          {erro && (
            <Text accessibilityRole="alert" style={styles.error}>
              {erro}
            </Text>
          )}
          {ocupado && <ActivityIndicator accessibilityLabel="Aguarde" />}

          <View style={styles.actions}>
            <Pressable
              accessibilityRole="button"
              disabled={ocupado}
              accessibilityState={{ disabled: ocupado }}
              onPress={onCriar}
              style={[
                styles.button,
                styles.createButton,
                ocupado && styles.dimmed,
              ]}
            >
              <Text style={styles.buttonText}>Criar casa</Text>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              disabled={ocupado}
              accessibilityState={{ disabled: ocupado }}
              onPress={onEntrar}
              style={[styles.button, ocupado && styles.dimmed]}
            >
              <Text style={styles.buttonText}>Entrar por convite</Text>
            </Pressable>
            {!carregando && (
              <Pressable
                accessibilityRole="button"
                disabled={ocupado}
                accessibilityState={{ disabled: ocupado }}
                onPress={atualizar}
                style={[styles.button, ocupado && styles.dimmed]}
              >
                <Text style={styles.buttonText}>
                  {casas === null ? "Tentar novamente" : "Atualizar lista"}
                </Text>
              </Pressable>
            )}
            <Pressable
              accessibilityRole="button"
              disabled={ocupado}
              accessibilityState={{ disabled: ocupado }}
              onPress={() => void executar(sair)}
              style={[styles.button, ocupado && styles.dimmed]}
            >
              <Text style={styles.buttonText}>Sair da conta</Text>
            </Pressable>
          </View>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Caldera.limestone },
  page: { flexGrow: 1, padding: 24, justifyContent: "center" },
  content: { width: "100%", maxWidth: 680, alignSelf: "center", gap: 20 },
  brand: { color: Caldera.ember, fontWeight: "800", letterSpacing: 2 },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 42,
    fontWeight: "800",
  },
  description: { color: "#555", fontSize: 16, lineHeight: 24 },
  feedback: { padding: 24, gap: 16, alignItems: "center" },
  card: {
    borderRadius: 24,
    padding: 24,
    gap: 10,
    backgroundColor: Caldera.pumice,
  },
  houseButton: { borderWidth: 1, borderColor: Caldera.obsidian },
  houseName: { color: Caldera.obsidian, fontSize: 23, fontWeight: "700" },
  enter: { color: Caldera.obsidian, fontWeight: "700", marginTop: 8 },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  button: {
    borderWidth: 1,
    borderColor: Caldera.obsidian,
    borderRadius: 24,
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  buttonText: { color: Caldera.obsidian, fontWeight: "600" },
  createButton: { backgroundColor: Caldera.ember, borderColor: Caldera.ember },
  error: { color: "#a32316", lineHeight: 22 },
  dimmed: { opacity: 0.6 },
});
