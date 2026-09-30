import { createStore } from "zustand/vanilla";

import { lerToken, removerToken, salvarToken } from "./token-storage.ts";

export const sessao = createStore<{
  token: string | null;
  pronta: boolean;
}>(() => ({ token: null, pronta: false }));

let encerrando: Promise<void> | null = null;

export async function restaurarSessao() {
  const token = await lerToken();
  sessao.setState({ token });
}

export async function salvarSessao(token: string) {
  await encerrando;
  await salvarToken(token);
  sessao.setState({ token });
}

export function encerrarSessao() {
  if (!encerrando) {
    encerrando = removerToken().finally(() => {
      sessao.setState({ token: null });
      encerrando = null;
    });
  }
  return encerrando;
}
