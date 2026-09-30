import type { Placar } from "../services/tarefas-api";

export const periodosPlacar = [
  { valor: "semanal", rotulo: "Semana" },
  { valor: "mensal", rotulo: "Mês" },
  { valor: "anual", rotulo: "Ano" },
  { valor: "acumulado", rotulo: "Acumulado" },
] as const;

export type PeriodoPlacar = (typeof periodosPlacar)[number]["valor"];

export function resumirPlacar(placar: Placar, periodo: PeriodoPlacar) {
  function pontos(morador: Placar["moradores"][number]) {
    switch (periodo) {
      case "semanal":
        return morador.semanal;
      case "mensal":
        return morador.mensal;
      case "anual":
        return morador.anual;
      case "acumulado":
        return morador.acumulado;
    }
  }
  const ordenados = [...placar.moradores].sort(
    (a, b) =>
      pontos(b) - pontos(a) ||
      a.nome.localeCompare(b.nome, "pt-BR") ||
      a.usuario_id.localeCompare(b.usuario_id),
  );
  let posicao = 0;
  let anterior: number | undefined;
  const moradores = ordenados.map((morador, indice) => {
    const valor = pontos(morador);
    if (valor !== anterior) posicao = indice + 1;
    anterior = valor;
    return { ...morador, pontos: valor, posicao };
  });
  return {
    moradores,
    total: moradores.reduce((soma, morador) => soma + morador.pontos, 0),
  };
}
