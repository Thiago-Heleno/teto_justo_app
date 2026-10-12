import type { Tarefa } from "../services/tarefas-api";

export function podeReabrirTarefa(
  tarefa: Pick<Tarefa, "estado_atual" | "usuarios_atribuidos">,
  usuarioId: string,
  donoDaCasaId: string,
) {
  return (
    tarefa.estado_atual === "finalizado" &&
    (tarefa.usuarios_atribuidos.includes(usuarioId) ||
      donoDaCasaId === usuarioId)
  );
}
