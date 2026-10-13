import { useState } from "react";

import { CadastroScreen } from "@/components/cadastro";
import { LoginScreen } from "@/components/login";

export default function AutenticacaoScreen() {
  const [cadastroAberto, setCadastroAberto] = useState(false);
  const [emailLogin, setEmailLogin] = useState("");
  const [mensagemCadastro, setMensagemCadastro] = useState<string>();

  if (cadastroAberto) {
    return (
      <CadastroScreen
        emailInicial={emailLogin}
        onVoltar={(email) => {
          setEmailLogin(email);
          setCadastroAberto(false);
        }}
        onCadastrado={(email) => {
          setEmailLogin(email);
          setMensagemCadastro("Conta criada. Entre com seu e-mail e senha.");
          setCadastroAberto(false);
        }}
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
