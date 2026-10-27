import { useEffect, useRef, useState } from "react";
import {
  ActivityIndicator,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { TestarNotificacoes } from "@/components/testar-notificacoes";
import { Caldera } from "@/constants/theme";
import { ErroApi } from "@/services/api";
import {
  ativarNotificacoes,
  notificacoesAtivas,
} from "@/services/notificacoes";
import {
  atualizarPerfil,
  carregarPerfil,
  excluirConta,
  type Perfil,
} from "@/services/perfil-api";
import { validarPerfil, type ErrosCadastro } from "@/utils/cadastro";

function mensagemDe(falha: unknown, padrao: string) {
  if (falha instanceof ErroApi) return falha.message;
  if (falha instanceof TypeError) {
    return "Não foi possível conectar ao servidor. Verifique sua conexão.";
  }
  return padrao;
}

export function PerfilUsuario({ onVoltar }: { onVoltar?: () => void }) {
  const [perfil, setPerfil] = useState<Perfil>();
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [errosCampos, setErrosCampos] = useState<ErrosCadastro>({});
  const [erro, setErro] = useState<string>();
  const [aviso, setAviso] = useState<string>();
  const [carregando, setCarregando] = useState(true);
  const [tentativa, setTentativa] = useState(0);
  const [ocupado, setOcupado] = useState(false);
  const [confirmacaoAberta, setConfirmacaoAberta] = useState(false);
  const [pushAtivo, setPushAtivo] = useState(false);
  const [ativandoPush, setAtivandoPush] = useState(false);
  const emAndamento = useRef(false);

  useEffect(() => {
    const controlador = new AbortController();
    carregarPerfil(controlador.signal)
      .then((dados) => {
        if (controlador.signal.aborted) return;
        setPerfil(dados);
        setNome(dados.nome);
        setEmail(dados.email);
        setErro(undefined);
      })
      .catch((falha) => {
        if (!controlador.signal.aborted) {
          setErro(mensagemDe(falha, "Não foi possível carregar seu perfil."));
        }
      })
      .finally(() => {
        if (!controlador.signal.aborted) setCarregando(false);
      });
    return () => controlador.abort();
  }, [tentativa]);

  useEffect(() => {
    void notificacoesAtivas()
      .then(setPushAtivo)
      .catch(() => {});
  }, []);

  async function ativarPush() {
    if (ativandoPush) return;
    setAtivandoPush(true);
    setErro(undefined);
    try {
      if (await ativarNotificacoes()) {
        setPushAtivo(true);
        setAviso("Notificações ativadas neste aparelho.");
      } else {
        setErro(
          "Permita notificações nas configurações do aparelho para ativar os avisos.",
        );
      }
    } catch (falha) {
      setErro(mensagemDe(falha, "Não foi possível ativar as notificações."));
    } finally {
      setAtivandoPush(false);
    }
  }

  const alterado =
    perfil !== undefined &&
    (nome.trim() !== perfil.nome || email.trim() !== perfil.email);

  async function salvar() {
    if (emAndamento.current || !perfil || !alterado) return;
    const validacao = validarPerfil({ nome, email });
    setErrosCampos(validacao);
    setErro(undefined);
    setAviso(undefined);
    if (Object.keys(validacao).length) return;

    emAndamento.current = true;
    setOcupado(true);
    try {
      const atualizado = await atualizarPerfil(perfil.id, {
        ...(nome.trim() !== perfil.nome && { nome: nome.trim() }),
        ...(email.trim() !== perfil.email && { email: email.trim() }),
      });
      setPerfil(atualizado);
      setNome(atualizado.nome);
      setEmail(atualizado.email);
      setAviso("Dados atualizados.");
    } catch (falha) {
      if (falha instanceof ErroApi && falha.status === 400) {
        setErrosCampos({ email: falha.message });
      } else if (!(falha instanceof ErroApi && falha.status === 401)) {
        setErro(mensagemDe(falha, "Não foi possível salvar seus dados."));
      }
    } finally {
      emAndamento.current = false;
      setOcupado(false);
    }
  }

  async function confirmarExclusao() {
    if (emAndamento.current || !perfil) return;
    emAndamento.current = true;
    setOcupado(true);
    setErro(undefined);
    setAviso(undefined);
    try {
      await excluirConta(perfil.id);
      // A sessão encerrada troca esta tela pelo login; não há estado a atualizar.
      return;
    } catch (falha) {
      if (!(falha instanceof ErroApi && falha.status === 401)) {
        setErro(mensagemDe(falha, "Não foi possível excluir sua conta."));
      }
    }
    emAndamento.current = false;
    setOcupado(false);
    setConfirmacaoAberta(false);
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.page}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.content}>
          <Text style={styles.brand}>TETO JUSTO</Text>
          <Text accessibilityRole="header" style={styles.title}>
            Meu perfil
          </Text>

          {carregando && (
            <ActivityIndicator accessibilityLabel="Carregando perfil" />
          )}

          {perfil && (
            <>
              <Text style={styles.label}>Nome</Text>
              <TextInput
                accessibilityLabel="Nome"
                style={[styles.input, errosCampos.nome && styles.inputError]}
                value={nome}
                onChangeText={(valor) => {
                  setNome(valor);
                  setErrosCampos((atuais) => ({ ...atuais, nome: undefined }));
                  setAviso(undefined);
                }}
                autoComplete="name"
                autoCapitalize="words"
                editable={!ocupado}
              />
              {errosCampos.nome && (
                <Text accessibilityRole="alert" style={styles.error}>
                  {errosCampos.nome}
                </Text>
              )}

              <Text style={styles.label}>E-mail</Text>
              <TextInput
                accessibilityLabel="E-mail"
                style={[styles.input, errosCampos.email && styles.inputError]}
                value={email}
                onChangeText={(valor) => {
                  setEmail(valor);
                  setErrosCampos((atuais) => ({
                    ...atuais,
                    email: undefined,
                  }));
                  setAviso(undefined);
                }}
                autoCapitalize="none"
                autoCorrect={false}
                autoComplete="email"
                keyboardType="email-address"
                editable={!ocupado}
                onSubmitEditing={() => void salvar()}
              />
              {errosCampos.email && (
                <Text accessibilityRole="alert" style={styles.error}>
                  {errosCampos.email}
                </Text>
              )}
            </>
          )}

          {erro && (
            <Text accessibilityRole="alert" style={styles.error}>
              {erro}
            </Text>
          )}
          {aviso && (
            <Text accessibilityRole="alert" style={styles.aviso}>
              {aviso}
            </Text>
          )}

          {erro && !perfil && !carregando && (
            <Pressable
              accessibilityRole="button"
              onPress={() => {
                setErro(undefined);
                setCarregando(true);
                setTentativa((valor) => valor + 1);
              }}
              style={styles.button}
            >
              <Text style={styles.buttonText}>Tentar novamente</Text>
            </Pressable>
          )}

          {perfil && (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{
                disabled: ocupado || !alterado,
                busy: ocupado,
              }}
              disabled={ocupado || !alterado}
              onPress={() => void salvar()}
              style={[
                styles.button,
                styles.primary,
                (ocupado || !alterado) && styles.dimmed,
              ]}
            >
              <Text style={[styles.buttonText, styles.primaryText]}>
                Salvar alterações
              </Text>
            </Pressable>
          )}

          {perfil && Platform.OS !== "web" && (
            <Pressable
              accessibilityRole="button"
              accessibilityState={{
                disabled: pushAtivo || ativandoPush,
                busy: ativandoPush,
              }}
              disabled={pushAtivo || ativandoPush}
              onPress={() => void ativarPush()}
              style={[
                styles.button,
                (pushAtivo || ativandoPush) && styles.dimmed,
              ]}
            >
              <Text style={styles.buttonText}>
                {pushAtivo ? "Notificações ativas" : "Ativar notificações"}
              </Text>
            </Pressable>
          )}

          {perfil && <TestarNotificacoes usuarioId={perfil.id} />}

          <View style={styles.actions}>
            {onVoltar && (
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ disabled: ocupado }}
                disabled={ocupado}
                onPress={onVoltar}
                style={[styles.button, ocupado && styles.dimmed]}
              >
                <Text style={styles.buttonText}>Voltar</Text>
              </Pressable>
            )}
            {perfil && (
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ disabled: ocupado }}
                disabled={ocupado}
                onPress={() => setConfirmacaoAberta(true)}
                style={[styles.button, styles.danger, ocupado && styles.dimmed]}
              >
                <Text style={styles.dangerText}>Excluir conta</Text>
              </Pressable>
            )}
          </View>
        </View>
      </ScrollView>
      <Modal
        animationType="fade"
        onRequestClose={() => {
          if (!ocupado) setConfirmacaoAberta(false);
        }}
        transparent
        visible={confirmacaoAberta}
      >
        <View style={styles.modalBackdrop}>
          <View accessibilityViewIsModal style={styles.modalCard}>
            <Text accessibilityRole="header" style={styles.modalTitle}>
              Excluir sua conta?
            </Text>
            <Text style={styles.description}>
              Esta ação não pode ser desfeita. Se você for proprietário de uma
              casa, exclua a casa antes.
            </Text>
            <View style={styles.actions}>
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ disabled: ocupado }}
                disabled={ocupado}
                onPress={() => setConfirmacaoAberta(false)}
                style={[styles.button, ocupado && styles.dimmed]}
              >
                <Text style={styles.buttonText}>Cancelar</Text>
              </Pressable>
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ disabled: ocupado, busy: ocupado }}
                disabled={ocupado}
                onPress={() => void confirmarExclusao()}
                style={[styles.button, styles.danger, ocupado && styles.dimmed]}
              >
                <Text style={styles.dangerText}>
                  {ocupado ? "Excluindo…" : "Excluir conta"}
                </Text>
              </Pressable>
            </View>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Caldera.limestone },
  page: { flexGrow: 1, justifyContent: "center", padding: 24 },
  content: { width: "100%", maxWidth: 480, alignSelf: "center", gap: 8 },
  brand: {
    color: Caldera.ember,
    fontWeight: "800",
    letterSpacing: 2,
    marginBottom: 16,
  },
  title: {
    color: Caldera.obsidian,
    fontSize: 36,
    fontWeight: "800",
    marginBottom: 16,
  },
  label: { color: Caldera.obsidian, fontWeight: "600" },
  input: {
    backgroundColor: Caldera.chalk,
    color: Caldera.obsidian,
    borderWidth: 1,
    borderColor: Caldera.pumice,
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
  },
  inputError: { borderColor: "#a32316" },
  error: { color: "#a32316", lineHeight: 22 },
  aviso: { color: Caldera.obsidian, lineHeight: 22 },
  description: { color: "#555", fontSize: 16, lineHeight: 24 },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: 12, marginTop: 16 },
  button: {
    alignSelf: "flex-start",
    borderWidth: 1,
    borderColor: Caldera.obsidian,
    borderRadius: 12,
    padding: 16,
  },
  buttonText: { color: Caldera.obsidian, fontWeight: "600" },
  primary: {
    backgroundColor: Caldera.ember,
    borderColor: Caldera.ember,
    marginTop: 8,
  },
  primaryText: { color: Caldera.chalk, fontWeight: "700" },
  danger: { borderColor: "#a32316" },
  dangerText: { color: "#a32316", fontWeight: "700" },
  dimmed: { opacity: 0.6 },
  modalBackdrop: {
    flex: 1,
    justifyContent: "center",
    padding: 24,
    backgroundColor: "#0008",
  },
  modalCard: {
    width: "100%",
    maxWidth: 520,
    alignSelf: "center",
    gap: 20,
    padding: 24,
    borderRadius: 20,
    backgroundColor: Caldera.limestone,
  },
  modalTitle: { color: Caldera.obsidian, fontSize: 24, fontWeight: "800" },
});
