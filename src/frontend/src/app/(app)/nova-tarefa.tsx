import { useFocusEffect } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
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
import { Plus, RefreshCw, Repeat } from "lucide-react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Avatar } from "@/components/avatar";
import { MotionPressable } from "@/components/motion-pressable";
import {
  RoletaResponsavel,
  type ResultadoRoleta,
} from "@/components/roleta-responsavel";
import {
  diasSemanaTarefa,
  intervalosSemanasTarefa,
  modosAtribuicaoTarefa,
  type IntervaloSemanas,
  type DiaSemana,
  pesosTarefa,
  prazosTarefa,
  type PesoTarefa,
  type PrazoDias,
  type ModoPrazo,
  type ModoAtribuicao,
  type TarefaDemonstracao,
} from "@/constants/tarefa";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import {
  carregarAdministradorDaCasa,
  carregarContextoTarefas,
  carregarUsuarioAtual,
  criarRotatividade as salvarRotatividade,
  criarTarefa as salvarTarefa,
  mensagemErroAoSalvarTarefa,
  type Casa,
  type Morador,
  type UsuarioAtual,
} from "@/services/tarefas-api";
import { prepararTarefa, type ErrosCriacao } from "@/utils/criacao-tarefa";
import { formatarDataDigitada } from "@/utils/data-fixa";

type TarefaPreparada = NonNullable<ReturnType<typeof prepararTarefa>["tarefa"]>;
type ResumoTarefa =
  | { pendente: TarefaPreparada; sorteio: ResultadoRoleta; salva?: never }
  | { salva: TarefaDemonstracao; sorteio?: ResultadoRoleta; pendente?: never };

