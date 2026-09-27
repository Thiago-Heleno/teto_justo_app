import type { PesoTarefa, PrazoDias } from "@/constants/tarefa";
import type { Tarefa, TarefaAtualizar } from "@/services/tarefas-api";

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
  Record<"nome" | "prazoDias" | "atrasoMaximo" | "dataFixa" | "responsavel", string>
>;

function dataValida(valor: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(valor)) return false;
  const [ano, mes, dia] = valor.split("-").map(Number);
  const data = new Date(Date.UTC(ano, mes - 1, dia));
  return data.getUTCFullYear() === ano && data.getUTCMonth() === mes - 1 && data.getUTCDate() === dia;
}

export function prepararEdicaoTarefa(
  formulario: FormularioEdicaoTarefa,
  tarefaOriginal: Tarefa,
  moradores: { id: string }[],
): { erros: ErrosEdicaoTarefa; dados?: TarefaAtualizar } {
  const erros: ErrosEdicaoTarefa = {};
  const nome = formulario.nome.trim();

  if (!nome) erros.nome = "Informe o nome da tarefa.";
  if (formulario.prazoDias !== null && ![1, 2, 3, 4, 5].includes(formulario.prazoDias))
    erros.prazoDias = "Selecione um prazo de 1 a 5 dias.";
  if (formulario.atrasoMaximo !== tarefaOriginal.atraso_maximo && ![1, 2, 3, 4, 5].includes(formulario.atrasoMaximo))
    erros.atrasoMaximo = "Selecione uma tolerância de 1 a 5 dias.";
  if (tarefaOriginal.tipo === "unitaria" && tarefaOriginal.modo_prazo === "dia_fixo" &&
      formulario.dataFixa !== (tarefaOriginal.data_fixa ?? "") && !dataValida(formulario.dataFixa))
    erros.dataFixa = "Informe uma data válida no formato AAAA-MM-DD.";
  if (!moradores.some(({ id }) => id === formulario.responsavel))
    erros.responsavel = "Selecione um responsável desta casa.";

  if (Object.keys(erros).length) return { erros };

  return {
    erros,
    dados: {
      nome,
      descricao: formulario.descricao.trim(),
      peso: formulario.peso,
      ...(formulario.prazoDias !== null && formulario.prazoDias !== tarefaOriginal.prazo_dias
        ? { prazo_dias: formulario.prazoDias } : {}),
      ...(formulario.atrasoMaximo !== tarefaOriginal.atraso_maximo
        ? { atraso_maximo: formulario.atrasoMaximo } : {}),
      ...(tarefaOriginal.tipo === "unitaria" && tarefaOriginal.modo_prazo === "dia_fixo" &&
        formulario.dataFixa !== (tarefaOriginal.data_fixa ?? "")
        ? { data_fixa: formulario.dataFixa } : {}),
      usuarios_atribuidos: [formulario.responsavel],
    },
  };
}
