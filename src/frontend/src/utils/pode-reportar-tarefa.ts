
import type { PoliticaReclamacao } from "@/services/casas-api";

export const JANELA_REPORTAGEM_MS = 24 * 60 * 60 * 1000;

export function podeReportarTarefa(
  concluidaEm: string,
  politica: PoliticaReclamacao,
  ehResponsavel: boolean,
  agora = Date.now(),
) {
  const idade = agora - Date.parse(concluidaEm);
  return (
    !ehResponsavel &&
    (politica === "uma_reclamacao" || politica === "votacao") &&
    idade >= 0 &&
    idade <= JANELA_REPORTAGEM_MS
  );
}

export function podeParticiparDoReport(
  usuarioId: string | undefined,
  moradoresIds: readonly string[],
  administradorId: string | undefined,
) {
  return Boolean(
    usuarioId &&
      (usuarioId === administradorId || moradoresIds.includes(usuarioId)),
  );
}

export function contarVotantesPossiveis(
  moradoresIds: readonly string[],
  administradorId: string | undefined,
  responsaveisIds: readonly string[],
) {
  const moradores = new Set(moradoresIds);
  if (administradorId) moradores.add(administradorId);
  return [...moradores].filter((id) => !responsaveisIds.includes(id)).length;
}
