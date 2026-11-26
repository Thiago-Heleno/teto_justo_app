
import type { Desempenho } from "../services/tarefas-api";
import type { PeriodoPlacar } from "./placar";

export function temSerieDiaria(
  periodo: PeriodoPlacar,
): periodo is "semanal" | "mensal" {
  return periodo === "semanal" || periodo === "mensal";
}

export function resumirDia(
  moradores: Desempenho["moradores"],
  diaSelecionado?: string,
) {
  const datas = moradores[0]?.serie.map((ponto) => ponto.data) ?? [];
  const escolhido = datas.indexOf(diaSelecionado ?? "");
  const indice = escolhido < 0 ? datas.length - 1 : escolhido;
  return {
    datas,
    indice,
    totais: moradores.map((morador) => ({
      usuario_id: morador.usuario_id,
      nome: morador.nome,
      pontos: morador.serie[indice]?.acumulado ?? morador.total,
    })),
  };
}

export function escalaPontos(valores: number[]) {
  const minimo = Math.min(0, ...valores);
  const maximo = Math.max(0, ...valores);
  return { minimo, maximo: minimo === maximo ? 1 : maximo };
}

export function proporcaoPontos(
  valor: number,
  escala: ReturnType<typeof escalaPontos>,
) {
  return (valor - escala.minimo) / (escala.maximo - escala.minimo);
}

export function posicaoDia(indice: number, quantidade: number) {
  return quantidade <= 1 ? 0.5 : indice / (quantidade - 1);
}

export function rotuloDia(data: string) {
  // A API já fornece o dia civil no fuso da casa. Não converter para UTC/local.
  return `${data.slice(8, 10)}/${data.slice(5, 7)}`;
}
