import { Platform } from "react-native";

import { ErroApi, requisitar } from "./api.ts";
import {
  encerrarSessao,
  restaurarSessao,
  salvarSessao,
  sessao,
} from "./sessao-store.ts";
import { SESSAO_WEB } from "./token-storage.ts";

export async function iniciarAutenticacao() {
  try {
    await restaurarSessao();
    if (sessao.getState().token) {
      await requisitar("/usuarios/eu");
    }
  } catch (erro) {
    // Uma indisponibilidade da API não apaga uma sessão salva.
    if (!(erro instanceof ErroApi && erro.status === 401)) throw erro;
  } finally {
    sessao.setState({ pronta: true });
  }
}

export async function entrar(email: string, senha: string) {
  const resposta = await requisitar<{ token: string | null; expira_em: string }>(
    "/sessoes/login",
    undefined,
    {
      method: "POST",
      publica: true,
      cookieSessao: Platform.OS === "web",
      body: { email: email.trim(), senha },
    },
  );
  const token = Platform.OS === "web" ? SESSAO_WEB : resposta.token;
  if (!token) throw new Error("O servidor não retornou um token de sessão.");
  await salvarSessao(token);
}

export async function sair() {
  if (sessao.getState().token) {
    await requisitar<void>("/sessoes/logout", undefined, { method: "POST" });
  }
  await encerrarSessao();
}
