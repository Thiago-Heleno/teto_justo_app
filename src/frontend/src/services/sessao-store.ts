import { createStore } from "zustand/vanilla";

import {
  lerCasaSelecionada,
  removerCasaSelecionada,
  salvarCasaSelecionada,
} from "./casa-storage.ts";
import type { Casa } from "./casas-api.ts";
import { lerToken, removerToken, salvarToken } from "./token-storage.ts";

export const sessao = createStore<{
  token: string | null;
  pronta: boolean;
  casaAtiva: Casa | null;
  casaPreferidaId: string | null;
}>(() => ({
  token: null,
  pronta: false,
  casaAtiva: null,
  casaPreferidaId: null,
}));

let encerrando: Promise<void> | null = null;
let armazenamento = Promise.resolve();

// Serializa a seleção e o logout para uma gravação antiga não restaurar a casa.
function gravar(acao: () => Promise<void>) {
  const operacao = armazenamento.then(acao);
  armazenamento = operacao.catch(() => {});
  return operacao;
}

export async function restaurarSessao() {
  await gravar(async () => {
    const token = await lerToken();
    const casaPreferidaId = token
      ? await lerCasaSelecionada().catch(() => null)
      : null;
    sessao.setState({ token, casaPreferidaId, casaAtiva: null });
  });
}

export async function salvarSessao(token: string) {
  await gravar(async () => {
    await removerCasaSelecionada();
    await salvarToken(token);
    sessao.setState({ token, casaAtiva: null, casaPreferidaId: null });
  });
}

export async function selecionarCasa(casa: Casa, signal?: AbortSignal) {
  const token = sessao.getState().token;
  let selecionada = false;
  await gravar(async () => {
    if (!token || token !== sessao.getState().token || signal?.aborted) return;
    await salvarCasaSelecionada(casa.id);
    if (signal?.aborted) return;
    sessao.setState({ casaAtiva: casa, casaPreferidaId: casa.id });
    selecionada = true;
  });
  return selecionada;
}

export function trocarCasa() {
  sessao.setState({ casaAtiva: null });
}

export function encerrarSessao() {
  if (!encerrando) {
    encerrando = gravar(async () => {
      try {
        await Promise.all([removerToken(), removerCasaSelecionada()]);
      } finally {
        sessao.setState({
          token: null,
          casaAtiva: null,
          casaPreferidaId: null,
        });
      }
    }).finally(() => {
      encerrando = null;
    });
  }
  return encerrando;
}
