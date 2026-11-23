import { requisitar } from "./api.ts";

export type RegraCasa = {
  id: string;
  fk_casa_id: string;
  titulo: string;
  descricao: string | null;
  valor_multa_centavos: number;
  ativa: boolean;
  criado_em: string;
};

export type RegraCasaCriar = {
  fk_casa_id: string;
  titulo: string;
  descricao?: string;
  valor_multa_centavos: number;
};

export type RegraCasaAtualizar = {
  titulo?: string;
  descricao?: string | null;
  valor_multa_centavos?: number;
  ativa?: boolean;
};

export type MultaCasa = {
  id: string;
  fk_casa_id: string;
  fk_regra_id: string;
  titulo_regra: string;
  fk_usuario_multado_id: string;
  fk_usuario_aplicador_id: string;
  valor_centavos: number;
  observacao: string | null;
  paga: boolean;
  pago_em: string | null;
  criado_em: string;
};

export type MultaCasaCriar = {
  fk_casa_id: string;
  fk_regra_id: string;
  fk_usuario_multado_id: string;
  observacao?: string;
};

export function listarRegrasCasa(casaId: string, signal?: AbortSignal) {
  return requisitar<RegraCasa[]>(`/regras-casa/casa/${casaId}`, signal);
}

export function criarRegraCasa(dados: RegraCasaCriar) {
  const descricao = dados.descricao?.trim();
  return requisitar<RegraCasa>("/regras-casa/", undefined, {
    method: "POST",
    body: {
      fk_casa_id: dados.fk_casa_id,
      titulo: dados.titulo.trim(),
      ...(descricao ? { descricao } : {}),
      valor_multa_centavos: dados.valor_multa_centavos,
    },
  });
}

export function atualizarRegraCasa(regraId: string, dados: RegraCasaAtualizar) {
  const corpo: Record<string, unknown> = {};
  if (dados.titulo !== undefined) corpo.titulo = dados.titulo.trim();
  if (dados.descricao !== undefined) {
    const limpa = dados.descricao === null ? "" : dados.descricao.trim();
    corpo.descricao = limpa || null;
  }
  if (dados.valor_multa_centavos !== undefined) {
    corpo.valor_multa_centavos = dados.valor_multa_centavos;
  }
  if (dados.ativa !== undefined) corpo.ativa = dados.ativa;

  return requisitar<RegraCasa>(`/regras-casa/${regraId}`, undefined, {
    method: "PATCH",
    body: corpo,
  });
}

export function excluirRegraCasa(regraId: string) {
  return requisitar<void>(`/regras-casa/${regraId}`, undefined, {
    method: "DELETE",
  });
}

export function listarMultasCasa(casaId: string, signal?: AbortSignal) {
  return requisitar<MultaCasa[]>(`/regras-casa/casa/${casaId}/multas`, signal);
}

export function aplicarMultaCasa(dados: MultaCasaCriar) {
  const observacao = dados.observacao?.trim();
  return requisitar<MultaCasa>("/regras-casa/multas", undefined, {
    method: "POST",
    body: {
      fk_casa_id: dados.fk_casa_id,
      fk_regra_id: dados.fk_regra_id,
      fk_usuario_multado_id: dados.fk_usuario_multado_id,
      ...(observacao ? { observacao } : {}),
    },
  });
}

export function definirMultaPaga(multaId: string, paga: boolean) {
  return requisitar<MultaCasa>(
    `/regras-casa/multas/${multaId}/pagar`,
    undefined,
    {
      method: paga ? "POST" : "DELETE",
    },
  );
}

export function excluirMultaCasa(multaId: string) {
  return requisitar<void>(`/regras-casa/multas/${multaId}`, undefined, {
    method: "DELETE",
  });
}
