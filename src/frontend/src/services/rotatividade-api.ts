import { requisitar } from "./api.ts";
import type { PesoTarefa, PrazoDias } from "@/constants/tarefa";

export type RotatividadeCriar = {
  fk_casa_id: string;
  nome: string;
  descricao: string;
  peso: PesoTarefa;
  prazo_dias: PrazoDias;
  atraso_maximo: PrazoDias;
  modo_prazo: "intervalo" | "dia_fixo";
  participantes: string[];
  dias_semana: number[];
  intervalo_semanas: number;
};

export type RotatividadeResposta = {
  id: string;
  fk_casa_id: string;
  nome: string;
  ativa: boolean;
};
export type Rotatividade = RotatividadeResposta & {
  descricao: string | null;
  dias_semana: number[];
  intervalo_semanas: number;
  prazo_dias: number;
  modo_prazo: string;
};
export type RotatividadeAtualizar = {
  nome: string;
  descricao: string;
  ativa: boolean;
};

export function listarRotatividades(casaId: string, signal?: AbortSignal) {
  const query = new URLSearchParams({ fk_casa_id: casaId });
  return requisitar<Rotatividade[]>(`/rotatividades/?${query}`, signal);
}
export function criarRotatividade(
  dados: RotatividadeCriar,
  signal?: AbortSignal,
) {
  return requisitar<RotatividadeResposta>("/rotatividades/", signal, {
    method: "POST",
    body: dados,
  });
}
export function atualizarRotatividade(
  id: string,
  dados: RotatividadeAtualizar,
  signal?: AbortSignal,
) {
  return requisitar<Rotatividade>(`/rotatividades/${id}`, signal, {
    method: "PATCH",
    body: dados,
  });
}
export function excluirRotatividade(id: string, signal?: AbortSignal) {
  return requisitar<boolean>(`/rotatividades/${id}`, signal, {
    method: "DELETE",
  });
}
