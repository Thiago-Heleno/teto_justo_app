import { requisitar } from "./api.ts";
import { encerrarSessao } from "./sessao-store.ts";

export type Perfil = { id: string; nome: string; email: string };

export function carregarPerfil(signal?: AbortSignal) {
  return requisitar<Perfil>("/usuarios/eu", signal);
}

export function atualizarPerfil(
  id: string,
  dados: Partial<Pick<Perfil, "nome" | "email">>,
) {
  return requisitar<Perfil>(`/usuarios/${id}`, undefined, {
    method: "PATCH",
    body: dados,
  });
}

// A sessão só termina depois que a API confirma a exclusão.
export async function excluirConta(id: string) {
  await requisitar<void>(`/usuarios/${id}`, undefined, { method: "DELETE" });
  await encerrarSessao();
}
