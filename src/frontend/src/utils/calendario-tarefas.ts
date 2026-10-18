import type { Tarefa } from "@/services/tarefas-api";

export function dataNoFuso(data: Date | string, fuso: string) {
  const partes = new Intl.DateTimeFormat("en", {
    timeZone: fuso,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(data));

  return ["year", "month", "day"]
    .map((tipo) => partes.find((parte) => parte.type === tipo)!.value)
    .join("-");
}

export function mudarMes(mes: string, deslocamento: number) {
  const data = new Date(`${mes}-01T12:00:00Z`);
  data.setUTCMonth(data.getUTCMonth() + deslocamento);
  return data.toISOString().slice(0, 7);
}

export function diasDoMes(mes: string): (string | null)[] {
  const primeiro = new Date(`${mes}-01T12:00:00Z`);
  const ultimo = new Date(`${mudarMes(mes, 1)}-01T12:00:00Z`);
  ultimo.setUTCDate(0);
  const inicio = primeiro.getUTCDay();
  const quantidade = ultimo.getUTCDate();
  const celulas = Math.ceil((inicio + quantidade) / 7) * 7;

  return Array.from({ length: celulas }, (_, indice) => {
    const dia = indice - inicio + 1;
    return dia >= 1 && dia <= quantidade
      ? `${mes}-${String(dia).padStart(2, "0")}`
      : null;
  });
}

export function agruparTarefasAtivas(tarefas: Tarefa[], fuso: string) {
  const porDia = new Map<string, Tarefa[]>();
  const ativas = tarefas
    .filter(
      ({ estado_atual }) =>
        estado_atual === "pendente" || estado_atual === "atrasada",
    )
    .sort(
      (a, b) => new Date(a.data_fim).getTime() - new Date(b.data_fim).getTime(),
    );

  for (const tarefa of ativas) {
    const dia = tarefa.data_fixa ?? dataNoFuso(tarefa.data_fim, fuso);
    const tarefasDoDia = porDia.get(dia) ?? [];
    tarefasDoDia.push(tarefa);
    porDia.set(dia, tarefasDoDia);
  }

  return porDia;
}
