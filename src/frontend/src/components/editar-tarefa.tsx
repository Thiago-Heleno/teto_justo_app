import { useRef, useState } from "react";
import { StyleSheet, Text, TextInput, View } from "react-native";
import { Save, X } from "lucide-react-native";
import Animated, { FadeInRight, ReduceMotion } from "react-native-reanimated";

import { Avatar } from "@/components/avatar";
import { MotionPressable } from "@/components/motion-pressable";
import {
  RoletaResponsavel,
  type ResultadoRoleta,
} from "@/components/roleta-responsavel";
import {
  modosAtribuicaoTarefa,
  pesosTarefa,
  prazosTarefa,
  type ModoAtribuicao,
  type PesoTarefa,
  type PrazoDias,
} from "@/constants/tarefa";
import { Caldera, CompactFont, Spacing } from "@/constants/theme";
import {
  mensagemErroAoSalvarTarefa,
  type Morador,
  type Tarefa,
  type TarefaAtualizar,
  type UsuarioAtual,
} from "@/services/tarefas-api";
import { formatarDataDigitada } from "@/utils/data-fixa";
import {
  prepararAtribuicaoTarefa,
  prepararEdicaoTarefa,
  type ErrosEdicaoTarefa,
} from "@/utils/edicao-tarefa";

type Props = {
  tarefa: Tarefa;
  moradores: Morador[];
  administrador?: UsuarioAtual;
  edicaoCompleta: boolean;
  onCancelar: () => void;
  onConcluir: () => void;
  onSalvar: (dados: TarefaAtualizar) => Promise<Tarefa>;
};

function ErroCampo({ mensagem }: { mensagem?: string }) {
  if (!mensagem) return null;
  return (
    <Text accessibilityLiveRegion="polite" style={styles.errorText}>
      Atenção: {mensagem}
    </Text>
  );
}

