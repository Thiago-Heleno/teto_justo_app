import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

const CHAVE_TOKEN = "teto_justo_token";
export const SESSAO_WEB = "sessao-por-cookie";

export async function salvarToken(token: string) {
  if (Platform.OS === "web") {
    return;
  }
  await SecureStore.setItemAsync(CHAVE_TOKEN, token);
}

export async function lerToken() {
  if (Platform.OS === "web") {
    return SESSAO_WEB;
  }
  return SecureStore.getItemAsync(CHAVE_TOKEN);
}

export async function removerToken() {
  if (Platform.OS === "web") {
    return;
  }
  await SecureStore.deleteItemAsync(CHAVE_TOKEN);
}
