import type {
  DiaSemana,
  IntervaloSemanas,
  ModoAtribuicao,
  ModoPrazo,
  PesoTarefa,
  PrazoDias,
  TarefaDemonstracao,
} from "@/constants/tarefa";
import type { AtribuicaoTarefa } from "@/services/tarefas-api";
import { dataFixaParaIso } from "./data-fixa.ts";

export type FormularioTarefa = {
  nome: string;
  descricao: string;
  peso: PesoTarefa | null;
  dias: PrazoDias | null;
  atrasoMaximo: PrazoDias | null;
  modoPrazo: ModoPrazo;
  dataFixa: string;
  responsavel: string | null;
  modoAtribuicao?: ModoAtribuicao;
  rotativa: boolean;
  usarRoleta?: boolean;
  participantes: string[];
  diasSemana: DiaSemana[];
  semanas: IntervaloSemanas;
};

export type ErrosCriacao = Partial<
  Record<
    | "nome"
    | "peso"
    | "prazo"
    | "atrasoMaximo"
    | "dataFixa"
    | "responsavel"
    | "participantes"
    | "diasSemana"
    | "semanas",
    string
  >
>;

export function explicarPrazoTarefa(
  modoPrazo: ModoPrazo,
  dias: PrazoDias | null,
  rotativa: boolean,
): string {
  if (modoPrazo === "dia_fixo")
    return "A tarefa abre à meia-noite e vence no fim do dia escolhido.";
  if (dias === null)
    return "Selecione o prazo para saber quando a tarefa vence.";
  const prazo = `${dias} ${dias === 1 ? "dia" : "dias"}`;
  return rotativa
    ? `A tarefa abre no dia do rodízio e vence ao final de ${prazo}, contando o dia de abertura.`
    : `A tarefa abre no dia atual e vence após ${prazo}.`;
}

export function prepararTarefa(
  formulario: FormularioTarefa,
  moradores: { id: string }[],
): {
  erros: ErrosCriacao;
  tarefa?: Omit<TarefaDemonstracao, "usuarios_atribuidos"> & AtribuicaoTarefa;
} {
  const {
    nome,
    descricao,
    peso,
    dias,
    atrasoMaximo,
    modoPrazo,
    dataFixa,
    responsavel,
    modoAtribuicao,
    rotativa,
    usarRoleta,
    participantes,
    diasSemana,
    semanas,
  } = formulario;
  const erros: ErrosCriacao = {};
  const sortear = !rotativa && modoAtribuicao === "aleatorio";
  const idsValidos = new Set(moradores.map(({ id }) => id));

  if (!nome.trim()) erros.nome = "Informe o nome da tarefa.";
  if (peso === null || ![1, 2, 3].includes(peso))
    erros.peso = "Selecione um peso de 1 a 3.";
  if (dias === null || ![1, 2, 3, 4, 5].includes(dias))
    erros.prazo = "Selecione um prazo de 1 a 5 dias.";
  if (atrasoMaximo === null || ![1, 2, 3, 4, 5].includes(atrasoMaximo))
    erros.atrasoMaximo = "Selecione a tolerância de 1 a 5 dias.";
  if (modoPrazo !== "intervalo" && modoPrazo !== "dia_fixo")
    erros.dataFixa = "Selecione um modo de prazo.";
  const exigeDataFixa = !rotativa && modoPrazo === "dia_fixo";
  const dataFixaIso = exigeDataFixa ? dataFixaParaIso(dataFixa) : undefined;
  if (exigeDataFixa && !dataFixaIso)
    erros.dataFixa = "Informe uma data válida no formato DD-MM-AAAA.";
  if (rotativa) {
    if (![1, 2, 3, 4].includes(semanas)) {
      erros.semanas = "Selecione um intervalo de 1 a 4 semanas.";
    }
    if (participantes.length < 2) {
      erros.participantes =
        "Selecione pelo menos dois moradores para o rodízio.";
    } else if (
      new Set(participantes).size !== participantes.length ||
      participantes.some((id) => !idsValidos.has(id))
    ) {
      erros.participantes = "Selecione moradores diferentes desta casa.";
    }
    if (diasSemana.length === 0) {
      erros.diasSemana = "Selecione pelo menos um dia da semana.";
    } else if (
      new Set(diasSemana).size !== diasSemana.length ||
      diasSemana.some((dia) => !Number.isInteger(dia) || dia < 1 || dia > 7)
    ) {
      erros.diasSemana = "Selecione dias válidos, sem repetições.";
    }
  } else if (!sortear && (!responsavel || !idsValidos.has(responsavel))) {
    erros.responsavel = "Selecione um responsável.";
  }

  if (
    Object.keys(erros).length ||
    peso === null ||
    dias === null ||
    atrasoMaximo === null
  )
    return { erros };

  return {
    erros,
    tarefa: {
      nome: nome.trim(),
      descricao: descricao.trim(),
      peso,
      prazo_dias: dias,
      atraso_maximo: atrasoMaximo,
      modo_prazo: modoPrazo,
      ...(dataFixaIso ? { data_fixa: dataFixaIso } : {}),
      ...(sortear
        ? { modo_atribuicao: "aleatorio" }
        : {
            usuarios_atribuidos: [rotativa ? participantes[0] : responsavel!],
          }),
      rotatividade: rotativa
        ? {
            participantes: [...participantes],
            dias_semana: [...diasSemana].sort((a, b) => a - b),
            intervalo_semanas: semanas,
            ...(usarRoleta ? { usar_roleta: true } : {}),
          }
        : null,
    },
  };
}
