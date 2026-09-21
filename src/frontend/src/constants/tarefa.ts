export const pesosTarefa = [1, 2, 3] as const;

export type PesoTarefa = (typeof pesosTarefa)[number];

export const opcoesEstadoTarefa = [
  { valor: "pendente", rotulo: "Pendente" },
  { valor: "atrasada", rotulo: "Atrasada" },
  { valor: "finalizado", rotulo: "Finalizada" },
  { valor: "nao_feito", rotulo: "Não feita" },
] as const;

export type EstadoTarefa = (typeof opcoesEstadoTarefa)[number]["valor"];

export const rotulosEstado: Record<EstadoTarefa, string> = {
  pendente: "Pendente",
  atrasada: "Atrasada",
  finalizado: "Finalizada",
  nao_feito: "Não feita",
};
