import { useState } from "react";

function App() {
  // Estados que vão guardar o que o usuário digitar
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [telefone, setTelefone] = useState("");
  const [senha, setSenha] = useState("");

  function cadastrarUsuario(e) {
    e.preventDefault();

    console.log({
      nome,
      email,
      telefone,
      senha,
    });
  }

  return (
    <div>
      <h1>Teto Justo</h1>

      <h2>Cadastro de usuário</h2>

      <form onSubmit={cadastrarUsuario}>
        <div>
          <label>Nome</label>
          <input
            type="text"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            placeholder="Digite seu nome"
          />
        </div>

        <div>
          <label>E-mail</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Digite seu e-mail"
          />
        </div>

        <div>
          <label>Telefone</label>
          <input
            type="text"
            value={telefone}
            onChange={(e) => setTelefone(e.target.value)}
            placeholder="Digite seu telefone"
          />
        </div>

        <div>
          <label>Senha</label>
          <input
            type="password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            placeholder="Digite sua senha"
          />
        </div>

        <button type="submit">Cadastrar</button>
      </form>
    </div>
  );
}

export default App;