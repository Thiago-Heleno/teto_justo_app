import type { EstadoTarefa } from "@/constants/tarefa";

export type FiltroPrazo = "todos" | "hoje" | "sete_dias" | "antigas";

type TarefaFiltravel = {
  estado_atual: EstadoTarefa;
  data_fim: string;
  usuarios_atribuidos: string[];
};

export type FiltrosTarefa = {
  estado: EstadoTarefa | "todos" | "em_aberto";
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
      filtros.estado === "todos" ||
      (filtros.estado === "em_aberto"
        ? tarefa.estado_atual === "pendente" ||
          tarefa.estado_atual === "atrasada"
        : tarefa.estado_atual === filtros.estado);
    const correspondeResponsavel =
      filtros.responsavel === "todos" ||
      tarefa.usuarios_atribuidos.includes(filtros.responsavel);

    const pendenciaAnterior =
      prazo < inicioDeHoje &&
      (tarefa.estado_atual === "pendente" ||
        tarefa.estado_atual === "atrasada");
    const correspondePrazo =
      filtros.prazo === "todos" ||
      (filtros.prazo === "hoje" &&
        (prazo >= inicioDeHoje || pendenciaAnterior) &&
        prazo <= fimDeHoje) ||
      (filtros.prazo === "sete_dias" &&
        (prazo >= inicioDeHoje || pendenciaAnterior) &&
        prazo <= fimDeSeteDias) ||
      (filtros.prazo === "antigas" && prazo < inicioDeHoje);

    return correspondeEstado && correspondeResponsavel && correspondePrazo;
  });
}

export function ordenarTarefas<
  T extends Pick<TarefaFiltravel, "estado_atual" | "data_fim">,
>(tarefas: T[], prazo: FiltroPrazo): T[] {
  const priorizarAbertas = prazo === "hoje" || prazo === "sete_dias";
  const prioridade: Record<EstadoTarefa, number> = {
    atrasada: 0,
    pendente: 1,
    finalizado: 2,
    nao_feito: 2,
  };

  return [...tarefas].sort(
    (a, b) =>
      (priorizarAbertas
        ? prioridade[a.estado_atual] - prioridade[b.estado_atual]
        : 0) || new Date(a.data_fim).getTime() - new Date(b.data_fim).getTime(),
  );
}

export function formatarPrazo(
  data: string,
  dataFixa: string | null | undefined,
  fuso: string,
) {
  const instante = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(data) ? data : data + "Z";
  const prazo = new Date(dataFixa ? dataFixa + "T23:59:00Z" : instante);
  const partes = new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: dataFixa ? "UTC" : fuso,
  }).formatToParts(prazo);
  const { day, month, year, hour, minute } = Object.fromEntries(
    partes.map(({ type, value }) => [type, value]),
  );
  return `${day} ${month} ${year}, ${hour}:${minute}`;
}
