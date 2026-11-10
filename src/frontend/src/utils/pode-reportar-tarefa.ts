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
