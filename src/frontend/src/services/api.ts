import { encerrarSessao, sessao } from "./sessao-store.ts";

export class ErroApi extends Error {
  status: number;

  constructor(mensagem: string, status: number) {
    super(mensagem);
    this.status = status;
  }
}

export async function requisitar<T>(
  caminho: string,
  signal?: AbortSignal,
  opcoes?: {
    method?: "GET" | "PATCH" | "POST";
    body?: unknown;
    publica?: boolean;
  },
): Promise<T> {
  const apiUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/+$/, "");
  if (!apiUrl) throw new Error("Configure EXPO_PUBLIC_API_URL.");

  const token = opcoes?.publica ? null : sessao.getState().token;
  if (!opcoes?.publica && !token) {
    throw new Error("Entre na sua conta para continuar.");
  }

  const resposta = await fetch(`${apiUrl}${caminho}`, {
    method: opcoes?.method ?? "GET",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opcoes?.body ? { "Content-Type": "application/json" } : {}),
    },
    body: opcoes?.body ? JSON.stringify(opcoes.body) : undefined,
    signal,
  });

  if (!resposta.ok) {
    if (resposta.status === 401 && token && sessao.getState().token === token) {
      await encerrarSessao();
    }
    const corpo = await resposta.json().catch(() => null);
    const detalhe = corpo?.detail;
    const mensagem =
      typeof detalhe === "string"
        ? detalhe
        : Array.isArray(detalhe)
          ? detalhe
              .map((erro: { msg?: string }) => erro.msg)
              .filter(Boolean)
              .join(" ")
          : "";
    throw new ErroApi(
      mensagem || "Não foi possível concluir a operação.",
      resposta.status,
    );
  }

  if (resposta.status === 204) return undefined as T;
  return resposta.json() as Promise<T>;
}
