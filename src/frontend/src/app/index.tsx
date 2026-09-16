import { useState } from "react";
import { View, Text, TextInput, Pressable, StyleSheet } from "react-native";

export default function HomeScreen() {
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [telefone, setTelefone] = useState("");
  const [senha, setSenha] = useState("");

  function cadastrarUsuario() {
    console.log({
      nome,
      email,
      telefone,
      senha,
    });
  }

  return (
    <View style={styles.container}>
      <Text style={styles.titulo}>Teto Justo</Text>
      <Text style={styles.subtitulo}>Cadastro de usuário</Text>

      <Text style={styles.label}>Nome</Text>
      <TextInput
        style={styles.input}
        placeholder="Digite seu nome"
        placeholderTextColor="#888"
        value={nome}
        onChangeText={setNome}
      />

      <Text style={styles.label}>E-mail</Text>
      <TextInput
        style={styles.input}
        placeholder="Digite seu e-mail"
        placeholderTextColor="#888"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
      />

      <Text style={styles.label}>Telefone</Text>
      <TextInput
        style={styles.input}
        placeholder="Digite seu telefone"
        placeholderTextColor="#888"
        value={telefone}
        onChangeText={setTelefone}
        keyboardType="phone-pad"
      />

      <Text style={styles.label}>Senha</Text>
      <TextInput
        style={styles.input}
        placeholder="Digite sua senha"
        placeholderTextColor="#888"
        value={senha}
        onChangeText={setSenha}
        secureTextEntry
      />

      <Pressable style={styles.botao} onPress={cadastrarUsuario}>
        <Text style={styles.textoBotao}>Cadastrar</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 24,
    justifyContent: "center",
  },

  titulo: {
    fontSize: 32,
    fontWeight: "bold",
    color: "white",
    marginBottom: 8,
  },

  subtitulo: {
    fontSize: 20,
    color: "white",
    marginBottom: 24,
  },

  label: {
    color: "white",
    marginBottom: 6,
  },

  input: {
    backgroundColor: "white",
    color: "black",
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },

  botao: {
    backgroundColor: "#2e7d32",
    padding: 14,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 8,
  },

  textoBotao: {
    color: "white",
    fontWeight: "bold",
    fontSize: 16,
  },
});
