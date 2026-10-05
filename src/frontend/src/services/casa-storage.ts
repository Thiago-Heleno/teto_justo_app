import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

const CHAVE_CASA = "teto_justo_casa_ativa";

export async function lerCasaSelecionada() {
  return Platform.OS === "web"
    ? localStorage.getItem(CHAVE_CASA)
    : SecureStore.getItemAsync(CHAVE_CASA);
}

export async function salvarCasaSelecionada(id: string) {
  if (Platform.OS === "web") {
    localStorage.setItem(CHAVE_CASA, id);
    return;
  }
  await SecureStore.setItemAsync(CHAVE_CASA, id);
}

export async function removerCasaSelecionada() {
  if (Platform.OS === "web") {
    localStorage.removeItem(CHAVE_CASA);
    return;
  }
  await SecureStore.deleteItemAsync(CHAVE_CASA);
}
