export const pesosTarefa = [1, 2, 3] as const;

export type PesoTarefa = (typeof pesosTarefa)[number];
<<<<<<< Updated upstream
=======

export const prazosTarefa = [1, 2, 3, 4, 5] as const;

export type PrazoDias = (typeof prazosTarefa)[number];

export type TarefaDemonstracao = {
  nome: string;
  descricao: string;
  peso: PesoTarefa;
  prazo_dias: PrazoDias;
  usuarios_atribuidos: [string];
};

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
>>>>>>> Stashed changes
