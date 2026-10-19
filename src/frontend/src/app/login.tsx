import { useState } from "react";

import { CadastroScreen } from "@/components/cadastro";
import { LoginScreen } from "@/components/login";
import { VerificacaoEmailScreen } from "@/components/verificacao-email";
import type { DadosConta } from "@/services/autenticacao-api";

export default function AutenticacaoScreen() {
  const [cadastroAberto, setCadastroAberto] = useState(false);
  const [emailLogin, setEmailLogin] = useState("");
  const [mensagemCadastro, setMensagemCadastro] = useState<string>();
  // Dados do cadastro ficam só em memória até o código ser confirmado.
  const [pendente, setPendente] = useState<{
    dados: DadosConta;
    token: string;
  }>();

  if (pendente) {
    return (
      <VerificacaoEmailScreen
        dados={pendente.dados}
        tokenInicial={pendente.token}
        onVoltar={(email) => {
          setEmailLogin(email);
          setPendente(undefined);
        }}
        onVerificado={(email) => {
          setEmailLogin(email);
          setMensagemCadastro(
            "E-mail verificado e conta criada. Entre com seu e-mail e senha.",
          );
          setPendente(undefined);
          setCadastroAberto(false);
        }}
      />
    );
  }

  if (cadastroAberto) {
    return (
      <CadastroScreen
        emailInicial={emailLogin}
        onVoltar={(email) => {
          setEmailLogin(email);
          setCadastroAberto(false);
        }}
        onCodigoEnviado={(dados, token) => setPendente({ dados, token })}
      />
    );
  }

  return (
    <LoginScreen
      emailInicial={emailLogin}
      mensagemCadastro={mensagemCadastro}
      onIniciarLogin={() => setMensagemCadastro(undefined)}
      onCriarConta={(email) => {
        setEmailLogin(email);
        setMensagemCadastro(undefined);
        setCadastroAberto(true);
      }}
    />
  );
}
