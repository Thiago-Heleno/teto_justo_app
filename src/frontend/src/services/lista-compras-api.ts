import { requisitar } from "./api.ts";

export type ListaCompra = {
  id: string;
  fk_casa_id: string;
  nome: string;
  criado_em: string;
};

export type ItemCompra = {
  id: string;
  fk_lista_id: string;
  nome: string;
  quantidade: number;
  fk_usuario_criador_id: string;
  comprado: boolean;
  fk_usuario_comprador_id: string | null;
  comprado_em: string | null;
  criado_em: string;
};

export function listarListasCompra(casaId: string, signal?: AbortSignal) {
  return requisitar<ListaCompra[]>(`/lista/casa/${casaId}`, signal);
}

export function criarListaCompra(casaId: string, nome: string) {
  return requisitar<ListaCompra>("/lista/", undefined, {
    method: "POST",
    body: { fk_casa_id: casaId, nome: nome.trim() },
  });
}

export function renomearListaCompra(listaId: string, nome: string) {
  return requisitar<ListaCompra>(`/lista/${listaId}`, undefined, {
    method: "PATCH",
    body: { nome: nome.trim() },
  });
}

export function excluirListaCompra(listaId: string) {
  return requisitar<void>(`/lista/${listaId}`, undefined, { method: "DELETE" });
}

export function listarItensCompra(listaId: string, signal?: AbortSignal) {
  return requisitar<ItemCompra[]>(`/lista/${listaId}/itens`, signal);
}

export function criarItemCompra(
  listaId: string,
  nome: string,
  quantidade: number,
) {
  return requisitar<ItemCompra>("/lista/itens", undefined, {
    method: "POST",
    body: { fk_lista_id: listaId, nome: nome.trim(), quantidade },
  });
}

export function editarItemCompra(
  itemId: string,
  dados: { nome: string; quantidade: number },
) {
  return requisitar<ItemCompra>(`/lista/itens/${itemId}`, undefined, {
    method: "PATCH",
    body: { nome: dados.nome.trim(), quantidade: dados.quantidade },
  });
}

export function excluirItemCompra(itemId: string) {
  return requisitar<void>(`/lista/itens/${itemId}`, undefined, {
    method: "DELETE",
  });
}

export function definirItemComprado(itemId: string, comprado: boolean) {
  return requisitar<ItemCompra>(`/lista/itens/${itemId}/comprado`, undefined, {
    method: comprado ? "POST" : "DELETE",
  });
}
