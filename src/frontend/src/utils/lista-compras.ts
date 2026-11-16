import type { ItemCompra } from "../services/lista-compras-api.ts";

export function quantidadeValida(texto: string): number | null {
  const valor = texto.trim();
  if (!/^[1-9]\d*$/.test(valor)) return null;
  const numero = Number(valor);
  return Number.isSafeInteger(numero) && numero <= 2147483647 ? numero : null;
}

export function agruparItensCompra(itens: ItemCompra[]) {
  return {
    pendentes: itens.filter((item) => !item.comprado),
    comprados: itens.filter((item) => item.comprado),
  };
}
