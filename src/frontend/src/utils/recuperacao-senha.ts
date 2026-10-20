import { ErroApi } from "../services/api.ts";

export const ESPERA_REENVIO_SEGUNDOS = 30;

// Erros comuns às duas telas; cada tela trata antes os status que são só dela.
export function mensagemDeErroRecuperacao(falha: unknown, padrao: string) {
  if (falha instanceof ErroApi) {
    if (falha.status === 429) {
      const segundos = falha.retryAfter;
      return segundos
        ? `Muitas tentativas. Tente novamente em ${segundos >= 60 ? `${Math.ceil(segundos / 60)} min` : `${segundos} s`}.`
        : "Muitas tentativas. Aguarde antes de tentar novamente.";
    }
    if (falha.status === 503) {
      return "Serviço temporariamente indisponível. Tente novamente em instantes.";
    }
  }
  if (falha instanceof TypeError) {
    return "Não foi possível conectar ao servidor. Verifique sua conexão.";
  }
  return padrao;
}
