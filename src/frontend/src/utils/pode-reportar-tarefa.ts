import type { Tarefa } from "@/services/tarefas-api";

const JANELA_REPORTAGEM_MS = 24 * 60 * 60 * 1000;

export function podeReportarTarefa(
  tarefa: Pick<Tarefa, "estado_atual" | "concluida_em" | "politica_reclamacao">,
  usuarioId: string,
  donoDaCasaId: string,
  agora = Date.now(),
) {
  if (
    tarefa.estado_atual !== "finalizado" ||
    tarefa.politica_reclamacao === "nenhuma" ||
    usuarioId === donoDaCasaId ||
    !tarefa.concluida_em
  ) {
    return false;
  }

  const concluidaEm = new Date(tarefa.concluida_em).getTime();
  return (
    Number.isFinite(concluidaEm) &&
    agora >= concluidaEm &&
    agora - concluidaEm < JANELA_REPORTAGEM_MS
  );
}
