import { Platform } from "react-native";

import { encerrarSessao, sessao } from "./sessao-store.ts";

type ErroValidacao = { loc: (string | number)[]; msg: string };

export class ErroApi extends Error {
  status: number;
  validacoes: ErroValidacao[];

  constructor(
    mensagem: string,
    status: number,
    validacoes: ErroValidacao[] = [],
  ) {
    super(mensagem);
    this.status = status;
    this.validacoes = validacoes;
  }
}

export async function requisitar<T>(
  caminho: string,
  signal?: AbortSignal,
  opcoes?: {
    method?: "GET" | "PATCH" | "POST";
    body?: unknown;
    publica?: boolean;
    cookieSessao?: boolean;
  },
): Promise<T> {
  const apiUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/+$/, "");
  if (!apiUrl) throw new Error("Configure EXPO_PUBLIC_API_URL.");

  const token = opcoes?.publica ? null : sessao.getState().token;
  const tokenBearer = Platform.OS !== "web" ? token : null;
  if (!opcoes?.publica && !token) {
    throw new Error("Entre na sua conta para continuar.");
  }

  const resposta = await fetch(`${apiUrl}${caminho}`, {
    method: opcoes?.method ?? "GET",
    headers: {
      ...(tokenBearer ? { Authorization: `Bearer ${tokenBearer}` } : {}),
      ...(opcoes?.body ? { "Content-Type": "application/json" } : {}),
      ...(Platform.OS === "web" && opcoes?.cookieSessao
        ? { "X-Session-Transport": "cookie" }
        : {}),
    },
    credentials: Platform.OS === "web" ? "include" : "omit",
    body: opcoes?.body ? JSON.stringify(opcoes.body) : undefined,
    signal,
  });

  if (!resposta.ok) {
    if (resposta.status === 401 && token && sessao.getState().token === token) {
      await encerrarSessao();
    }
    const corpo = await resposta.json().catch(() => null);
    const detalhe = corpo?.detail;
    const validacoes: ErroValidacao[] = Array.isArray(detalhe)
      ? detalhe.flatMap((erro) =>
          typeof erro?.msg === "string"
            ? [{ loc: Array.isArray(erro.loc) ? erro.loc : [], msg: erro.msg }]
            : [],
        )
      : [];
    const mensagem =
      typeof detalhe === "string"
        ? detalhe
        : validacoes.map((erro) => erro.msg).join(" ");
    throw new ErroApi(
      mensagem || "Não foi possível concluir a operação.",
      resposta.status,
      validacoes,
    );
  }

  if (resposta.status === 204) return undefined as T;
  return resposta.json() as Promise<T>;
}
