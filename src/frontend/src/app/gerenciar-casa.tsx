import { Link } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { MoradoresCasa } from "@/components/moradores-casa";
import { DetalhesCasa } from "@/components/detalhes-casa";
import { Acao, ConfirmarAcao, styles } from "@/components/gerenciamento-ui";
import { useGerenciamentoCasa } from "@/hooks/use-gerenciamento-casa";
import {
  atualizarCasa,
  excluirCasa,
  type CasaAtualizar,
} from "@/services/casas-api";
import { limparCasaAposSaida, sessao } from "@/services/sessao-store";

export default function GerenciarCasaScreen() {
  const g = useGerenciamentoCasa(false);
  const [edicao, setEdicao] = useState<CasaAtualizar | null>(null);
  const [confirmacao, setConfirmacao] = useState<"casa" | null>(null);
  const [detalhes, setDetalhes] = useState(false);
  const [aviso, setAviso] = useState<string>();
  const casa = g.dados?.casa;

  async function salvar() {
    if (!casa || !edicao) return;
    if (
      !edicao.nome.trim() ||
      !edicao.endereco.trim() ||
      !edicao.timezone.trim()
    ) {
      g.setErro("Preencha nome, endereço e fuso horário.");
      return;
    }
    await g.executar(
      (signal) => atualizarCasa(casa.id, edicao, signal),
      (atualizada) => {
        if (sessao.getState().casaAtiva?.id === atualizada.id)
          sessao.setState({ casaAtiva: atualizada });
        setEdicao(null);
        setAviso("Casa atualizada.");
        g.atualizar();
      },
    );
  }
  async function confirmar() {
    if (!casa || !confirmacao) return;
    const token = sessao.getState().token;
    if (!token) return;
    if (confirmacao === "casa") {
      await g.executar(
        (signal) => excluirCasa(casa.id, signal),
        async () => {
          await limparCasaAposSaida(casa.id, token);
        },
      );
    }
    setConfirmacao(null);
  }
  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={styles.page}
      >
        <Link href="/" style={styles.text}>
          ← Voltar ao início
        </Link>
        <Text accessibilityRole="header" style={styles.title}>
          GERENCIAR CASA
        </Text>
        {g.erro && (
          <Text accessibilityRole="alert" style={styles.error}>
            {g.erro}
          </Text>
        )}
        {aviso && (
          <Text accessibilityRole="alert" style={styles.text}>
            {aviso}
          </Text>
        )}
        {!g.dados && !g.erro && (
          <ActivityIndicator accessibilityLabel="Carregando casa e moradores" />
        )}
        <Acao
          texto="Atualizar dados"
          disabled={g.ocupado}
          onPress={g.atualizar}
        />
        {casa && (
          <>
            <View style={styles.card}>
              <Text style={styles.subtitle}>{casa.nome}</Text>
              <Text style={styles.text}>{casa.endereco}</Text>
              <Text style={styles.text}>Fuso: {casa.timezone}</Text>
              <Text style={styles.text}>
                {g.admin ? "Você é o administrador." : "Acesso de consulta."}
              </Text>
              <Acao
                texto={detalhes ? "Ocultar detalhes" : "Ver detalhes e foto"}
                disabled={g.ocupado}
                onPress={() => setDetalhes(!detalhes)}
              />
              {detalhes && (
                <DetalhesCasa
                  key={casa.id + casa.nome + casa.timezone}
                  casaId={casa.id}
                  onFechar={() => setDetalhes(false)}
                />
              )}
              {g.admin && !edicao && (
                <Acao
                  texto="Editar casa"
                  disabled={g.ocupado}
                  onPress={() => {
                    setAviso(undefined);
                    setEdicao({
                      nome: casa.nome,
                      endereco: casa.endereco,
                      timezone: casa.timezone,
                    });
                  }}
                />
              )}
            </View>
            {g.admin && edicao && (
              <View style={styles.card}>
                <Text style={styles.subtitle}>Editar casa</Text>
                <Text style={styles.label}>Nome</Text>
                <TextInput
                  accessibilityLabel="Nome da casa"
                  editable={!g.ocupado}
                  style={styles.input}
                  value={edicao.nome}
                  onChangeText={(nome) => setEdicao({ ...edicao, nome })}
                />
                <Text style={styles.label}>Endereço</Text>
                <TextInput
                  accessibilityLabel="Endereço da casa"
                  editable={!g.ocupado}
                  style={styles.input}
                  value={edicao.endereco}
                  onChangeText={(endereco) =>
                    setEdicao({ ...edicao, endereco })
                  }
                />
                <Text style={styles.label}>Fuso horário IANA</Text>
                <TextInput
                  accessibilityLabel="Fuso horário"
                  editable={!g.ocupado}
                  autoCapitalize="none"
                  style={styles.input}
                  value={edicao.timezone}
                  onChangeText={(timezone) =>
                    setEdicao({ ...edicao, timezone })
                  }
                />
                <View style={styles.row}>
                  <Acao
                    texto="Salvar casa"
                    disabled={g.ocupado}
                    onPress={() => void salvar()}
                  />
                  <Acao
                    texto="Cancelar edição"
                    disabled={g.ocupado}
                    onPress={() => setEdicao(null)}
                  />
                </View>
              </View>
            )}
            <MoradoresCasa
              key={casa.id}
              casa={casa}
              usuarioId={g.dados?.usuarioId}
            />
            <Link href="/rotatividades" style={styles.text}>
              Ver regras de rodízio →
            </Link>
            {g.admin && (
              <Acao
                texto="Excluir casa"
                disabled={g.ocupado}
                onPress={() => setConfirmacao("casa")}
              />
            )}
          </>
        )}
        <ConfirmarAcao
          mensagem={
            g.admin && confirmacao
              ? "Excluir esta casa? A exclusão pode ser impedida se houver dados vinculados."
              : null
          }
          ocupado={g.ocupado}
          onCancelar={() => setConfirmacao(null)}
          onConfirmar={() => void confirmar()}
        />
      </ScrollView>
    </SafeAreaView>
  );
}
