import type { EstadoTarefa } from "@/constants/tarefa";
import type { FiltrosTarefa } from "@/utils/filtros-tarefa";

export type Casa = { id: string; nome: string };

export type Morador = { id: string; nome: string };

export type Tarefa = {
  id: string;
  nome: string;
  descricao: string | null;
  estado_atual: EstadoTarefa;
  peso: number;
  data_fim: string;
  usuarios_atribuidos: string[];
};

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
): Promise<T> {
  const { apiUrl, token } = configuracao();
  const resposta = await fetch(`${apiUrl}${caminho}`, {
    headers: { Authorization: `Bearer ${token}` },
    signal,
  });

  if (!resposta.ok) {
    const corpo = await resposta.json().catch(() => null);
    throw new Error(corpo?.detail || "Não foi possível carregar as tarefas.");
  }

  return resposta.json() as Promise<T>;
}

export function carregarContextoTarefas(signal?: AbortSignal) {
  const { casaId } = configuracao();
  return Promise.all([
    requisitar<Casa>(`/casas/${casaId}`, signal),
    requisitar<Morador[]>(`/casas/${casaId}/moradores`, signal),
  ]);
}

export function carregarTarefas(filtros: FiltrosTarefa, signal?: AbortSignal) {
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
