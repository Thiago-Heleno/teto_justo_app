import { Link } from "expo-router";
import { useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { FormularioRotatividade } from "@/components/formulario-rotatividade";
import { Acao, ConfirmarAcao, styles } from "@/components/gerenciamento-ui";
import { diasSemanaTarefa } from "@/constants/tarefa";
import {
  mensagemGerenciamento,
  useGerenciamentoCasa,
} from "@/hooks/use-gerenciamento-casa";
import {
  listarRotatividades,
  criarRotatividade,
  atualizarRotatividade,
  excluirRotatividade,
  type Rotatividade,
} from "@/services/rotatividade-api";

export default function RotatividadesScreen() {
  const g = useGerenciamentoCasa();
  const [resultado, setResultado] = useState<{
    casa: typeof casa;
    versao: number;
    regras: Rotatividade[] | null;
    erro?: string;
  }>();
  const [versao, setVersao] = useState(0);
  const [edicao, setEdicao] = useState<Rotatividade | "nova" | null>(null);
  const [remover, setRemover] = useState<Rotatividade | null>(null);
  const [aviso, setAviso] = useState<string>();
  const casa = g.dados?.casa;
  const atual = resultado?.casa === casa && resultado?.versao === versao;
  const regras = atual ? (resultado?.regras ?? null) : null;
  const erroLista = atual ? resultado?.erro : undefined;

  useEffect(() => {
    const controlador = new AbortController();
    if (casa)
      void listarRotatividades(casa.id, controlador.signal)
        .then((lista) => {
          if (!controlador.signal.aborted)
            setResultado({ casa, versao, regras: lista });
        })
        .catch((falha) => {
          if (!controlador.signal.aborted)
            setResultado({
              casa,
              versao,
              regras: null,
              erro: mensagemGerenciamento(falha),
            });
        });
    return () => controlador.abort();
  }, [casa, versao]);

  function concluir() {
    setEdicao(null);
    setRemover(null);
    setAviso("Operação concluída.");
    setVersao((v) => v + 1);
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
        <Link href="/gerenciar-casa" style={styles.text}>
          Gerenciar casa
        </Link>
        <Text accessibilityRole="header" style={styles.title}>
          REGRAS DE RODÍZIO
        </Text>
        {casa && <Text style={styles.subtitle}>{casa.nome}</Text>}
        {g.erro && (
          <Text accessibilityRole="alert" style={styles.error}>
            {g.erro}
          </Text>
        )}
        {erroLista && (
          <Text accessibilityRole="alert" style={styles.error}>
            {erroLista}
          </Text>
        )}
        {aviso && (
          <Text accessibilityRole="alert" style={styles.text}>
            {aviso}
          </Text>
        )}
        <Acao
          texto="Atualizar lista"
          disabled={g.ocupado}
          onPress={() => {
            setEdicao(null);
            setRemover(null);
            g.atualizar();
          }}
        />
        {((!g.dados && !g.erro) || (casa && regras === null && !erroLista)) && (
          <ActivityIndicator accessibilityLabel="Carregando regras" />
        )}
        {casa && (
          <Text style={styles.text}>
            {g.admin
              ? "Gerencie as regras desta casa."
              : "Você pode consultar as regras. Alterações são exclusivas do administrador."}
          </Text>
        )}
        {g.admin && !edicao && (
          <Acao
            texto="Criar regra"
            disabled={g.ocupado}
            onPress={() => {
              g.setErro(undefined);
              setAviso(undefined);
              setEdicao("nova");
            }}
          />
        )}
        {g.admin && casa && edicao && (
          <FormularioRotatividade
            key={edicao === "nova" ? "nova" : edicao.id}
            casaId={casa.id}
            moradores={g.dados?.moradores ?? []}
            regra={edicao === "nova" ? null : edicao}
            ocupado={g.ocupado}
            onCriar={(dados) =>
              void g.executar(
                (signal) => criarRotatividade(dados, signal),
                concluir,
              )
            }
            onEditar={(dados) => {
              if (edicao !== "nova")
                void g.executar(
                  (signal) => atualizarRotatividade(edicao.id, dados, signal),
                  concluir,
                );
            }}
            onCancelar={() => setEdicao(null)}
          />
        )}
        {casa && regras?.length === 0 && (
          <Text style={styles.text}>Nenhuma regra cadastrada.</Text>
        )}
        {casa &&
          regras?.map((regra) => (
            <View key={regra.id} style={styles.card}>
              <Text style={styles.subtitle}>{regra.nome}</Text>
              <Text style={styles.text}>
                {regra.descricao || "Sem descrição"}
              </Text>
              <Text style={styles.text}>
                {regra.ativa ? "Ativa" : "Pausada"}
              </Text>
              <Text style={styles.text}>
                Dias:{" "}
                {regra.dias_semana
                  .map(
                    (dia) =>
                      diasSemanaTarefa.find((d) => d.valor === dia)
                        ?.abreviacao ?? dia,
                  )
                  .join(", ")}
              </Text>
              <Text style={styles.text}>
                A cada {regra.intervalo_semanas} semana(s) · Prazo:{" "}
                {regra.prazo_dias} dia(s) ·{" "}
                {regra.modo_prazo === "dia_fixo"
                  ? "Dia da ocorrência"
                  : "Dias após a ocorrência"}
              </Text>
              {g.admin && (
                <View style={styles.row}>
                  <Acao
                    texto={`Editar ${regra.nome}`}
                    disabled={g.ocupado || Boolean(edicao)}
                    onPress={() => {
                      g.setErro(undefined);
                      setAviso(undefined);
                      setEdicao(regra);
                    }}
                  />
                  <Acao
                    texto={`Remover ${regra.nome}`}
                    disabled={g.ocupado || Boolean(edicao)}
                    onPress={() => setRemover(regra)}
                  />
                </View>
              )}
            </View>
          ))}
        <Text style={styles.text}>
          Regras com tarefas já geradas não podem ser excluídas. O administrador
          pode pausá-las em Editar.
        </Text>
        <ConfirmarAcao
          mensagem={
            g.admin && remover ? `Remover a regra “${remover.nome}”?` : null
          }
          ocupado={g.ocupado}
          onCancelar={() => setRemover(null)}
          onConfirmar={() => {
            if (remover)
              void g
                .executar(
                  (signal) => excluirRotatividade(remover.id, signal),
                  concluir,
                )
                .finally(() => setRemover(null));
          }}
        />
      </ScrollView>
    </SafeAreaView>
  );
}
