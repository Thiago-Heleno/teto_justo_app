import type { EstadoTarefa } from "@/constants/tarefa";

export type FiltroPrazo = "todos" | "hoje" | "sete_dias" | "atrasadas";

type TarefaFiltravel = {
  estado_atual: EstadoTarefa;
  data_fim: string;
  usuarios_atribuidos: string[];
};

export type FiltrosTarefa = {
  estado: EstadoTarefa | "todos";
  responsavel: string | "todos";
  prazo: FiltroPrazo;
};

export function filtrarTarefas<T extends TarefaFiltravel>(
  tarefas: T[],
  filtros: FiltrosTarefa,
  agora = new Date(),
) {
  const fimDeHoje = new Date(agora);
  fimDeHoje.setHours(23, 59, 59, 999);

  const fimDeSeteDias = new Date(agora);
  fimDeSeteDias.setDate(fimDeSeteDias.getDate() + 7);

  return tarefas.filter((tarefa) => {
    const prazo = new Date(tarefa.data_fim);
    const correspondeEstado =
      filtros.estado === "todos" || tarefa.estado_atual === filtros.estado;
    const correspondeResponsavel =
      filtros.responsavel === "todos" ||
      tarefa.usuarios_atribuidos.includes(filtros.responsavel);

    const correspondePrazo =
      filtros.prazo === "todos" ||
      (filtros.prazo === "hoje" && prazo >= agora && prazo <= fimDeHoje) ||
      (filtros.prazo === "sete_dias" &&
        prazo >= agora &&
        prazo <= fimDeSeteDias) ||
      (filtros.prazo === "atrasadas" &&
        prazo < agora &&
        tarefa.estado_atual !== "finalizado");

    return correspondeEstado && correspondeResponsavel && correspondePrazo;
  });
}

export function formatarPrazo(data: string) {
  return new Date(data).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}
