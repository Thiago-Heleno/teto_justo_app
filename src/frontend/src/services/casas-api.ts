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

export type DetalhesCasa = { casa: Casa; nomeProprietario: string | null };

type MoradorCasa = { id: string; nome: string };

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

export function sairDaCasa(casaId: string, signal?: AbortSignal) {
  return requisitar<void>(`/casas/${casaId}/sair`, signal, {
    method: "DELETE",
  });
}

export async function carregarDetalhesCasa(
  casaId: string,
  signal?: AbortSignal,
): Promise<DetalhesCasa> {
  const [respostaCasa, respostaMoradores] = await Promise.allSettled([
    requisitar<Casa>(`/casas/${casaId}`, signal),
    requisitar<MoradorCasa[]>(`/casas/${casaId}/moradores`, signal),
  ]);

  if (respostaCasa.status === "rejected") throw respostaCasa.reason;

  const casa = respostaCasa.value;
  const nomeProprietario =
    respostaMoradores.status === "fulfilled"
      ? (respostaMoradores.value.find(
          (morador) => morador.id === casa.fk_usuario_id,
        )?.nome ?? null)
      : null;

  return { casa, nomeProprietario };
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
