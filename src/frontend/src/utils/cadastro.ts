export type DadosCadastro = {
  nome: string;
  email: string;
  senha: string;
  confirmacao: string;
};

export type ErrosCadastro = Partial<Record<keyof DadosCadastro, string>>;

export function validarPerfil(dados: Pick<DadosCadastro, "nome" | "email">) {
  const erros: ErrosCadastro = {};

  if (!dados.nome.trim()) erros.nome = "Informe seu nome.";
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(dados.email.trim())) {
    erros.email = "Informe um e-mail válido.";
  }
  return erros;
}

export const TAMANHO_CODIGO = 5;

export function somenteDigitosDoCodigo(valor: string) {
  return valor.replace(/\D/g, "").slice(0, TAMANHO_CODIGO);
}

export function validarCadastro(dados: DadosCadastro): ErrosCadastro {
  const erros = validarPerfil(dados);

  if (!dados.senha.trim()) erros.senha = "Informe uma senha.";
  if (!dados.confirmacao) {
    erros.confirmacao = "Confirme sua senha.";
  } else if (dados.senha !== dados.confirmacao) {
    erros.confirmacao = "As senhas não coincidem.";
  }

  return erros;
}
