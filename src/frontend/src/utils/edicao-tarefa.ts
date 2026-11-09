import type { PesoTarefa, PrazoDias } from "@/constants/tarefa";
import type { Tarefa, TarefaAtualizar } from "@/services/tarefas-api";
import { dataFixaParaIso } from "./data-fixa.ts";

export type FormularioEdicaoTarefa = {
  nome: string;
  descricao: string;
  peso: PesoTarefa;
  prazoDias: PrazoDias | null;
  atrasoMaximo: number;
  dataFixa: string;
  responsavel: string;
};

export type ErrosEdicaoTarefa = Partial<
  Record<
    "nome" | "prazoDias" | "atrasoMaximo" | "dataFixa" | "responsavel",
    string
  >
>;

export function prepararEdicaoTarefa(
  formulario: FormularioEdicaoTarefa,
  tarefaOriginal: Tarefa,
  moradores: { id: string }[],
): { erros: ErrosEdicaoTarefa; dados?: TarefaAtualizar } {
  const erros: ErrosEdicaoTarefa = {};
  const nome = formulario.nome.trim();
  const usaDiaFixo = tarefaOriginal.modo_prazo === "dia_fixo";
  const dataFixaIso = usaDiaFixo
    ? dataFixaParaIso(formulario.dataFixa)
    : undefined;

  if (!nome) erros.nome = "Informe o nome da tarefa.";
  if (
    formulario.prazoDias !== null &&
    ![1, 2, 3, 4, 5].includes(formulario.prazoDias)
  )
    erros.prazoDias = "Selecione um prazo de 1 a 5 dias.";
  if (
    formulario.atrasoMaximo !== tarefaOriginal.atraso_maximo &&
    ![1, 2, 3, 4, 5].includes(formulario.atrasoMaximo)
  )
    erros.atrasoMaximo = "Selecione uma tolerância de 1 a 5 dias.";
  if (
    usaDiaFixo &&
    (formulario.dataFixa || tarefaOriginal.data_fixa) &&
    !dataFixaIso
  )
    erros.dataFixa = "Informe uma data válida no formato DD-MM-AAAA.";
  if (!moradores.some(({ id }) => id === formulario.responsavel))
    erros.responsavel = "Selecione um responsável desta casa.";

  if (Object.keys(erros).length) return { erros };

  return {
    erros,
    dados: {
      nome,
      descricao: formulario.descricao.trim(),
      peso: formulario.peso,
      ...(formulario.prazoDias !== null &&
      formulario.prazoDias !== tarefaOriginal.prazo_dias
        ? { prazo_dias: formulario.prazoDias }
        : {}),
      ...(formulario.atrasoMaximo !== tarefaOriginal.atraso_maximo
        ? { atraso_maximo: formulario.atrasoMaximo }
        : {}),
      ...(dataFixaIso && dataFixaIso !== tarefaOriginal.data_fixa
        ? { data_fixa: dataFixaIso }
        : {}),
      usuarios_atribuidos: [formulario.responsavel],
    },
  };
}
