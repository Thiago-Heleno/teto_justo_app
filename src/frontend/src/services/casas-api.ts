import { requisitar } from "./api.ts";

export type Casa = {
  id: string;
  nome: string;
  endereco: string;
  foto: string | null;
  fk_usuario_id: string;
  timezone: string;
};

export type CasaCriar = Pick<Casa, "nome" | "endereco">;

export type ConviteCasa = { convite: string; expira_em: string };

export function criarConviteCasa(casaId: string, signal?: AbortSignal) {
  return requisitar<ConviteCasa>(`/casas/${casaId}/convites`, signal, {
    method: "POST",
  });
}

export function criarCasa(dados: CasaCriar, signal?: AbortSignal) {
  return requisitar<Casa>("/casas/", signal, {
    method: "POST",
    body: { nome: dados.nome.trim(), endereco: dados.endereco.trim() },
  });
}

export function entrarCasa(convite: string, signal?: AbortSignal) {
  return requisitar<Casa>("/casas/entrar", signal, {
    method: "POST",
    body: { convite: convite.trim() },
  });
}

export async function listarCasas(signal?: AbortSignal): Promise<Casa[]> {
  const casas: Casa[] = [];
  const limite = 100;
  while (true) {
    const pagina = await requisitar<Casa[]>(
      `/casas/?inicio=${casas.length}&limite=${limite}`,
      signal,
    );
    casas.push(...pagina);
    if (pagina.length < limite) return casas;
  }
}

export function casaInicial(casas: Casa[], preferidaId: string | null) {
  return (
    casas.find((casa) => casa.id === preferidaId) ??
    (casas.length === 1 ? casas[0] : null)
  );
}
