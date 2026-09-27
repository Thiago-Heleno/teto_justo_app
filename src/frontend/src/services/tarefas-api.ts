import type { DiaSemana, EstadoTarefa, IntervaloSemanas, PesoTarefa, PrazoDias } from "@/constants/tarefa";
import type { FiltrosTarefa } from "@/utils/filtros-tarefa";

export type Casa = { id: string; nome: string; fk_usuario_id: string };

export type Morador = { id: string; nome: string; score: number };

export type UsuarioAtual = { id: string };

export type Tarefa = {
  id: string;
  nome: string;
  descricao: string | null;
  estado_atual: EstadoTarefa;
  peso: number;
  prazo_dias: number | null;
  atraso_maximo: number;
  tipo: "unitaria" | "rotativa";
  modo_prazo: "intervalo" | "dia_fixo";
  data_fixa: string | null;
  data_inicio: string | null;
  data_fim: string;
  usuarios_atribuidos: string[];
  concluida_em?: string | null;
  resultado_pontuacao?: {
    pontos_possiveis: number;
    pontos_ganhos: number;
    saldo_atual: number;
  } | null;
};

export type TarefaAtualizar = {
  nome: string;
  descricao: string;
  peso: number;
  prazo_dias?: number;
  atraso_maximo?: number;
  data_fixa?: string;
  usuarios_atribuidos: string[];
};

export type TarefaCriar = {
  fk_casa_id: string;
  nome: string;
  descricao: string;
  peso: PesoTarefa;
  prazo_dias: PrazoDias;
  atraso_maximo: PrazoDias;
  tipo: "unitaria";
  modo_prazo: "intervalo" | "dia_fixo";
  data_fixa?: string;
  usuarios_atribuidos: [string];
};

export type RotatividadeCriar = {
  fk_casa_id: string;
  nome: string;
  descricao: string;
  peso: PesoTarefa;
  prazo_dias: PrazoDias;
  atraso_maximo: PrazoDias;
  modo_prazo: "intervalo" | "dia_fixo";
  participantes: string[];
  dias_semana: DiaSemana[];
  intervalo_semanas: IntervaloSemanas;
};

export type Placar = {
  casa_id: string;
  fuso_horario: string;
  moradores: {
    usuario_id: string;
    nome: string;
    semanal: number;
    mensal: number;
    anual: number;
    acumulado: number;
  }[];
};

export function temConfiguracaoTarefas() {
  return Boolean(
    process.env.EXPO_PUBLIC_API_URL ||
    process.env.EXPO_PUBLIC_TETO_JUSTO_TOKEN ||
    process.env.EXPO_PUBLIC_CASA_ID,
  );
}

function configuracao() {
  const apiUrl = process.env.EXPO_PUBLIC_API_URL?.replace(/\/+$/, "");
  const token = process.env.EXPO_PUBLIC_TETO_JUSTO_TOKEN;
  const casaId = process.env.EXPO_PUBLIC_CASA_ID;

  if (!apiUrl || !token || !casaId) {
    throw new Error(
      "Configure EXPO_PUBLIC_API_URL, EXPO_PUBLIC_TETO_JUSTO_TOKEN e EXPO_PUBLIC_CASA_ID.",
    );
  }

  return { apiUrl, token, casaId };
}

async function requisitar<T>(
  caminho: string,
  signal?: AbortSignal,
  opcoes?: { method?: "GET" | "PATCH" | "POST"; body?: unknown },
): Promise<T> {
  const { apiUrl, token } = configuracao();
  const resposta = await fetch(`${apiUrl}${caminho}`, {
    method: opcoes?.method ?? "GET",
    headers: {
      Authorization: `Bearer ${token}`,
      ...(opcoes?.body ? { "Content-Type": "application/json" } : {}),
    },
    body: opcoes?.body ? JSON.stringify(opcoes.body) : undefined,
    signal,
  });

  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null);
    const detalhe = corpo?.detail;
    const mensagem = typeof detalhe === "string"
      ? detalhe
      : Array.isArray(detalhe)
        ? detalhe.map((erro: { msg?: string }) => erro.msg).filter(Boolean).join(" ")
        : "";
    throw new Error(mensagem || "Não foi possível concluir a operação.");
  }

  return resposta.json() as Promise<T>;
}

export async function carregarContextoTarefas(signal?: AbortSignal) {
  const { casaId } = configuracao();
  return Promise.all([
    requisitar<Casa>(`/casas/${casaId}`, signal),
    requisitar<Morador[]>(`/casas/${casaId}/moradores`, signal),
  ]);
}

export function carregarUsuarioAtual(signal?: AbortSignal) {
  return requisitar<UsuarioAtual>("/usuarios/eu", signal);
}

export function carregarPlacar(signal?: AbortSignal) {
  const { casaId } = configuracao();
  return requisitar<Placar>(`/casas/${casaId}/placar`, signal);
}

export function criarTarefa(dados: TarefaCriar, signal?: AbortSignal) {
  return requisitar<Tarefa>("/tarefas/", signal, { method: "POST", body: dados });
}

export function criarRotatividade(dados: RotatividadeCriar, signal?: AbortSignal) {
  return requisitar<unknown>("/rotatividades/", signal, { method: "POST", body: dados });
}

export async function carregarTarefas(
  filtros: FiltrosTarefa,
  signal?: AbortSignal,
) {
  const { casaId } = configuracao();
  const parametros = new URLSearchParams({
    estado: filtros.estado,
    prazo: filtros.prazo,
  });

  if (filtros.responsavel !== "todos") {
    parametros.set("responsavel", filtros.responsavel);
  }

  return requisitar<Tarefa[]>(
    `/tarefas/casa/${casaId}?${parametros.toString()}`,
    signal,
  );
}

export function finalizarTarefa(idTarefa: string, signal?: AbortSignal) {
  return requisitar<Tarefa>(`/tarefas/${idTarefa}`, signal, {
    method: "PATCH",
    body: { estado_atual: "finalizado" },
  });
}

export function editarTarefa(
  idTarefa: string,
  dados: TarefaAtualizar,
  signal?: AbortSignal,
) {
  return requisitar<Tarefa>(`/tarefas/${idTarefa}`, signal, {
    method: "PATCH",
    body: dados,
  });
}
