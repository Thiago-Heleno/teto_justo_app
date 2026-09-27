import { useEffect, useRef, useState } from "react";
import {
  Keyboard,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { MotionPressable } from "@/components/motion-pressable";
import {
  diasSemanaTarefa,
  intervalosSemanasTarefa,
  type IntervaloSemanas,
  type DiaSemana,
  pesosTarefa,
  prazosTarefa,
  type PesoTarefa,
  type PrazoDias,
  type ModoPrazo,
  type TarefaDemonstracao,
} from "@/constants/tarefa";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import {
  casaDemonstracao,
  moradoresDemonstracao,
  usuarioDemonstracaoId,
} from "@/data/tarefa-demonstracao";
import {
  carregarContextoTarefas,
  criarTarefa as salvarTarefa,
  temConfiguracaoTarefas,
  type Casa,
} from "@/services/tarefas-api";
import { prepararTarefa, type ErrosCriacao } from "@/utils/criacao-tarefa";

function ErroCampo({ mensagem }: { mensagem?: string }) {
  if (!mensagem) return null;
  return (
    <Text style={styles.help} accessibilityLiveRegion="polite">
      Atenção: {mensagem}
    </Text>
  );
}

function IndicadorSelecao({ selecionado }: { selecionado: boolean }) {
  return (
    <View accessible={false} style={styles.radio}>
      {selecionado && <View style={styles.radioDot} />}
    </View>
  );
}

export default function NovaTarefaScreen() {
  const { width } = useWindowDimensions();
  const [usarApi, setUsarApi] = useState(temConfiguracaoTarefas);
  const [contexto, setContexto] = useState<
    [Casa, { id: string; nome: string }[]] | null
  >(usarApi ? null : [casaDemonstracao, moradoresDemonstracao]);
  const [erroContexto, setErroContexto] = useState<string>();
  const [tentativa, setTentativa] = useState(0);
  const casa = contexto?.[0];
  const moradores = contexto?.[1] ?? [];

  useEffect(() => {
    if (!usarApi) return;
    const controlador = new AbortController();
    async function carregar() {
      try {
        const dados = await carregarContextoTarefas(controlador.signal);
        if (!controlador.signal.aborted) setContexto(dados);
      } catch (erro: unknown) {
        if (!controlador.signal.aborted)
          setErroContexto(
            erro instanceof Error
              ? erro.message
              : "Não foi possível carregar os moradores.",
          );
      }
    }
    void carregar();
    return () => controlador.abort();
  }, [usarApi, tentativa]);
  const scrollRef = useRef<ScrollView>(null);
  const envioEmAndamento = useRef(false);
  const descricaoRef = useRef<TextInput>(null);
  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const [peso, setPeso] = useState<PesoTarefa | null>(null);
  const [dias, setDias] = useState<PrazoDias | null>(null);
  const [atrasoMaximo, setAtrasoMaximo] = useState<PrazoDias | null>(null);
  const [modoPrazo, setModoPrazo] = useState<ModoPrazo>("intervalo");
  const [dataFixa, setDataFixa] = useState("");
  const [responsavel, setResponsavel] = useState<string | null>(null);
  const [rotativa, setRotativa] = useState(false);
  const [participantes, setParticipantes] = useState<string[]>([]);
  const [diasSemana, setDiasSemana] = useState<DiaSemana[]>([]);
  const [semanas, setSemanas] = useState<IntervaloSemanas>(1);
  const [erros, setErros] = useState<ErrosCriacao>({});
  const [tarefa, setTarefa] = useState<TarefaDemonstracao | null>(null);
  const [salvando, setSalvando] = useState(false);
  const [erroEnvio, setErroEnvio] = useState<string>();
  const cardStyle = [styles.card, width < 600 && styles.compactCard];

  async function criarTarefa() {
    const resultado = prepararTarefa(
      {
        nome,
        descricao,
        peso,
        dias,
        atrasoMaximo,
        modoPrazo,
        dataFixa,
        responsavel,
        rotativa,
        participantes,
        diasSemana,
        semanas,
      },
      moradores,
    );
    setErros(resultado.erros);
    Keyboard.dismiss();
    if (resultado.tarefa) {
      if (!usarApi || resultado.tarefa.rotatividade) {
        setTarefa(resultado.tarefa);
      } else if (casa) {
        if (envioEmAndamento.current) return;
        envioEmAndamento.current = true;
        setSalvando(true);
        setErroEnvio(undefined);
        try {
          const preparada = resultado.tarefa;
          await salvarTarefa({
            fk_casa_id: casa.id,
            nome: preparada.nome,
            descricao: preparada.descricao,
            peso: preparada.peso,
            prazo_dias: preparada.prazo_dias,
            atraso_maximo: preparada.atraso_maximo,
            tipo: "unitaria",
            modo_prazo: preparada.modo_prazo,
            ...(preparada.data_fixa ? { data_fixa: preparada.data_fixa } : {}),
            usuarios_atribuidos: preparada.usuarios_atribuidos,
          });
          setTarefa(preparada);
        } catch (erro: unknown) {
          setErroEnvio(erro instanceof Error ? erro.message : "Não foi possível criar a tarefa.");
        } finally {
          envioEmAndamento.current = false;
          setSalvando(false);
        }
      }
    }
    scrollRef.current?.scrollTo({ y: 0, animated: false });
  }

  function criarOutraTarefa() {
    setNome("");
    setDescricao("");
    setPeso(null);
    setDias(null);
    setAtrasoMaximo(null);
    setModoPrazo("intervalo");
    setDataFixa("");
    setResponsavel(null);
    setRotativa(false);
    setParticipantes([]);
    setDiasSemana([]);
    setSemanas(1);
    setErros({});
    setTarefa(null);
    setErroEnvio(undefined);
    scrollRef.current?.scrollTo({ y: 0, animated: false });
  }

  function alternarParticipante(id: string) {
    setParticipantes((atuais) =>
      atuais.includes(id)
        ? atuais.filter((participante) => participante !== id)
        : [...atuais, id],
    );
    setErros((atuais) => ({ ...atuais, participantes: undefined }));
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
      >
        <ScrollView
          ref={scrollRef}
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          keyboardDismissMode="on-drag"
        >
          <View style={styles.form}>
            <View style={styles.section}>
              <Text style={styles.help}>{casa?.nome ?? "Sua casa"}</Text>
              <Text accessibilityRole="header" style={styles.title}>
                {tarefa
                  ? tarefa.rotatividade
                    ? "PRÉVIA DO RODÍZIO"
                    : usarApi
                      ? "TAREFA CRIADA!"
                      : "TUDO PRONTO!"
                  : "NOVA TAREFA"}
              </Text>
              <Text style={styles.body}>
                {tarefa
                  ? "Confira os detalhes abaixo."
                  : "Organize o que precisa ser feito na casa."}
              </Text>
              <View style={styles.badge}>
                <Text style={styles.help}>
                  {usarApi
                    ? "Tarefas da sua casa"
                    : "Demonstração · dados fictícios"}
                </Text>
              </View>
              {(!usarApi || rotativa) && (
                <Text style={styles.help}>
                  {usarApi
                    ? "Esta prévia não salva nem inicia o rodízio."
                    : "Esta demonstração não salva tarefas nem inicia o rodízio."}
                </Text>
              )}
            </View>

            {!contexto ? (
              <View style={cardStyle}>
                <Text style={styles.body} accessibilityLiveRegion="polite">
                  {erroContexto || "Carregando os moradores da sua casa..."}
                </Text>
                {erroContexto && (
                  <MotionPressable
                    accessibilityRole="button"
                    style={styles.button}
                    onPress={() => {
                      setErroContexto(undefined);
                      setTentativa((atual) => atual + 1);
                    }}
                  >
                    <Text style={styles.body}>Tentar novamente</Text>
                  </MotionPressable>
                )}
                {erroContexto && (
                  <MotionPressable
                    accessibilityRole="button"
                    style={styles.demoButton}
                    onPress={() => {
                      setUsarApi(false);
                      setContexto([casaDemonstracao, moradoresDemonstracao]);
                      setErroContexto(undefined);
                    }}
                  >
                    <Text style={styles.body}>Usar dados de demonstração</Text>
                  </MotionPressable>
                )}
              </View>
            ) : tarefa ? (
              <>
                <View style={cardStyle}>
                  <Text
                    accessibilityRole="header"
                    accessibilityLiveRegion="polite"
                    style={styles.sectionTitle}
                  >
                    {usarApi && !tarefa.rotatividade
                      ? "Detalhes salvos"
                      : "Prévia da tarefa"}
                  </Text>
                  <View style={styles.section}>
                    <Text style={styles.help}>Nome</Text>
                    <Text style={styles.body}>{tarefa.nome}</Text>
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.help}>Descrição</Text>
                    <Text style={styles.body}>
                      {tarefa.descricao || "Sem descrição."}
                    </Text>
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.help}>Peso</Text>
                    <Text style={styles.body}>{tarefa.peso}</Text>
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.help}>Prazo para terminar</Text>
                    <Text style={styles.body}>
                      {tarefa.prazo_dias}{" "}
                      {tarefa.prazo_dias === 1 ? "dia" : "dias"}
                    </Text>
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.help}>Tolerância após o prazo</Text>
                    <Text style={styles.body}>{tarefa.atraso_maximo} {tarefa.atraso_maximo === 1 ? "dia" : "dias"}</Text>
                    <Text style={styles.help}>Modo do prazo</Text>
                    <Text style={styles.body}>{tarefa.modo_prazo === "dia_fixo" ? "Dia fixo" : "Intervalo"}</Text>
                    {tarefa.data_fixa && <Text style={styles.body}>Vencimento: {tarefa.data_fixa}</Text>}
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.help}>
                      {tarefa.rotatividade
                        ? "Primeiro responsável"
                        : "Responsável"}
                    </Text>
                    <Text style={styles.body}>
                      {moradores.find((morador) => morador.id === tarefa.usuarios_atribuidos[0])?.nome}
                    </Text>
                  </View>
                  {tarefa.rotatividade && (
                    <View style={styles.section}>
                      <Text style={styles.help}>
                        {tarefa.rotatividade.intervalo_semanas === 1
                          ? "Repetir toda semana"
                          : `Repetir a cada ${tarefa.rotatividade.intervalo_semanas} semanas`}
                      </Text>
                      <Text style={styles.body}>
                        {diasSemanaTarefa
                          .filter((dia) =>
                            tarefa.rotatividade?.dias_semana.includes(
                              dia.valor,
                            ),
                          )
                          .map((dia) => dia.rotulo)
                          .join(", ")}
                      </Text>
                      <Text style={styles.help}>Ordem do rodízio</Text>
                      {tarefa.rotatividade.participantes.map((id, indice) => (
                        <Text key={id} style={styles.body}>
                          {indice + 1}.{" "}
                          {moradores.find((morador) => morador.id === id)?.nome}
                        </Text>
                      ))}
                      <Text style={styles.help}>
                        Em cada período, o próximo participante fica
                        responsável. Após o último participante, a sequência
                        recomeça.
                      </Text>
                    </View>
                  )}
                </View>
                <MotionPressable
                  accessibilityRole="button"
                  onPress={criarOutraTarefa}
                  style={styles.button}
                >
                  <Text style={styles.body}>
                    {tarefa.rotatividade
                      ? "Conferir outra tarefa"
                      : "Criar outra tarefa"}
                  </Text>
                </MotionPressable>
              </>
            ) : (
              <>
                <View style={cardStyle}>
                  <View style={styles.section}>
                    <Text
                      accessibilityRole="header"
                      style={styles.sectionTitle}
                    >
                      OS DETALHES
                    </Text>
                    <Text style={styles.help}>
                      Campos com * são obrigatórios.
                    </Text>
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.body}>Nome *</Text>
                    <TextInput
                      accessibilityLabel="Nome da tarefa, obrigatório"
                      accessibilityHint={erros.nome}
                      style={styles.input}
                      placeholder="Ex.: Limpar a cozinha"
                      placeholderTextColor={Caldera.obsidian}
                      selectionColor={Caldera.ember}
                      returnKeyType="next"
                      onSubmitEditing={() => descricaoRef.current?.focus()}
                      value={nome}
                      onChangeText={(valor) => {
                        setNome(valor);
                        setErros((atuais) => ({ ...atuais, nome: undefined }));
                      }}
                    />
                    <ErroCampo mensagem={erros.nome} />
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.body}>Descrição (opcional)</Text>
                    <TextInput
                      ref={descricaoRef}
                      accessibilityLabel="Descrição, opcional"
                      style={[styles.input, styles.description]}
                      placeholder="O que precisa ser feito?"
                      placeholderTextColor={Caldera.obsidian}
                      selectionColor={Caldera.ember}
                      multiline
                      textAlignVertical="top"
                      value={descricao}
                      onChangeText={setDescricao}
                    />
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.body}>Peso *</Text>
                    <Text style={styles.help}>
                      Selecione a dificuldade: 1 é a menor e 3 é a maior.
                    </Text>
                    <View
                      style={styles.options}
                      accessibilityRole="radiogroup"
                      accessibilityLabel="Peso da tarefa"
                    >
                      {pesosTarefa.map((opcao) => (
                        <MotionPressable
                          key={opcao}
                          accessibilityRole="radio"
                          accessibilityLabel={`Peso ${opcao}`}
                          accessibilityState={{ checked: peso === opcao }}
                          aria-checked={peso === opcao}
                          onPress={() => {
                            setPeso(opcao);
                            setErros((atuais) => ({
                              ...atuais,
                              peso: undefined,
                            }));
                          }}
                          style={[
                            styles.option,
                            peso === opcao && styles.selected,
                          ]}
                        >
                          <IndicadorSelecao selecionado={peso === opcao} />
                          <Text style={styles.body}>{opcao}</Text>
                        </MotionPressable>
                      ))}
                    </View>
                    <ErroCampo mensagem={erros.peso} />
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.body}>Dias para terminar *</Text>
                    <Text style={styles.help}>Escolha de 1 a 5 dias.</Text>
                    <View
                      style={styles.options}
                      accessibilityRole="radiogroup"
                      accessibilityLabel="Dias para terminar"
                    >
                      {prazosTarefa.map((opcao) => (
                        <MotionPressable
                          key={opcao}
                          accessibilityRole="radio"
                          accessibilityLabel={`${opcao} ${opcao === 1 ? "dia" : "dias"}`}
                          accessibilityState={{ checked: dias === opcao }}
                          aria-checked={dias === opcao}
                          onPress={() => {
                            setDias(opcao);
                            setErros((atuais) => ({
                              ...atuais,
                              prazo: undefined,
                            }));
                          }}
                          style={[
                            styles.option,
                            dias === opcao && styles.selected,
                          ]}
                        >
                          <IndicadorSelecao selecionado={dias === opcao} />
                          <Text style={styles.body}>{opcao}</Text>
                        </MotionPressable>
                      ))}
                    </View>
                    <ErroCampo mensagem={erros.prazo} />
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.body}>Tolerância após o prazo *</Text>
                    <Text style={styles.help}>Escolha de 1 a 5 dias. A pontuação diminui a cada dia de atraso.</Text>
                    <View style={styles.options} accessibilityRole="radiogroup">
                      {prazosTarefa.map((opcao) => (
                        <MotionPressable
                          key={opcao}
                          accessibilityRole="radio"
                          accessibilityLabel={`${opcao} ${opcao === 1 ? "dia" : "dias"} de tolerância`}
                          accessibilityState={{ checked: atrasoMaximo === opcao }}
                          onPress={() => {
                            setAtrasoMaximo(opcao);
                            setErros((atuais) => ({ ...atuais, atrasoMaximo: undefined }));
                          }}
                          style={[styles.option, atrasoMaximo === opcao && styles.selected]}
                        >
                          <IndicadorSelecao selecionado={atrasoMaximo === opcao} />
                          <Text style={styles.body}>{opcao}</Text>
                        </MotionPressable>
                      ))}
                    </View>
                    <ErroCampo mensagem={erros.atrasoMaximo} />
                  </View>
                  <View style={styles.section}>
                    <Text style={styles.body}>Como funciona o prazo? *</Text>
                    <View style={styles.options} accessibilityRole="radiogroup">
                      <MotionPressable
                        accessibilityRole="radio"
                        accessibilityState={{ checked: modoPrazo === "intervalo" }}
                        onPress={() => setModoPrazo("intervalo")}
                        style={[styles.option, modoPrazo === "intervalo" && styles.selected]}
                      >
                        <IndicadorSelecao selecionado={modoPrazo === "intervalo"} />
                        <Text style={styles.body}>Intervalo</Text>
                      </MotionPressable>
                      <MotionPressable
                        accessibilityRole="radio"
                        accessibilityState={{ checked: modoPrazo === "dia_fixo" }}
                        onPress={() => setModoPrazo("dia_fixo")}
                        style={[styles.option, modoPrazo === "dia_fixo" && styles.selected]}
                      >
                        <IndicadorSelecao selecionado={modoPrazo === "dia_fixo"} />
                        <Text style={styles.body}>Dia fixo</Text>
                      </MotionPressable>
                    </View>
                    <Text style={styles.help}>
                      {modoPrazo === "dia_fixo"
                        ? "O dia escolhido é o vencimento. A tarefa abre antes, conforme o prazo em dias."
                        : "A tarefa abre no dia escolhido e vence após o prazo em dias."}
                    </Text>
                    {!rotativa && modoPrazo === "dia_fixo" && (
                      <>
                        <Text style={styles.body}>Data do vencimento *</Text>
                        <TextInput
                          accessibilityLabel="Data do vencimento no formato ano, mês e dia"
                          autoCapitalize="none"
                          inputMode="numeric"
                          placeholder="2026-10-01"
                          placeholderTextColor={Caldera.obsidian}
                          selectionColor={Caldera.ember}
                          style={styles.input}
                          value={dataFixa}
                          onChangeText={(valor) => {
                            setDataFixa(valor);
                            setErros((atuais) => ({ ...atuais, dataFixa: undefined }));
                          }}
                        />
                      </>
                    )}
                    <ErroCampo mensagem={erros.dataFixa} />
                  </View>
                </View>

                <View style={cardStyle}>
                  <View style={styles.section}>
                    <Text
                      accessibilityRole="header"
                      style={styles.sectionTitle}
                    >
                      QUEM VAI FAZER?
                    </Text>
                    <View
                      style={styles.options}
                      accessibilityRole="radiogroup"
                      accessibilityLabel="Tipo de tarefa"
                    >
                      {[
                        { valor: false, nome: "Comum" },
                        { valor: true, nome: "Rotativa" },
                      ].map((opcao) => (
                        <MotionPressable
                          key={opcao.nome}
                          accessibilityRole="radio"
                          accessibilityLabel={`Tarefa ${opcao.nome.toLowerCase()}`}
                          accessibilityState={{
                            checked: rotativa === opcao.valor,
                          }}
                          aria-checked={rotativa === opcao.valor}
                          onPress={() => {
                            setRotativa(opcao.valor);
                            setErros((atuais) => ({
                              ...atuais,
                              responsavel: undefined,
                              participantes: undefined,
                              diasSemana: undefined,
                              semanas: undefined,
                              dataFixa: undefined,
                            }));
                          }}
                          style={[
                            styles.option,
                            rotativa === opcao.valor && styles.selected,
                          ]}
                        >
                          <IndicadorSelecao
                            selecionado={rotativa === opcao.valor}
                          />
                          <Text style={styles.body}>{opcao.nome}</Text>
                        </MotionPressable>
                      ))}
                    </View>
                    <Text style={styles.body}>
                      {rotativa
                        ? "Participantes do rodízio *"
                        : "Responsável *"}
                    </Text>
                    <Text style={styles.help}>
                      {rotativa
                        ? "Escolha pelo menos dois moradores, na ordem em que vão participar. O primeiro selecionado começa."
                        : "Escolha apenas um morador. Ao escolher outro, a seleção anterior é substituída."}
                    </Text>
                  </View>
                  {moradores.length === 0 && (
                    <Text style={styles.help}>
                      Não há moradores disponíveis para esta casa.
                    </Text>
                  )}
                  {rotativa && moradores.length === 1 && (
                    <Text style={styles.help}>
                      O rodízio precisa de pelo menos dois moradores na casa.
                    </Text>
                  )}
                  <View
                    style={styles.section}
                    accessibilityRole={rotativa ? undefined : "radiogroup"}
                    accessibilityLabel={
                      rotativa
                        ? "Participantes do rodízio"
                        : "Responsável pela tarefa"
                    }
                  >
                    {moradores.map((morador) => {
                      const selecionado = rotativa
                        ? participantes.includes(morador.id)
                        : responsavel === morador.id;
                      const nomeExibido = `${morador.nome}${!usarApi && morador.id === usuarioDemonstracaoId ? " (você)" : ""}`;
                      return (
                        <MotionPressable
                          key={morador.id}
                          accessibilityRole={rotativa ? "checkbox" : "radio"}
                          accessibilityLabel={nomeExibido}
                          accessibilityState={{ checked: selecionado }}
                          aria-checked={selecionado}
                          onPress={() => {
                            if (rotativa) alternarParticipante(morador.id);
                            else setResponsavel(morador.id);
                            setErros((atuais) => ({
                              ...atuais,
                              responsavel: undefined,
                            }));
                          }}
                          style={[
                            styles.resident,
                            selecionado && styles.selected,
                          ]}
                        >
                          <View style={styles.avatar}>
                            <Text style={styles.help}>
                              {morador.nome
                                .split(" ")
                                .filter(Boolean)
                                .slice(0, 2)
                                .map((parte) => parte[0])
                                .join("")
                                .toUpperCase()}
                            </Text>
                          </View>
                          <Text style={[styles.body, styles.residentName]}>
                            {nomeExibido}
                          </Text>
                          {rotativa ? (
                            <View accessible={false} style={styles.checkbox}>
                              <Text style={styles.help}>
                                {selecionado ? "✓" : ""}
                              </Text>
                            </View>
                          ) : (
                            <IndicadorSelecao selecionado={selecionado} />
                          )}
                        </MotionPressable>
                      );
                    })}
                  </View>
                  <ErroCampo
                    mensagem={
                      rotativa ? erros.participantes : erros.responsavel
                    }
                  />
                  {rotativa && (
                    <>
                      {participantes.length > 0 && (
                        <View style={styles.section}>
                          <Text style={styles.body}>Ordem do rodízio</Text>
                          {participantes.map((id, indice) => (
                            <View key={id} style={styles.orderRow}>
                              <Text style={[styles.help, styles.residentName]}>
                                {indice + 1}.{" "}
                                {
                                  moradores.find((morador) => morador.id === id)
                                    ?.nome
                                }
                                {indice === 0 ? " · começa" : ""}
                              </Text>
                              {indice > 0 && (
                                <MotionPressable
                                  accessibilityRole="button"
                                  accessibilityLabel={`Antecipar ${moradores.find((morador) => morador.id === id)?.nome}`}
                                  style={styles.reorderButton}
                                  onPress={() =>
                                    setParticipantes((atuais) => {
                                      const novaOrdem = [...atuais];
                                      const [movido] = novaOrdem.splice(
                                        indice,
                                        1,
                                      );
                                      novaOrdem.splice(indice - 1, 0, movido);
                                      return novaOrdem;
                                    })
                                  }
                                >
                                  <Text style={styles.help}>↑ Subir</Text>
                                </MotionPressable>
                              )}
                            </View>
                          ))}
                          <Text style={styles.help}>
                            Após o último, o rodízio volta ao primeiro.
                          </Text>
                        </View>
                      )}
                      <View style={styles.section}>
                        <Text style={styles.body}>
                          Repetir a cada quantas semanas? *
                        </Text>
                        <View
                          style={styles.options}
                          accessibilityRole="radiogroup"
                          accessibilityLabel="Intervalo de repetição em semanas"
                        >
                          {intervalosSemanasTarefa.map((opcao) => (
                            <MotionPressable
                              key={opcao}
                              accessibilityRole="radio"
                              accessibilityLabel={`${opcao} ${opcao === 1 ? "semana" : "semanas"}`}
                              accessibilityState={{
                                checked: semanas === opcao,
                              }}
                              aria-checked={semanas === opcao}
                              onPress={() => {
                                setSemanas(opcao);
                                setErros((atuais) => ({
                                  ...atuais,
                                  semanas: undefined,
                                }));
                              }}
                              style={[
                                styles.option,
                                semanas === opcao && styles.selected,
                              ]}
                            >
                              <IndicadorSelecao
                                selecionado={semanas === opcao}
                              />
                              <Text style={styles.body}>
                                {opcao} {opcao === 1 ? "semana" : "semanas"}
                              </Text>
                            </MotionPressable>
                          ))}
                        </View>
                        {semanas === 4 && (
                          <Text style={styles.help}>
                            4 semanas são 28 dias: aproximadamente uma vez por
                            mês.
                          </Text>
                        )}
                        <ErroCampo mensagem={erros.semanas} />
                      </View>
                      <View style={styles.section}>
                        <Text style={styles.body}>
                          Repetir em quais dias? *
                        </Text>
                        <Text style={styles.help}>
                          {semanas === 1
                            ? "Selecione um ou mais dias. A tarefa se repete toda semana nos dias escolhidos."
                            : `Selecione um ou mais dias. A tarefa se repete nos dias escolhidos a cada ${semanas} semanas.`}
                        </Text>
                        <View
                          style={styles.options}
                          accessibilityLabel="Dias da semana da tarefa"
                        >
                          {diasSemanaTarefa.map((dia) => {
                            const selecionado = diasSemana.includes(dia.valor);
                            return (
                              <MotionPressable
                                key={dia.valor}
                                accessibilityRole="checkbox"
                                accessibilityLabel={dia.rotulo}
                                accessibilityState={{ checked: selecionado }}
                                aria-checked={selecionado}
                                onPress={() => {
                                  setDiasSemana((atuais) =>
                                    atuais.includes(dia.valor)
                                      ? atuais.filter(
                                          (valor) => valor !== dia.valor,
                                        )
                                      : [...atuais, dia.valor],
                                  );
                                  setErros((atuais) => ({
                                    ...atuais,
                                    diasSemana: undefined,
                                  }));
                                }}
                                style={[
                                  styles.option,
                                  styles.weekday,
                                  selecionado && styles.selected,
                                ]}
                              >
                                <View
                                  accessible={false}
                                  style={styles.checkbox}
                                >
                                  <Text style={styles.help}>
                                    {selecionado ? "✓" : ""}
                                  </Text>
                                </View>
                                <Text style={styles.body}>
                                  {dia.abreviacao}
                                </Text>
                              </MotionPressable>
                            );
                          })}
                        </View>
                        <ErroCampo mensagem={erros.diasSemana} />
                      </View>
                    </>
                  )}
                </View>
                {erroEnvio && <Text accessibilityLiveRegion="polite" style={styles.help}>{erroEnvio}</Text>}
                <MotionPressable
                  accessibilityRole="button"
                  accessibilityState={{ busy: salvando, disabled: salvando }}
                  disabled={salvando}
                  onPress={() => void criarTarefa()}
                  style={styles.button}
                >
                  <Text style={styles.body}>
                    {salvando
                      ? "Criando..."
                      : rotativa
                        ? "Conferir rodízio"
                        : usarApi
                          ? "Criar tarefa"
                          : "Conferir tarefa"}
                  </Text>
                </MotionPressable>
              </>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: Caldera.pumice },
  container: { flex: 1 },
  content: {
    flexGrow: 1,
    paddingHorizontal: Spacing.three,
    paddingTop: Platform.OS === "web" ? 120 : Spacing.four,
    paddingBottom: Spacing.six,
  },
  form: {
    width: "100%",
    maxWidth: 760,
    alignSelf: "center",
    gap: Spacing.four,
  },
  section: { gap: Spacing.two },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 48,
    lineHeight: 56,
    letterSpacing: 0.96,
  },
  sectionTitle: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 26,
    lineHeight: 32,
    letterSpacing: 0.52,
  },
  body: {
    color: Caldera.obsidian,
    fontSize: 16,
    lineHeight: 24,
    fontWeight: "500",
  },
  help: {
    color: Caldera.obsidian,
    fontSize: 14,
    lineHeight: 20,
    fontWeight: "500",
  },
  badge: {
    alignSelf: "flex-start",
    backgroundColor: Caldera.sulfur,
    borderRadius: 800,
    paddingHorizontal: 16,
    paddingVertical: 8,
  },
  card: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: 40,
    gap: Spacing.four,
  },
  compactCard: { padding: Spacing.four },
  input: {
    color: Caldera.obsidian,
    backgroundColor: Caldera.pumice,
    borderRadius: 100,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.three,
    minHeight: 56,
    fontSize: 16,
    fontWeight: "500",
  },
  description: { minHeight: 128, borderRadius: 40 },
  options: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  option: {
    flexGrow: 1,
    minWidth: 52,
    minHeight: 48,
    borderRadius: 800,
    backgroundColor: Caldera.pumice,
    padding: Spacing.two,
    flexDirection: "row",
    gap: Spacing.two,
    justifyContent: "center",
    alignItems: "center",
  },
  weekday: { minWidth: 88 },
  selected: { backgroundColor: Caldera.ember },
  checkbox: {
    width: 24,
    height: 24,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 6,
    alignItems: "center",
    justifyContent: "center",
  },
  orderRow: { flexDirection: "row", alignItems: "center", gap: Spacing.two },
  reorderButton: {
    minHeight: 44,
    paddingHorizontal: Spacing.three,
    justifyContent: "center",
    borderRadius: 800,
    backgroundColor: Caldera.pumice,
  },
  radio: {
    width: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    alignItems: "center",
    justifyContent: "center",
  },
  radioDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Caldera.obsidian,
  },
  resident: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.two,
    padding: Spacing.three,
    borderRadius: 40,
    backgroundColor: Caldera.pumice,
    minHeight: 72,
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: Caldera.limestone,
    alignItems: "center",
    justifyContent: "center",
  },
  residentName: { flex: 1 },
  demoButton: {
    minHeight: 56,
    justifyContent: "center",
    alignItems: "center",
    padding: Spacing.three,
    borderRadius: 800,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
  },
  button: {
    minHeight: 56,
    paddingVertical: 12,
    paddingHorizontal: Spacing.four,
    borderRadius: 800,
    backgroundColor: Caldera.ember,
    alignItems: "center",
    justifyContent: "center",
  },
});
