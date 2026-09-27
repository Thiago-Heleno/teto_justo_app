import type {
  DiaSemana,
  IntervaloSemanas,
  ModoPrazo,
  PesoTarefa,
  PrazoDias,
  TarefaDemonstracao,
} from "@/constants/tarefa";

export type FormularioTarefa = {
  nome: string;
  descricao: string;
  peso: PesoTarefa | null;
  dias: PrazoDias | null;
  atrasoMaximo: PrazoDias | null;
  modoPrazo: ModoPrazo;
  dataFixa: string;
  responsavel: string | null;
  rotativa: boolean;
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

function dataValida(valor: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(valor)) return false;
  const [ano, mes, dia] = valor.split("-").map(Number);
  const data = new Date(Date.UTC(ano, mes - 1, dia));
  return data.getUTCFullYear() === ano && data.getUTCMonth() === mes - 1 && data.getUTCDate() === dia;
}

export function prepararTarefa(
  formulario: FormularioTarefa,
  moradores: { id: string }[],
): { erros: ErrosCriacao; tarefa?: TarefaDemonstracao } {
  const {
    nome,
    descricao,
    peso,
    dias,
    atrasoMaximo,
    modoPrazo,
    dataFixa,
    responsavel,
    rotativa,
    participantes,
    diasSemana,
    semanas,
  } = formulario;
  const erros: ErrosCriacao = {};
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
  if (!rotativa && modoPrazo === "dia_fixo" && !dataValida(dataFixa))
    erros.dataFixa = "Informe uma data válida no formato AAAA-MM-DD.";
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
  } else if (!responsavel || !idsValidos.has(responsavel)) {
    erros.responsavel = "Selecione um responsável.";
  }

  if (Object.keys(erros).length || peso === null || dias === null || atrasoMaximo === null)
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
      ...(rotativa || modoPrazo !== "dia_fixo" ? {} : { data_fixa: dataFixa }),
      usuarios_atribuidos: [rotativa ? participantes[0] : responsavel!],
      rotatividade: rotativa
        ? {
            participantes: [...participantes],
            dias_semana: [...diasSemana].sort((a, b) => a - b),
            intervalo_semanas: semanas,
          }
        : null,
    },
  };
}
