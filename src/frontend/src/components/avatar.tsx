import { Image } from "expo-image";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Caldera } from "@/constants/theme";
import { uriFoto } from "@/utils/foto";

type Props = {
  nome: string;
  foto?: string | null;
  tamanho: 36 | 40 | 48 | 64 | 96;
};

export function Avatar({ nome, foto, tamanho }: Props) {
  const [fotoComErro, setFotoComErro] = useState<string>();
  const uri = foto ? uriFoto(foto) : null;

  return (
    <View
      accessible
      accessibilityRole="image"
      accessibilityLabel={nome}
      style={[
        styles.avatar,
        { width: tamanho, height: tamanho, borderRadius: tamanho / 2 },
        tamanho === 36 && styles.lista,
        tamanho === 40 && styles.selecao,
      ]}
    >
      {uri && uri !== fotoComErro ? (
        <Image
          key={uri}
          source={{ uri }}
          contentFit="cover"
          onError={() => setFotoComErro(uri)}
          style={StyleSheet.absoluteFill}
        />
      ) : (
        <Text
          style={[
            styles.iniciais,
            tamanho === 36 && styles.textoLista,
            tamanho === 40 && styles.textoSelecao,
            tamanho === 64 && styles.textoPerfil,
            tamanho === 96 && styles.textoPerfilGrande,
          ]}
        >
          {nome
            .trim()
            .split(/\s+/)
            .slice(0, 2)
            .map((parte) => parte.charAt(0))
            .join("")
            .toUpperCase()}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  avatar: {
    flexShrink: 0,
    overflow: "hidden",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: Caldera.ember,
  },
  lista: { marginLeft: -6, borderWidth: 2, borderColor: Caldera.limestone },
  selecao: { backgroundColor: Caldera.limestone },
  iniciais: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  textoLista: { fontSize: 11 },
  textoSelecao: { lineHeight: 20 },
  textoPerfil: { fontSize: 24 },
  textoPerfilGrande: { fontSize: 36 },
});