export function EditarTarefa({
  tarefa,
  moradores,
  administrador,
  edicaoCompleta,
  onCancelar,
  onConcluir,
  onSalvar,
}: Props) {
  const [nome, setNome] = useState(tarefa.nome);
  const [descricao, setDescricao] = useState(tarefa.descricao ?? "");
  const [peso, setPeso] = useState<PesoTarefa>(tarefa.peso as PesoTarefa);
  const [prazoDias, setPrazoDias] = useState<PrazoDias | null>(
    (tarefa.prazo_dias ?? null) as PrazoDias | null,
  );
  const [atrasoMaximo, setAtrasoMaximo] = useState(tarefa.atraso_maximo);
  const [dataFixa, setDataFixa] = useState(() =>
    formatarDataDigitada(tarefa.data_fixa ?? ""),
  );
  const [responsavel, setResponsavel] = useState(
    tarefa.usuarios_atribuidos[0] ?? "",
  );
  const [modoAtribuicao, setModoAtribuicao] =
    useState<ModoAtribuicao>("manual");
  const [sorteio, setSorteio] = useState<{
    roleta: ResultadoRoleta;
    pendente?: TarefaAtualizar;
  }>();
  const [erros, setErros] = useState<ErrosEdicaoTarefa>({});
  const [salvando, setSalvando] = useState(false);
  const [erroEnvio, setErroEnvio] = useState<string>();
  const envioEmAndamento = useRef(false);
  const podeSortear =
    tarefa.tipo === "unitaria" &&
    (tarefa.estado_atual === "pendente" || tarefa.estado_atual === "atrasada");
  const sortear = podeSortear && modoAtribuicao === "aleatorio";
  const moradoresDisponiveis =
    podeSortear &&
    administrador &&
    !moradores.some(({ id }) => id === administrador.id)
      ? [...moradores, { ...administrador, foto: null }]
      : moradores;

  function prepararEdicao() {
    if (sorteio || envioEmAndamento.current) return;
    const resultado = prepararEdicaoTarefa(
      {
        nome,
        descricao,
        peso,
        prazoDias,
        atrasoMaximo,
        dataFixa,
        responsavel,
        modoAtribuicao: sortear ? "aleatorio" : "manual",
      },
      tarefa,
      moradoresDisponiveis,
    );
    setErros(resultado.erros);
    if (!resultado.dados) return;

    if (resultado.dados.modo_atribuicao === "aleatorio") {
      setErroEnvio(undefined);
      setSorteio({
        pendente: resultado.dados,
        roleta: {
          casaId: tarefa.fk_casa_id,
          candidatos: moradores,
          administrador,
        },
      });
      return;
    }

    void gravarEdicao(resultado.dados);
  }

  async function gravarEdicao(
    dados: TarefaAtualizar,
    roleta?: ResultadoRoleta,
  ) {
    if (envioEmAndamento.current) return;
    envioEmAndamento.current = true;
    setSalvando(true);
    setErroEnvio(undefined);
    try {
      const atualizada = await onSalvar(dados);
      if (roleta) {
        setSorteio({
          roleta: { ...roleta, sorteadoId: atualizada.usuarios_atribuidos[0] },
        });
      } else {
        onConcluir();
      }
    } catch (erro: unknown) {
      setErroEnvio(
        mensagemErroAoSalvarTarefa(erro, "Não foi possível editar a tarefa."),
      );
    } finally {
      envioEmAndamento.current = false;
      setSalvando(false);
    }
  }

  if (sorteio) {
    const { pendente, roleta } = sorteio;
    return (
      <View style={styles.container}>
        <View style={styles.card}>
          <Text accessibilityRole="header" style={styles.title}>
            {pendente ? "CONFIRA A EDIÇÃO" : "TAREFA SALVA"}
          </Text>
          {pendente && <Text style={styles.label}>{tarefa.nome}</Text>}
          <RoletaResponsavel
            {...roleta}
            salvando={salvando}
            onGirar={
              pendente ? () => void gravarEdicao(pendente, roleta) : undefined
            }
          />
          <ErroCampo mensagem={erroEnvio} />
          <MotionPressable
            accessibilityRole="button"
            disabled={salvando}
            onPress={
              pendente
                ? () => {
                    setSorteio(undefined);
                    setErroEnvio(undefined);
                  }
                : onConcluir
            }
            style={pendente ? styles.cancelButton : styles.saveButton}
          >
            <Text style={styles.saveText}>
              {pendente ? "Voltar para editar" : "Continuar"}
            </Text>
          </MotionPressable>
        </View>
      </View>
    );
  }

  if (!edicaoCompleta) {
    return (
      <View style={styles.container}>
        <Text accessibilityRole="header" style={styles.title}>
          ATRIBUIR RESPONSÁVEL
        </Text>
        <View style={styles.card}>
          <Text style={styles.label}>{tarefa.nome}</Text>
          <View
            accessibilityRole="radiogroup"
            accessibilityLabel="Modo de atribuição"
            style={styles.options}
          >
            {modosAtribuicaoTarefa.map(({ valor, rotulo }) => (
              <MotionPressable
                key={valor}
                accessibilityRole="radio"
                accessibilityState={{ checked: modoAtribuicao === valor }}
                aria-checked={modoAtribuicao === valor}
                disabled={salvando}
                onPress={() => {
                  setModoAtribuicao(valor);
                  setErros({});
                  setErroEnvio(undefined);
                }}
                style={[
                  styles.option,
                  modoAtribuicao === valor && styles.selected,
                ]}
              >
                <Text style={styles.optionText}>{rotulo}</Text>
              </MotionPressable>
            ))}
          </View>
          {sortear ? (
            <>
              <Text style={styles.help}>
                O sorteio inclui o administrador e os moradores ativos.
              </Text>
              <RoletaResponsavel
                casaId={tarefa.fk_casa_id}
                candidatos={moradores}
                administrador={administrador}
                salvando={salvando}
                onGirar={() =>
                  void gravarEdicao(
                    { modo_atribuicao: "aleatorio" },
                    {
                      casaId: tarefa.fk_casa_id,
                      candidatos: moradores,
                      administrador,
                    },
                  )
                }
              />
            </>
          ) : (
            <>
              <View
                accessibilityRole="radiogroup"
                accessibilityLabel="Responsável pela tarefa"
                style={styles.options}
              >
                {moradoresDisponiveis.map((morador) => (
                  <MotionPressable
                    key={morador.id}
                    accessibilityRole="radio"
                    accessibilityState={{ checked: responsavel === morador.id }}
                    aria-checked={responsavel === morador.id}
                    accessibilityLabel={morador.nome}
                    disabled={salvando}
                    onPress={() => {
                      setResponsavel(morador.id);
                      setErros({});
                    }}
                    style={[
                      styles.option,
                      styles.opcaoMorador,
                      responsavel === morador.id && styles.selected,
                    ]}
                  >
                    <Avatar
                      nome={morador.nome}
                      foto={morador.foto}
                      tamanho={40}
                    />
                    <Text style={[styles.optionText, { flexShrink: 1 }]}>
                      {morador.nome}
                    </Text>
                  </MotionPressable>
                ))}
              </View>
              <ErroCampo mensagem={erros.responsavel} />
              <MotionPressable
                accessibilityRole="button"
                disabled={salvando}
                onPress={() => {
                  const resultado = prepararAtribuicaoTarefa(
                    "manual",
                    responsavel,
                    moradoresDisponiveis,
                  );
                  setErros(resultado.erros);
                  if (resultado.dados) void gravarEdicao(resultado.dados);
                }}
                style={styles.saveButton}
              >
                <Text style={styles.saveText}>
                  {salvando ? "Salvando..." : "Salvar responsável"}
                </Text>
              </MotionPressable>
            </>
          )}
          <ErroCampo mensagem={erroEnvio} />
          <MotionPressable
            accessibilityRole="button"
            disabled={salvando}
            onPress={onCancelar}
            style={styles.cancelButton}
          >
            <Text style={styles.cancelText}>Cancelar</Text>
          </MotionPressable>
        </View>
      </View>
    );
  }

  return (
    <Animated.View
      entering={FadeInRight.duration(260).reduceMotion(ReduceMotion.System)}
      style={styles.container}
    >
      <Text style={styles.eyebrow}>EDIÇÃO DE TAREFA</Text>
      <Text accessibilityRole="header" style={styles.title}>
        EDITAR TAREFA
      </Text>
      <Text style={styles.help}>Campos com * são obrigatórios.</Text>

      <View style={styles.card}>
        <View style={styles.field}>
          <Text style={styles.label}>Nome *</Text>
          <TextInput
            accessibilityLabel="Nome da tarefa, obrigatório"
            onChangeText={(valor) => {
              setNome(valor);
              setErros((atuais) => ({ ...atuais, nome: undefined }));
            }}
            placeholderTextColor={Caldera.obsidian}
            selectionColor={Caldera.ember}
            style={styles.input}
            value={nome}
          />
          <ErroCampo mensagem={erros.nome} />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Descrição</Text>
          <TextInput
            accessibilityLabel="Descrição da tarefa"
            multiline
            onChangeText={setDescricao}
            selectionColor={Caldera.ember}
            style={[styles.input, styles.description]}
            textAlignVertical="top"
            value={descricao}
          />
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Peso *</Text>
          <View accessibilityRole="radiogroup" style={styles.options}>
            {pesosTarefa.map((opcao) => (
              <MotionPressable
                accessibilityRole="radio"
                accessibilityState={{ checked: peso === opcao }}
                key={opcao}
                onPress={() => setPeso(opcao)}
                style={[styles.option, peso === opcao && styles.selected]}
              >
                <Text style={styles.optionText}>{opcao}</Text>
              </MotionPressable>
            ))}
          </View>
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Prazo *</Text>
          <View accessibilityRole="radiogroup" style={styles.options}>
            {prazosTarefa.map((opcao) => (
              <MotionPressable
                accessibilityRole="radio"
                accessibilityState={{ checked: prazoDias === opcao }}
                key={opcao}
                onPress={() => setPrazoDias(opcao)}
                style={[styles.option, prazoDias === opcao && styles.selected]}
              >
                <Text style={styles.optionText}>
                  {opcao} {opcao === 1 ? "dia" : "dias"}
                </Text>
              </MotionPressable>
            ))}
          </View>
          <ErroCampo mensagem={erros.prazoDias} />
          {tarefa.modo_prazo === "intervalo" && (
            <Text style={styles.help}>
              O vencimento é calculado a partir do início e do prazo em dias.
              Uma data específica só pode ser escolhida no modo dia fixo,
              definido na criação da tarefa.
            </Text>
          )}
        </View>

        <View style={styles.field}>
          <Text style={styles.label}>Tolerância após o prazo</Text>
          <View accessibilityRole="radiogroup" style={styles.options}>
            {prazosTarefa.map((opcao) => (
              <MotionPressable
                accessibilityRole="radio"
                accessibilityState={{ checked: atrasoMaximo === opcao }}
                key={opcao}
                onPress={() => setAtrasoMaximo(opcao)}
                style={[
                  styles.option,
                  atrasoMaximo === opcao && styles.selected,
                ]}
              >
                <Text style={styles.optionText}>
                  {opcao} {opcao === 1 ? "dia" : "dias"}
                </Text>
              </MotionPressable>
            ))}
          </View>
          <ErroCampo mensagem={erros.atrasoMaximo} />
        </View>

        {tarefa.modo_prazo === "dia_fixo" && (
          <View style={styles.field}>
            <Text style={styles.label}>Data do vencimento</Text>
            {tarefa.tipo === "rotativa" && (
              <Text style={styles.help}>
                A alteração vale apenas para esta ocorrência do rodízio.
              </Text>
            )}
            <TextInput
              accessibilityLabel="Data do vencimento no formato dia, mês e ano"
              autoCapitalize="none"
              inputMode="numeric"
              onChangeText={(valor) => setDataFixa(formatarDataDigitada(valor))}
              placeholder="DD-MM-AAAA"
              placeholderTextColor={Caldera.obsidian}
              selectionColor={Caldera.ember}
              style={styles.input}
              value={dataFixa}
            />
            <ErroCampo mensagem={erros.dataFixa} />
          </View>
        )}

        <View style={styles.field}>
          <Text style={styles.label}>
            {sortear ? "Responsável" : "Responsável *"}
          </Text>
          {podeSortear && (
            <View
              accessibilityRole="radiogroup"
              accessibilityLabel="Modo de atribuição"
              style={styles.options}
            >
              {modosAtribuicaoTarefa.map(({ valor, rotulo }) => (
                <MotionPressable
                  key={valor}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: modoAtribuicao === valor }}
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
                  <Text style={styles.optionText}>{rotulo}</Text>
                </MotionPressable>
              ))}
            </View>
          )}
          {sortear ? (
            <Text style={styles.help}>
              O sorteio inclui o administrador e os moradores ativos.
            </Text>
          ) : (
            <View
              accessibilityRole="radiogroup"
              accessibilityLabel="Responsável pela tarefa"
              style={styles.options}
            >
              {moradoresDisponiveis.map((morador) => (
                <MotionPressable
                  accessibilityRole="radio"
                  accessibilityState={{ checked: responsavel === morador.id }}
                  aria-checked={responsavel === morador.id}
                  accessibilityLabel={morador.nome}
                  key={morador.id}
                  onPress={() => {
                    setResponsavel(morador.id);
                    setErros((atuais) => ({
                      ...atuais,
                      responsavel: undefined,
                    }));
                  }}
                  style={[
                    styles.option,
                    styles.opcaoMorador,
                    responsavel === morador.id && styles.selected,
                  ]}
                >
                  <Avatar
                    nome={morador.nome}
                    foto={morador.foto}
                    tamanho={40}
                  />
                  <Text style={[styles.optionText, { flexShrink: 1 }]}>
                    {morador.nome}
                  </Text>
                </MotionPressable>
              ))}
            </View>
          )}
          {!sortear && <ErroCampo mensagem={erros.responsavel} />}
        </View>

        {erroEnvio && (
          <Text accessibilityLiveRegion="polite" style={styles.errorText}>
            {erroEnvio}
          </Text>
        )}

        <View style={styles.actions}>
          <MotionPressable
            accessibilityRole="button"
            accessibilityState={{ busy: salvando, disabled: salvando }}
            disabled={salvando}
            onPress={prepararEdicao}
            style={[styles.saveButton, salvando && styles.disabled]}
          >
            <Save color={Caldera.obsidian} size={18} />
            <Text style={styles.saveText}>
              {salvando
                ? "Salvando..."
                : sortear
                  ? "Conferir detalhes"
                  : "Salvar alterações"}
            </Text>
          </MotionPressable>
          <MotionPressable
            accessibilityRole="button"
            disabled={salvando}
            onPress={onCancelar}
            style={styles.cancelButton}
          >
            <X color={Caldera.obsidian} size={18} />
            <Text style={styles.cancelText}>Cancelar</Text>
          </MotionPressable>
        </View>
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    width: "100%",
    maxWidth: 1040,
    alignSelf: "center",
    gap: Spacing.three,
  },
  eyebrow: { color: Caldera.ember, fontSize: 12, fontWeight: "500" },
  title: {
    color: Caldera.obsidian,
    fontFamily: CompactFont,
    fontSize: 48,
    lineHeight: 48,
    letterSpacing: 0.96,
  },
  help: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  card: {
    backgroundColor: Caldera.limestone,
    borderRadius: 40,
    padding: Spacing.five,
    gap: Spacing.four,
  },
  field: { gap: Spacing.two },
  label: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  input: {
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 20,
    color: Caldera.obsidian,
    fontSize: 16,
    fontWeight: "500",
    paddingHorizontal: Spacing.three,
    paddingVertical: 12,
  },
  description: { minHeight: 112 },
  options: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  option: {
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.three,
    paddingVertical: 10,
  },
  opcaoMorador: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.two,
    maxWidth: "100%",
  },
  selected: { backgroundColor: Caldera.ember },
  optionText: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  errorText: { color: Caldera.obsidian, fontSize: 14, fontWeight: "500" },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: Spacing.two },
  saveButton: {
    alignItems: "center",
    flexDirection: "row",
    gap: Spacing.two,
    backgroundColor: Caldera.ember,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
  },
  disabled: { opacity: 0.6 },
  saveText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
  cancelButton: {
    alignItems: "center",
    flexDirection: "row",
    gap: Spacing.two,
    borderWidth: 1.5,
    borderColor: Caldera.obsidian,
    borderRadius: 800,
    paddingHorizontal: Spacing.four,
    paddingVertical: 12,
  },
  cancelText: { color: Caldera.obsidian, fontSize: 16, fontWeight: "500" },
});
