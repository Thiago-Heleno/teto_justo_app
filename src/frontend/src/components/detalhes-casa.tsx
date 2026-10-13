import { Image } from "expo-image";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { Caldera } from "@/constants/theme";
import { ErroApi } from "@/services/api";
import {
  carregarDetalhesCasa,
  type DetalhesCasa as DadosDetalhesCasa,
} from "@/services/casas-api";

function uriFoto(foto: string): string | null {
  const tipo = foto.startsWith("/9j/")
    ? "image/jpeg"
    : foto.startsWith("iVBORw0KGgo")
      ? "image/png"
      : foto.startsWith("R0lGOD")
        ? "image/gif"
        : foto.startsWith("UklGR")
          ? "image/webp"
          : null;
  return tipo ? `data:${tipo};base64,${foto}` : null;
}

export function DetalhesCasa({
  casaId,
  onFechar,
}: {
  casaId: string;
  onFechar: () => void;
}) {
  const [dados, setDados] = useState<DadosDetalhesCasa | null>(null);
  const [erro, setErro] = useState<string>();
  const [tentativa, setTentativa] = useState(0);
  const [fotoFalhou, setFotoFalhou] = useState(false);

  useEffect(() => {
    const controlador = new AbortController();
    carregarDetalhesCasa(casaId, controlador.signal)
      .then((detalhes) => {
        if (!controlador.signal.aborted) setDados(detalhes);
      })
      .catch((falha) => {
        if (controlador.signal.aborted) return;
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
  }, [casaId, tentativa]);

  const casa = dados?.casa;
  const foto = casa?.foto ? uriFoto(casa.foto) : null;

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Text accessibilityRole="header" style={styles.title}>
          Detalhes da casa
        </Text>
        <Pressable
          accessibilityRole="button"
          onPress={onFechar}
          style={styles.button}
        >
          <Text style={styles.buttonText}>Fechar</Text>
        </Pressable>
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
          <Pressable
            accessibilityRole="button"
            onPress={() => {
              setDados(null);
              setErro(undefined);
              setFotoFalhou(false);
              setTentativa((valor) => valor + 1);
            }}
            style={styles.button}
          >
            <Text style={styles.buttonText}>Tentar novamente</Text>
          </Pressable>
        </View>
      )}

      {casa && (
        <View style={styles.details}>
          {casa.foto === null ? (
            <Text style={styles.notice}>Foto não cadastrada</Text>
          ) : foto && !fotoFalhou ? (
            <Image
              accessibilityLabel={`Foto da casa ${casa.nome}`}
              contentFit="cover"
              onError={() => setFotoFalhou(true)}
              source={{ uri: foto }}
              style={styles.photo}
            />
          ) : (
            <Text accessibilityRole="alert" style={styles.notice}>
              O formato da foto não pode ser exibido.
            </Text>
          )}

          <View>
            <Text style={styles.label}>Nome</Text>
            <Text style={styles.value}>{casa.nome}</Text>
          </View>
          <View>
            <Text style={styles.label}>Endereço</Text>
            <Text style={styles.value}>{casa.endereco}</Text>
          </View>
          <View>
            <Text style={styles.label}>Fuso horário</Text>
            <Text style={styles.value}>{casa.timezone}</Text>
          </View>
          <View>
            <Text style={styles.label}>Proprietário</Text>
            <Text style={styles.value}>
              {dados.nomeProprietario ?? "Nome indisponível"}
            </Text>
            <Text selectable style={styles.identifier}>
              ID: {casa.fk_usuario_id}
            </Text>
          </View>
          <View>
            <Text style={styles.label}>ID da casa</Text>
            <Text selectable style={styles.identifier}>
              {casa.id}
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
    padding: 24,
    gap: 20,
    borderRadius: 20,
    backgroundColor: Caldera.pumice,
  },
  header: {
    flexDirection: "row",
    flexWrap: "wrap",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
  },
  title: { color: Caldera.obsidian, fontSize: 24, fontWeight: "800" },
  button: {
    alignSelf: "flex-start",
    borderWidth: 1,
    borderColor: Caldera.obsidian,
    borderRadius: 12,
    padding: 12,
  },
  buttonText: { color: Caldera.obsidian, fontWeight: "600" },
  details: { gap: 16 },
  photo: { width: "100%", height: 220, borderRadius: 12 },
  label: { color: "#555", fontSize: 14, fontWeight: "700" },
  value: { color: Caldera.obsidian, fontSize: 18 },
  identifier: { color: Caldera.obsidian, fontSize: 14 },
  notice: { color: "#555" },
  feedback: { gap: 12 },
  error: { color: "#a32316" },
});