function ErroCampo({ mensagem }: { mensagem?: string }) {
  if (!mensagem) return null;
  return (
    <Text style={styles.aviso} accessibilityLiveRegion="polite">
      ⚠ {mensagem}
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
  const [contexto, setContexto] = useState<
    [Casa, Morador[], UsuarioAtual | undefined, UsuarioAtual] | null
  >(null);
  const [erroContexto, setErroContexto] = useState<string>();
  const [tentativa, setTentativa] = useState(0);
  const casa = contexto?.[0];
  const moradores = contexto?.[1] ?? [];
  const usuario = contexto?.[2];
  const administrador = contexto?.[3];
  const podeCriarRotativa = usuario?.id === casa?.fk_usuario_id;
  const responsaveisDisponiveis =
    administrador && !moradores.some(({ id }) => id === administrador.id)
      ? [...moradores, { ...administrador, foto: null }]
      : moradores;

  const scrollRef = useRef<ScrollView>(null);
  const envioEmAndamento = useRef(false);
  const descricaoRef = useRef<TextInput>(null);
  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const [alturaDescricao, setAlturaDescricao] = useState(56);
  const [peso, setPeso] = useState<PesoTarefa | null>(null);
  const [dias, setDias] = useState<PrazoDias | null>(null);
  const [atrasoMaximo, setAtrasoMaximo] = useState<PrazoDias | null>(null);
  const [modoPrazo, setModoPrazo] = useState<ModoPrazo>("intervalo");
  const [dataFixa, setDataFixa] = useState("");
  const [responsavel, setResponsavel] = useState<string | null>(null);
  const [modoAtribuicao, setModoAtribuicao] =
    useState<ModoAtribuicao>("manual");
  const [rotativa, setRotativa] = useState(false);
  const [participantes, setParticipantes] = useState<string[]>([]);
  const [diasSemana, setDiasSemana] = useState<DiaSemana[]>([]);
  const [semanas, setSemanas] = useState<IntervaloSemanas>(1);
  const [erros, setErros] = useState<ErrosCriacao>({});
  const [resumo, setResumo] = useState<ResumoTarefa | null>(null);
  const tarefa = resumo?.salva ?? resumo?.pendente;
  const [salvando, setSalvando] = useState(false);
  const [erroEnvio, setErroEnvio] = useState<string>();
  const cardStyle = [styles.card, width < 600 && styles.compactCard];
  const sortear = !rotativa && modoAtribuicao === "aleatorio";

  useFocusEffect(
    useCallback(() => {
      const controlador = new AbortController();
      setContexto(null);
      setErroContexto(undefined);
      async function carregar() {
        try {
          const [[casaAtual, moradoresAtuais], usuarioAtual] =
            await Promise.all([
              carregarContextoTarefas(controlador.signal),
              carregarUsuarioAtual(controlador.signal).catch(() => undefined),
            ]);
          const administradorAtual = await carregarAdministradorDaCasa(
            casaAtual,
            usuarioAtual,
            controlador.signal,
          );
          if (!controlador.signal.aborted) {
            setContexto([
              casaAtual,
              moradoresAtuais,
              usuarioAtual,
              administradorAtual,
            ]);
            const ids = new Set(moradoresAtuais.map((morador) => morador.id));
            setResponsavel((atual) => (atual && ids.has(atual) ? atual : null));
            setParticipantes((atuais) => atuais.filter((id) => ids.has(id)));
          }
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
      // A tentativa refaz a consulta sem precisar mudar de aba.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [tentativa]),
  );

  useEffect(() => {
    if (Platform.OS !== "web") return;
    const campo = descricaoRef.current as unknown as HTMLTextAreaElement | null;
    if (!campo) return;
    campo.style.height = "auto";
    campo.style.height = `${Math.max(56, campo.scrollHeight)}px`;
  }, [descricao, width, contexto, tarefa]);

  function prepararCriacao() {
    if (!casa || tarefa || envioEmAndamento.current) return;
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
        modoAtribuicao: sortear ? "aleatorio" : "manual",
        rotativa,
        participantes,
        diasSemana,
        semanas,
      },
      rotativa ? moradores : responsaveisDisponiveis,
    );
    setErros(resultado.erros);
    Keyboard.dismiss();
    const preparada = resultado.tarefa;
    if (!preparada) {
      scrollRef.current?.scrollTo({ y: 0, animated: false });
      return;
    }

    if (preparada.modo_atribuicao === "aleatorio") {
      setErroEnvio(undefined);
      setResumo({
        pendente: preparada,
        sorteio: { casaId: casa.id, candidatos: moradores, administrador },
      });
      scrollRef.current?.scrollTo({ y: 0, animated: false });
      return;
    }

    void gravarTarefa(preparada, casa.id);
  }

  async function gravarTarefa(
    preparada: TarefaPreparada,
    casaId: string,
    sorteio?: ResultadoRoleta,
  ) {
    if (envioEmAndamento.current) return;
    envioEmAndamento.current = true;
    setSalvando(true);
    setErroEnvio(undefined);
    try {
      const { rotatividade, ...campos } = preparada;
      if (rotatividade) {
        const { nome, descricao, peso, prazo_dias, atraso_maximo, modo_prazo } =
          campos;
        await salvarRotatividade({
          fk_casa_id: casaId,
          nome,
          descricao,
          peso,
          prazo_dias,
          atraso_maximo,
          modo_prazo,
          ...rotatividade,
        });
        setResumo({
          salva: {
            ...preparada,
            usuarios_atribuidos: preparada.usuarios_atribuidos ?? [],
          },
        });
      } else {
        const salva = await salvarTarefa({
          ...campos,
          fk_casa_id: casaId,
          tipo: "unitaria",
        });
        setResumo({
          salva: {
            ...preparada,
            usuarios_atribuidos: salva.usuarios_atribuidos,
          },
          sorteio: sorteio && {
            ...sorteio,
            sorteadoId: salva.usuarios_atribuidos[0],
          },
        });
      }
    } catch (erro: unknown) {
      setErroEnvio(
        mensagemErroAoSalvarTarefa(erro, "Não foi possível criar a tarefa."),
      );
    } finally {
      envioEmAndamento.current = false;
      setSalvando(false);
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
    setModoAtribuicao("manual");
    setRotativa(false);
    setParticipantes([]);
    setDiasSemana([]);
    setSemanas(1);
    setErros({});
    setResumo(null);
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
              <Text accessibilityRole="header" style={styles.title}>
                {resumo?.pendente
                  ? "CONFIRA A TAREFA"
                  : tarefa
                    ? tarefa.rotatividade
                      ? "RODÍZIO CADASTRADO!"
                      : "TAREFA CRIADA!"
                    : "NOVA TAREFA"}
              </Text>
              <Text style={styles.houseName}>{casa?.nome ?? "Sua casa"}</Text>
              <Text style={styles.body}>
                {tarefa
                  ? "Confira os detalhes abaixo."
                  : "Organize o que precisa ser feito na casa."}
              </Text>
              {rotativa && !tarefa && (
                <Text style={styles.help}>
                  Configure o rodízio e distribua ocorrências automaticamente.
                </Text>
              )}
              {tarefa?.rotatividade && (
                <Text style={styles.help}>
                  Rodízio salvo. As ocorrências serão criadas nos dias
                  programados e atribuídas automaticamente pelo balanceamento.
                </Text>
              )}
            </View>

            {!contexto && !tarefa ? (
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
                    <RefreshCw color={Caldera.obsidian} size={18} />
                    <Text style={styles.body}>Tentar novamente</Text>
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
                    {resumo?.pendente
                      ? "Conferir detalhes"
                      : tarefa.rotatividade
                        ? "Rodízio salvo"
                        : "Detalhes salvos"}
                  </Text>
                  {resumo?.sorteio && (
                    <RoletaResponsavel
                      {...resumo.sorteio}
                      salvando={salvando}
                      onGirar={
                        resumo.pendente
                          ? () =>
                              void gravarTarefa(
                                resumo.pendente,
                                resumo.sorteio.casaId,
                                resumo.sorteio,
                              )
                          : undefined
                      }
                    />
                  )}
                  <ErroCampo mensagem={erroEnvio} />
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
                    <Text style={styles.body}>
                      {tarefa.atraso_maximo}{" "}
                      {tarefa.atraso_maximo === 1 ? "dia" : "dias"}
                    </Text>
                    <Text style={styles.help}>Modo do prazo</Text>
                    <Text style={styles.body}>
                      {tarefa.modo_prazo === "dia_fixo"
                        ? "Dia fixo"
                        : "Intervalo"}
                    </Text>
                    {tarefa.data_fixa && (
                      <Text style={styles.body}>
                        Vencimento: {tarefa.data_fixa}
                      </Text>
                    )}
                  </View>
                  {!tarefa.rotatividade && !resumo?.sorteio && (
                    <View style={styles.section}>
                      <Text style={styles.help}>Responsável</Text>
                      <Text style={styles.body}>
                        {
                          moradores.find(
                            (morador) =>
                              morador.id === tarefa.usuarios_atribuidos?.[0],
                          )?.nome
                        }
                      </Text>
                    </View>
                  )}
                  {tarefa.rotatividade && (
                    <View style={styles.section}>
                      <Text style={styles.help}>Participantes elegíveis</Text>
                      {tarefa.rotatividade.participantes.map((id) => (
                        <Text key={id} style={styles.body}>
                          {moradores.find((morador) => morador.id === id)?.nome}
                        </Text>
                      ))}
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
                      <Text style={styles.help}>
                        A cada ocorrência, o sistema escolhe o participante
                        elegível com menor pontuação potencial acumulada. A
                        ordem selecionada desempata pontuações iguais.
                      </Text>
                    </View>
                  )}
                </View>
                {resumo?.pendente ? (
                  <MotionPressable
                    accessibilityRole="button"
                    disabled={salvando}
                    onPress={() => {
                      setResumo(null);
                      setErroEnvio(undefined);
                    }}
                    style={styles.button}
                  >
                    <Text style={styles.body}>Voltar para editar</Text>
                  </MotionPressable>
                ) : (
                  <MotionPressable
                    accessibilityRole="button"
                    onPress={criarOutraTarefa}
                    style={styles.button}
                  >
                    <Plus color={Caldera.obsidian} size={18} />
                    <Text style={styles.body}>
                      {tarefa.rotatividade
                        ? "Criar outro rodízio"
                        : "Criar outra tarefa"}
                    </Text>
                  </MotionPressable>
                )}
              </>
            ) : (
              <>
                <View style={cardStyle}>
                  <View style={styles.section}>
                    <Text
                      accessibilityRole="header"
                      style={[styles.sectionTitle, styles.detailsTitle]}
                    >
                      DETALHES
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
                      style={[
                        styles.input,
                        styles.description,
                        Platform.OS !== "web" && { height: alturaDescricao },
                      ]}
                      placeholder="O que precisa ser feito?"
                      placeholderTextColor={Caldera.obsidian}
                      selectionColor={Caldera.ember}
                      multiline
                      numberOfLines={1}
                      scrollEnabled={false}
                      onContentSizeChange={
                        Platform.OS === "web"
                          ? undefined
                          : (event) =>
                              setAlturaDescricao(
                                Math.max(
                                  56,
                                  Math.ceil(
                                    event.nativeEvent.contentSize.height,
                                  ),
                                ),
                              )
                      }
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
                    <Text style={styles.help}>
                      Escolha de 1 a 5 dias. A pontuação diminui a cada dia de
                      atraso.
                    </Text>
                    <View style={styles.options} accessibilityRole="radiogroup">
                      {prazosTarefa.map((opcao) => (
                        <MotionPressable
                          key={opcao}
                          accessibilityRole="radio"
                          accessibilityLabel={`${opcao} ${opcao === 1 ? "dia" : "dias"} de tolerância`}
                          accessibilityState={{
                            checked: atrasoMaximo === opcao,
                          }}
                          onPress={() => {
                            setAtrasoMaximo(opcao);
                            setErros((atuais) => ({
                              ...atuais,
                              atrasoMaximo: undefined,
                            }));
                          }}
                          style={[
                            styles.option,
                            atrasoMaximo === opcao && styles.selected,
                          ]}
                        >
                          <IndicadorSelecao
                            selecionado={atrasoMaximo === opcao}
                          />
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
                        accessibilityState={{
                          checked: modoPrazo === "intervalo",
                        }}
                        onPress={() => setModoPrazo("intervalo")}
                        style={[
                          styles.option,
                          modoPrazo === "intervalo" && styles.selected,
                        ]}
                      >
                        <IndicadorSelecao
                          selecionado={modoPrazo === "intervalo"}
                        />
                        <Text style={styles.body}>Intervalo</Text>
                      </MotionPressable>
                      <MotionPressable
                        accessibilityRole="radio"
                        accessibilityState={{
                          checked: modoPrazo === "dia_fixo",
                        }}
                        onPress={() => setModoPrazo("dia_fixo")}
                        style={[
                          styles.option,
                          modoPrazo === "dia_fixo" && styles.selected,
                        ]}
                      >
                        <IndicadorSelecao
                          selecionado={modoPrazo === "dia_fixo"}
                        />
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
                          accessibilityLabel="Data do vencimento no formato dia, mês e ano"
                          autoCapitalize="none"
                          inputMode="numeric"
                          placeholder="DD-MM-AAAA"
                          placeholderTextColor={Caldera.obsidian}
                          selectionColor={Caldera.ember}
                          style={styles.input}
                          value={dataFixa}
                          onChangeText={(valor) => {
                            setDataFixa(formatarDataDigitada(valor));
                            setErros((atuais) => ({
                              ...atuais,
                              dataFixa: undefined,
                            }));
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
                    {podeCriarRotativa && (
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
                            disabled={salvando}
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
                    )}
                    <Text style={styles.body}>
                      {rotativa
                        ? "Participantes do rodízio *"
                        : sortear
                          ? "Responsável"
                          : "Responsável *"}
                    </Text>
                    {!rotativa && (
                      <View
                        style={styles.options}
                        accessibilityRole="radiogroup"
                        accessibilityLabel="Modo de atribuição"
                      >
                        {modosAtribuicaoTarefa.map(({ valor, rotulo }) => (
                          <MotionPressable
                            key={valor}
                            accessibilityRole="radio"
                            accessibilityState={{
                              checked: modoAtribuicao === valor,
                            }}
                            aria-checked={modoAtribuicao === valor}
                            disabled={salvando}
                            onPress={() => {
                              setModoAtribuicao(valor);
                              setErros((atuais) => ({
                                ...atuais,
                                responsavel: undefined,
                              }));
                            }}
                            style={[
                              styles.option,
                              modoAtribuicao === valor && styles.selected,
                            ]}
                          >
                            <IndicadorSelecao
                              selecionado={modoAtribuicao === valor}
                            />
                            <Text style={styles.body}>{rotulo}</Text>
                          </MotionPressable>
                        ))}
                      </View>
                    )}
                    <Text style={styles.help}>
                      {rotativa
                        ? "Escolha pelo menos dois moradores, na ordem em que vão participar. O primeiro selecionado começa."
                        : sortear
                          ? "O sorteio inclui o administrador e os moradores ativos."
                          : "Escolha apenas um morador. Ao escolher outro, a seleção anterior é substituída."}
                    </Text>
                  </View>
                  {!sortear && responsaveisDisponiveis.length === 0 && (
                    <Text style={styles.help}>
                      Não há moradores disponíveis para esta casa.
                    </Text>
                  )}
                  {rotativa && moradores.length === 1 && (
                    <Text style={styles.help}>
                      O rodízio precisa de pelo menos dois moradores na casa.
                    </Text>
                  )}
                  {!sortear && (
                    <View
                      style={styles.section}
                      accessibilityRole={rotativa ? undefined : "radiogroup"}
                      accessibilityLabel={
                        rotativa
                          ? "Participantes do rodízio"
                          : "Responsável pela tarefa"
                      }
                    >
                      {(rotativa ? moradores : responsaveisDisponiveis).map(
                        (morador) => {
                          const selecionado = rotativa
                            ? participantes.includes(morador.id)
                            : responsavel === morador.id;
                          const nomeExibido = morador.nome;
                          return (
                            <MotionPressable
                              key={morador.id}
                              accessibilityRole={
                                rotativa ? "checkbox" : "radio"
                              }
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
                              <Avatar
                                nome={morador.nome}
                                foto={morador.foto}
                                tamanho={40}
                              />
                              <Text style={[styles.body, styles.residentName]}>
                                {nomeExibido}
                              </Text>
                              {rotativa ? (
                                <View
                                  accessible={false}
                                  style={styles.checkbox}
                                >
                                  <Text style={styles.help}>
                                    {selecionado ? "✓" : ""}
                                  </Text>
                                </View>
                              ) : (
                                <IndicadorSelecao selecionado={selecionado} />
                              )}
                            </MotionPressable>
                          );
                        },
                      )}
                    </View>
                  )}
                  {!sortear && (
                    <ErroCampo
                      mensagem={
                        rotativa ? erros.participantes : erros.responsavel
                      }
                    />
                  )}
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
                {erroEnvio && (
                  <Text accessibilityLiveRegion="polite" style={styles.aviso}>
                    ⚠ {erroEnvio}
                  </Text>
                )}
                <MotionPressable
                  accessibilityRole="button"
                  accessibilityState={{ busy: salvando, disabled: salvando }}
                  disabled={salvando}
                  onPress={prepararCriacao}
                  style={styles.button}
                >
                  {rotativa ? (
                    <Repeat color={Caldera.obsidian} size={18} />
                  ) : (
                    <Plus color={Caldera.obsidian} size={18} />
                  )}
                  <Text style={styles.body}>
                    {salvando
                      ? "Criando..."
                      : rotativa
                        ? "Conferir rodízio"
                        : sortear
                          ? "Conferir detalhes"
                          : "Criar tarefa"}
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
    paddingTop: Spacing.four,
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
  houseName: {
    color: Caldera.ember,
    fontFamily: CompactFont,
    fontSize: 32,
    lineHeight: 40,
    letterSpacing: 0.64,
  },
  detailsTitle: { fontSize: 32, lineHeight: 40, letterSpacing: 0.64 },
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
  aviso: {
    color: "#b3001b",
    backgroundColor: "#ffe3e6",
    borderLeftWidth: 4,
    borderLeftColor: "#b3001b",
    borderRadius: 8,
    paddingVertical: 8,
    paddingHorizontal: 12,
    fontSize: 14,
    lineHeight: 20,
    fontWeight: "700",
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
  description: { borderRadius: 28, lineHeight: 24 },
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
  residentName: { flex: 1 },
  button: {
    minHeight: 56,
    paddingVertical: 12,
    paddingHorizontal: Spacing.four,
    borderRadius: 800,
    backgroundColor: Caldera.ember,
    alignItems: "center",
    flexDirection: "row",
    gap: Spacing.two,
    justifyContent: "center",
  },
});
