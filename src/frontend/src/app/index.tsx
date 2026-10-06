import { Link } from "expo-router";
import { useRef, useState } from "react";
import {
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
import { Caldera } from "@/constants/theme";
import { sair } from "@/services/autenticacao-api";
import { sessao, trocarCasa } from "@/services/sessao-store";

export default function HomeScreen() {
  const casa = useStore(sessao, (estado) => estado.casaAtiva);
  const [erro, setErro] = useState<string>();
  const [saindo, setSaindo] = useState(false);
  const envioEmAndamento = useRef(false);

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
          {casa && !saindo && <ConvidarMorador casa={casa} />}
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ disabled: saindo }}
            disabled={saindo}
            onPress={trocarCasa}
            style={styles.button}
          >
            <Text style={styles.buttonText}>Trocar de casa</Text>
          </Pressable>
          {erro && (
            <Text accessibilityRole="alert" style={styles.error}>
              {erro}
            </Text>
          )}
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ disabled: saindo, busy: saindo }}
            onPress={() => void fazerLogout()}
            disabled={saindo}
            style={styles.button}
          >
            <Text style={styles.buttonText}>
              {saindo ? "Saindo…" : "Sair da conta"}
            </Text>
          </Pressable>
        </View>
      </ScrollView>
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
  error: { color: "#a32316" },
});
