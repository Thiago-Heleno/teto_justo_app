import type { EstadoTarefa } from "@/constants/tarefa";
import type { FiltrosTarefa } from "@/utils/filtros-tarefa";

export type Casa = { id: string; nome: string };

export type Morador = { id: string; nome: string; score: number };

export type Tarefa = {
  id: string;
  nome: string;
  descricao: string | null;
  estado_atual: EstadoTarefa;
  peso: number;
  data_fim: string;
  usuarios_atribuidos: string[];
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
  opcoes?: { method?: "GET" | "PATCH"; body?: unknown },
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
    throw new Error(corpo?.detail || "Não foi possível carregar as tarefas.");
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
