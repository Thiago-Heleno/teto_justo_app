import { Image } from "expo-image";
import { useEffect, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { RefreshCw, X } from "lucide-react-native";

import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import { ErroApi } from "@/services/api";
import {
  carregarDetalhesCasa,
  type Casa,
  type DetalhesCasa as DadosDetalhesCasa,
} from "@/services/casas-api";
import { uriFoto } from "@/utils/foto";

export function DetalhesCasa({
  casaReferencia,
  onFechar,
}: {
  casaReferencia: Casa;
  onFechar: () => void;
}) {
  const [dados, setDados] = useState<
    (DadosDetalhesCasa & { referencia: Casa }) | null
  >(null);
  const [erro, setErro] = useState<string>();
  const [tentativa, setTentativa] = useState(0);
  const [fotoComErro, setFotoComErro] = useState<string>();

  useEffect(() => {
    const controlador = new AbortController();
    carregarDetalhesCasa(casaReferencia.id, controlador.signal)
      .then((detalhes) => {
        if (!controlador.signal.aborted) {
          setDados({ ...detalhes, referencia: casaReferencia });
          setErro(undefined);
        }
      })
      .catch((falha) => {
        if (controlador.signal.aborted) return;
        setDados(null);
        setErro(
          falha instanceof ErroApi && [403, 404].includes(falha.status)
            ? "Você não tem mais acesso a esta casa. Use Trocar de casa e Atualizar lista."
            : falha instanceof TypeError
              ? "Não foi possível carregar os detalhes. Verifique a conexão e tente novamente."
              : falha instanceof Error
                ? falha.message
                : "Não foi possível carregar os detalhes da casa.",
        );
      });

    return () => controlador.abort();
  }, [casaReferencia, tentativa]);

  const casa =
    dados &&
    (dados.referencia === casaReferencia ? dados.casa : casaReferencia);
  const foto = casa?.foto ? uriFoto(casa.foto) : null;

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text accessibilityRole="header" style={styles.title}>
          DETALHES DA CASA
        </Text>
        <MotionPressable
          accessibilityRole="button"
          onPress={onFechar}
          style={styles.button}
        >
          <X color={Caldera.obsidian} size={18} />
          <Text style={styles.buttonText}>Fechar</Text>
        </MotionPressable>
      </View>

      {!dados && !erro && (
        <ActivityIndicator
          accessibilityLabel="Carregando detalhes da casa"
          color={Caldera.obsidian}
        />
      )}

      {erro && (
        <View style={styles.feedback}>
          <Text accessibilityRole="alert" style={styles.error}>
            {erro}
          </Text>
          <MotionPressable
            accessibilityRole="button"
            onPress={() => {
              setDados(null);
              setErro(undefined);
              setFotoComErro(undefined);
              setTentativa((valor) => valor + 1);
            }}
            style={styles.button}
          >
            <RefreshCw color={Caldera.obsidian} size={18} />
            <Text style={styles.buttonText}>Tentar novamente</Text>
          </MotionPressable>
        </View>
      )}

      {casa && (
        <View style={styles.details}>
          {casa.foto === null ? (
            <Text style={styles.notice}>Foto não cadastrada</Text>
          ) : foto && foto !== fotoComErro ? (
            <></>
          ) : (
            <Text accessibilityRole="alert" style={styles.notice}>
              O formato da foto não pode ser exibido.
            </Text>
          )}

          <View style={styles.field}>
            <Text style={styles.label}>Nome</Text>
            <Text style={styles.value}>{casa.nome}</Text>
          </View>
          <View style={styles.field}>
            <Text style={styles.label}>Endereço</Text>
            <Text style={styles.value}>{casa.endereco}</Text>
          </View>
          <View style={styles.field}>
            <Text style={styles.label}>Fuso horário</Text>
            <Text style={styles.value}>{casa.timezone}</Text>
          </View>
          <View style={styles.field}>
            <Text style={styles.label}>Proprietário</Text>
            <Text style={styles.value}>
              {dados.nomeProprietario ?? "Nome indisponível"}
            </Text>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    width: "100%",
    padding: Spacing.four,
    gap: Spacing.four,
    borderRadius: 40,
    backgroundColor: Caldera.limestone,
  },
  header: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: Spacing.three,
  },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 32,
    lineHeight: 36,
    letterSpacing: 0.64,
  },
  button: {
    alignItems: "center",
    alignSelf: "flex-start",
    flexDirection: "row",
    gap: Spacing.two,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
  },
  buttonText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  details: { gap: Spacing.three },
  photo: { width: "100%", height: 220, borderRadius: 24 },
  field: {
    gap: Spacing.two,
    padding: Spacing.three,
    borderRadius: 24,
    backgroundColor: Caldera.pumice,
  },
  label: { color: Caldera.obsidian, fontSize: 12, fontWeight: "500" },
  value: {
    color: Caldera.obsidian,
    fontSize: 18,
    lineHeight: 26,
    fontWeight: "500",
  },
  notice: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  feedback: { gap: Spacing.three },
  error: { color: "#a32316", lineHeight: 22 },
});
