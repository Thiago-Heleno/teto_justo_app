import type { MultaCasa } from "../services/regras-casa-api.ts";

export type FiltroMultas = "todas" | "pendentes" | "pagas";

const MAX_INT4 = 2147483647;
const formatadorBrl = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
});

export function valorParaCentavos(texto: string): number | null {
  const semPrefixo = texto.trim().replace(/^R\$\s*/i, "");
  const correspondencia = /^(\d+)(?:[.,](\d{1,2}))?$/.exec(semPrefixo);
  if (!correspondencia) return null;

  const reais = Number(correspondencia[1]);
  const centavos = Number((correspondencia[2] ?? "").padEnd(2, "0"));
  const total = reais * 100 + centavos;
  return Number.isSafeInteger(total) && total > 0 && total <= MAX_INT4
    ? total
    : null;
}

export function formatarCentavos(centavos: number): string {
  return formatadorBrl.format(centavos / 100);
}

export function centavosParaEntrada(centavos: number): string {
  return (centavos / 100).toFixed(2).replace(".", ",");
}

export function filtrarMultas(
  multas: MultaCasa[],
  filtro: FiltroMultas,
): MultaCasa[] {
  if (filtro === "pendentes") return multas.filter((multa) => !multa.paga);
  if (filtro === "pagas") return multas.filter((multa) => multa.paga);
  return multas;
}

export function resumirMultas(multas: MultaCasa[], usuarioId?: string) {
  let totalPendenteCentavos = 0;
  let totalPagoCentavos = 0;
  let quantidadePendentes = 0;
  let minhasPendentesCentavos = 0;
  let minhasPendentesCount = 0;

  for (const multa of multas) {
    if (multa.paga) {
      totalPagoCentavos += multa.valor_centavos;
      continue;
    }
    totalPendenteCentavos += multa.valor_centavos;
    quantidadePendentes += 1;
    if (usuarioId && multa.fk_usuario_multado_id === usuarioId) {
      minhasPendentesCentavos += multa.valor_centavos;
      minhasPendentesCount += 1;
    }
  }

  return {
    totalPendenteCentavos,
    totalPagoCentavos,
    quantidadePendentes,
    minhasPendentesCentavos,
    minhasPendentesCount,
  };
}
