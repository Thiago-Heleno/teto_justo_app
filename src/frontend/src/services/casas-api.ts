import { requisitar } from "./api.ts";

export type Casa = {
  id: string;
  nome: string;
  endereco: string;
  foto: string | null;
  fk_usuario_id: string;
  timezone: string;
};

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
