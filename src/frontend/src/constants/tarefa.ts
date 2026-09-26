export const pesosTarefa = [1, 2, 3] as const;

export type PesoTarefa = (typeof pesosTarefa)[number];

export const prazosTarefa = [1, 2, 3, 4, 5] as const;

export type PrazoDias = (typeof prazosTarefa)[number];

export const diasSemanaTarefa = [
  { valor: 1, rotulo: "Segunda-feira", abreviacao: "Seg" },
  { valor: 2, rotulo: "Terça-feira", abreviacao: "Ter" },
  { valor: 3, rotulo: "Quarta-feira", abreviacao: "Qua" },
  { valor: 4, rotulo: "Quinta-feira", abreviacao: "Qui" },
  { valor: 5, rotulo: "Sexta-feira", abreviacao: "Sex" },
  { valor: 6, rotulo: "Sábado", abreviacao: "Sáb" },
  { valor: 7, rotulo: "Domingo", abreviacao: "Dom" },
] as const;

export type DiaSemana = (typeof diasSemanaTarefa)[number]["valor"];

export const intervalosSemanasTarefa = [1, 2, 3, 4] as const;

export type IntervaloSemanas = (typeof intervalosSemanasTarefa)[number];

export type RotatividadeTarefa = {
  participantes: string[];
  dias_semana: DiaSemana[];
  intervalo_semanas: IntervaloSemanas;
};

export type TarefaDemonstracao = {
  nome: string;
  descricao: string;
  peso: PesoTarefa;
  prazo_dias: PrazoDias;
  usuarios_atribuidos: [string];
  rotatividade: RotatividadeTarefa | null;
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
