import type { PesoTarefa } from "@/constants/tarefa";
import type { Tarefa, TarefaAtualizar } from "@/services/tarefas-api";

export type FormularioEdicaoTarefa = {
  nome: string;
  descricao: string;
  peso: PesoTarefa;
  dataFim: string;
  responsavel: string;
};

export type ErrosEdicaoTarefa = Partial<
  Record<"nome" | "dataFim" | "responsavel", string>
>;

export function dataTarefaParaCampo(dataFim: string) {
  return dataFim.slice(0, 10);
}

function dataValida(valor: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(valor)) return false;
  const [ano, mes, dia] = valor.split("-").map(Number);
  const data = new Date(Date.UTC(ano, mes - 1, dia));
  return (
    data.getUTCFullYear() === ano &&
    data.getUTCMonth() === mes - 1 &&
    data.getUTCDate() === dia
  );
}

export function prepararEdicaoTarefa(
  formulario: FormularioEdicaoTarefa,
  tarefaOriginal: Tarefa,
  moradores: { id: string }[],
  agora = new Date(),
): { erros: ErrosEdicaoTarefa; dados?: TarefaAtualizar } {
  const erros: ErrosEdicaoTarefa = {};
  const nome = formulario.nome.trim();
  const dataOriginal = dataTarefaParaCampo(tarefaOriginal.data_fim);

  if (!nome) erros.nome = "Informe o nome da tarefa.";
  if (!dataValida(formulario.dataFim)) {
    erros.dataFim = "Informe uma data válida no formato AAAA-MM-DD.";
  } else if (formulario.dataFim !== dataOriginal) {
    const novoFim = new Date(`${formulario.dataFim}T23:59:59.999Z`);
    if (novoFim <= agora) erros.dataFim = "O novo prazo deve estar no futuro.";
  }
  if (!moradores.some(({ id }) => id === formulario.responsavel)) {
    erros.responsavel = "Selecione um responsável desta casa.";
  }

  if (Object.keys(erros).length) return { erros };

  return {
    erros,
    dados: {
      nome,
      descricao: formulario.descricao.trim(),
      peso: formulario.peso,
      data_fim:
        formulario.dataFim === dataOriginal
          ? tarefaOriginal.data_fim
          : `${formulario.dataFim}T23:59:59.999Z`,
      usuarios_atribuidos: [formulario.responsavel],
    },
  };
}
