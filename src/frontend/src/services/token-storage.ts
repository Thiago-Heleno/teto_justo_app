import * as SecureStore from "expo-secure-store";

const CHAVE_TOKEN = "teto_justo_token";

export function salvarToken(token: string) {
  return SecureStore.setItemAsync(CHAVE_TOKEN, token);
}

export function lerToken() {
  return SecureStore.getItemAsync(CHAVE_TOKEN);
}

export function removerToken() {
  return SecureStore.deleteItemAsync(CHAVE_TOKEN);
}
