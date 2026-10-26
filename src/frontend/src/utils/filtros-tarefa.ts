import type { EstadoTarefa } from "@/constants/tarefa";

export type FiltroPrazo = "todos" | "hoje" | "sete_dias" | "antigas";

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
  const inicioDeHoje = new Date(agora);
  inicioDeHoje.setHours(0, 0, 0, 0);

  const fimDeHoje = new Date(agora);
  fimDeHoje.setHours(23, 59, 59, 999);

  const fimDeSeteDias = new Date(fimDeHoje);
  fimDeSeteDias.setDate(fimDeSeteDias.getDate() + 6);

  return tarefas.filter((tarefa) => {
    const prazo = new Date(tarefa.data_fim);
    const correspondeEstado =
      filtros.estado === "todos" || tarefa.estado_atual === filtros.estado;
    const correspondeResponsavel =
      filtros.responsavel === "todos" ||
      tarefa.usuarios_atribuidos.includes(filtros.responsavel);

    const correspondePrazo =
      filtros.prazo === "todos" ||
      (filtros.prazo === "hoje" &&
        prazo >= inicioDeHoje &&
        prazo <= fimDeHoje) ||
      (filtros.prazo === "sete_dias" &&
        prazo >= inicioDeHoje &&
        prazo <= fimDeSeteDias) ||
      (filtros.prazo === "antigas" && prazo < inicioDeHoje);

    return correspondeEstado && correspondeResponsavel && correspondePrazo;
  });
}

export function formatarPrazo(data: string, dataFixa?: string | null) {
  const prazo = new Date(data);
  const dia = dataFixa ? Number(dataFixa.slice(8, 10)) : prazo.getDate();
  const mes = dataFixa
    ? new Date(`${dataFixa}T00:00:00Z`).toLocaleDateString("pt-BR", {
        month: "short",
        timeZone: "UTC",
      })
    : prazo.toLocaleDateString("pt-BR", { month: "short" });
  const ano = dataFixa ? dataFixa.slice(0, 4) : String(prazo.getFullYear());
  const horario = dataFixa
    ? "23:59"
    : prazo.toLocaleTimeString("pt-BR", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
  return `${String(dia).padStart(2, "0")} ${mes} ${ano}, ${horario}`;
}
