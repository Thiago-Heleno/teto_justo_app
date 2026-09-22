import type { EstadoTarefa, PesoTarefa } from "@/constants/tarefa";

export const casaDemonstracao = {
  id: "casa-teste",
  nome: "República Girassol",
};

export const usuarioDemonstracaoId = "morador-ana";

export const moradoresDemonstracao = [
  { id: usuarioDemonstracaoId, nome: "Ana Silva", iniciais: "AS" },
  { id: "morador-bruno", nome: "Bruno Costa", iniciais: "BC" },
  { id: "morador-carla", nome: "Carla Souza", iniciais: "CS" },
];

export type TarefaCasaDemonstracao = {
  id: string;
  nome: string;
  descricao: string;
  peso: PesoTarefa;
  data_fim: string;
  usuarios_atribuidos: [string];
  estado_atual: EstadoTarefa;
};

function prazoEm({ dias = 0, horas = 0 }) {
  const prazo = new Date();
  prazo.setDate(prazo.getDate() + dias);
  prazo.setHours(prazo.getHours() + horas, 0, 0, 0);
  return prazo.toISOString();
}

export const tarefasDemonstracao: TarefaCasaDemonstracao[] = [
  {
    id: "tarefa-cozinha",
    nome: "Limpar a cozinha",
    descricao:
      "Lavar a louça, limpar o fogão e deixar a bancada livre para o jantar.",
    peso: 3,
    data_fim: prazoEm({ horas: 4 }),
    usuarios_atribuidos: [usuarioDemonstracaoId],
    estado_atual: "pendente",
  },
  {
    id: "tarefa-lixo",
    nome: "Levar o lixo reciclável",
    descricao: "Separar papel, plástico e vidro antes de levar à coleta.",
    peso: 1,
    data_fim: prazoEm({ dias: -1 }),
    usuarios_atribuidos: ["morador-bruno"],
    estado_atual: "atrasada",
  },
  {
    id: "tarefa-mercado",
    nome: "Comprar produtos de limpeza",
    descricao: "Comprar detergente, esponjas e sacos de lixo para a casa.",
    peso: 2,
    data_fim: prazoEm({ dias: 3 }),
    usuarios_atribuidos: ["morador-carla"],
    estado_atual: "pendente",
  },
  {
    id: "tarefa-contas",
    nome: "Revisar as contas do mês",
    descricao: "Conferir os valores de água, energia e internet.",
    peso: 2,
    data_fim: prazoEm({ dias: 2 }),
    usuarios_atribuidos: [usuarioDemonstracaoId],
    estado_atual: "finalizado",
  },
  {
    id: "tarefa-banheiro",
    nome: "Limpar o banheiro social",
    descricao: "Higienizar pia, vaso, box e repor o papel higiênico.",
    peso: 3,
    data_fim: prazoEm({ dias: -3 }),
    usuarios_atribuidos: [usuarioDemonstracaoId],
    estado_atual: "nao_feito",
  },
];
