import { useFocusEffect } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { MotionPressable } from "@/components/motion-pressable";
import { RoletaResponsavel } from "@/components/roleta-responsavel";
import { Caldera, Spacing } from "@/constants/theme";
import { listarMoradoresCasa } from "@/services/casas-api";
import {
  buscarTarefa,
  consultarRoletaTarefa,
  girarRoletaTarefa,
  type RoletaOcorrenciaDetalhe,
  type Tarefa,
} from "@/services/tarefas-api";

type Perfil = { id: string; nome: string };

type Props = {
  tarefaId: string;
  casaId: string;
  fusoDaCasa: string;
  moradores: readonly Perfil[];
  administrador?: Perfil;
  onAtualizada: (tarefa: Tarefa) => void;
};

export function RoletaOcorrencia({
  tarefaId,
  casaId,
  fusoDaCasa,
  moradores,
  administrador,
  onAtualizada,
}: Props) {
  const [roleta, setRoleta] = useState<RoletaOcorrenciaDetalhe>();
  const [operacao, setOperacao] = useState<"consulta" | "giro">();
  const [erro, setErro] = useState<string>();
  const [animar, setAnimar] = useState(false);
  const [perfisAtualizados, setPerfisAtualizados] = useState<Perfil[]>([]);
  const requisicao = useRef<AbortController | null>(null);
  const emFoco = useRef(false);

  const atualizar = useCallback(
    async (acao: "consulta" | "giro" = "consulta") => {
      if (!emFoco.current || requisicao.current) return;
      const controlador = new AbortController();
      requisicao.current = controlador;
      const { signal } = controlador;
      setOperacao(acao);
      setErro(undefined);

      try {
        let detalhe: RoletaOcorrenciaDetalhe;
        let confirmouGiro = false;
        if (acao === "giro") {
          try {
            detalhe = await girarRoletaTarefa(tarefaId, signal);
            confirmouGiro = detalhe.origem === "giro";
          } catch {
            if (signal.aborted) return;
            detalhe = await consultarRoletaTarefa(tarefaId, signal);
            if (
              !signal.aborted &&
              detalhe.estado === "aberta" &&
              detalhe.pode_girar
            )
              setErro("O giro não foi confirmado. Você pode tentar novamente.");
          }
        } else {
          detalhe = await consultarRoletaTarefa(tarefaId, signal);
        }
        if (signal.aborted) return;
        setRoleta(detalhe);
        setAnimar(confirmouGiro);
        if (detalhe.estado === "atribuida") {
          try {
            const tarefa = await buscarTarefa(tarefaId, signal);
            if (!signal.aborted) onAtualizada(tarefa);
          } catch {
            if (!signal.aborted)
              setErro(
                "A atribuição foi confirmada. Atualize para carregar o prazo da tarefa.",
              );
          }
        }
      } catch (falha: unknown) {
        if (signal.aborted) return;
        setRoleta(undefined);
        setAnimar(false);
        setErro(
          acao === "giro"
            ? "Não foi possível confirmar o giro. Atualize para consultar o resultado."
            : falha instanceof Error
              ? falha.message
              : "Não foi possível consultar a roleta.",
        );
      } finally {
        if (requisicao.current === controlador) {
          requisicao.current = null;
          setOperacao(undefined);
        }
      }
    },
    [onAtualizada, tarefaId],
  );

  useFocusEffect(
    useCallback(() => {
      emFoco.current = true;
      void atualizar();
      return () => {
        emFoco.current = false;
        requisicao.current?.abort();
        requisicao.current = null;
      };
    }, [atualizar]),
  );

  const limite =
    roleta?.estado === "agendada"
      ? roleta.abre_em
      : roleta?.estado === "aberta"
        ? roleta.expira_em
        : undefined;
  useEffect(() => {
    if (!limite) return;
    const instante = new Date(limite).getTime();
    if (!Number.isFinite(instante)) return;
    let temporizador: ReturnType<typeof setTimeout>;
    function agendar() {
      const espera = instante - Date.now();
      temporizador = setTimeout(
        espera > 2_147_483_647 ? agendar : () => void atualizar(),
        Math.min(2_147_483_647, Math.max(0, espera)),
      );
    }
    agendar();
    return () => clearTimeout(temporizador);
  }, [atualizar, limite]);

  const perfis = new Map(
    moradores.map((morador) => [morador.id, morador.nome]),
  );
  if (administrador) perfis.set(administrador.id, administrador.nome);
  for (const morador of perfisAtualizados) perfis.set(morador.id, morador.nome);
  const faltamPerfis = Boolean(
    roleta &&
    (roleta.candidatos.some((id) => !perfis.has(id)) ||
      (roleta.responsavel_id && !perfis.has(roleta.responsavel_id))),
  );
  useEffect(() => {
    if (!faltamPerfis || !roleta) return;
    const controlador = new AbortController();
    listarMoradoresCasa(casaId, controlador.signal)
      .then((novosPerfis) => {
        if (!controlador.signal.aborted) setPerfisAtualizados(novosPerfis);
      })
      .catch(() => {});
    return () => controlador.abort();
  }, [casaId, faltamPerfis, roleta]);

  let mensagem: string | undefined;
  if (roleta?.estado === "agendada" || roleta?.estado === "aberta") {
    const horario = new Intl.DateTimeFormat("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
      timeZone: fusoDaCasa,
    }).format(
      new Date(
        roleta.estado === "agendada" ? roleta.abre_em : roleta.expira_em,
      ),
    );
    mensagem =
      roleta.estado === "agendada"
        ? `Abre em ${horario}`
        : `Giro até ${horario}`;
    if (roleta.estado === "aberta" && !roleta.pode_girar)
      mensagem += roleta.candidatos.length
        ? " · Apenas participantes ativos podem girar."
        : " · Sem participantes ativos.";
  } else if (roleta?.estado === "expirada") {
    mensagem = "Aguardando a atribuição pelo próximo job de rodízios.";
  } else if (roleta?.estado === "atribuindo") {
    mensagem = "Aguardando a confirmação do responsável.";
  } else if (!roleta && operacao) {
    mensagem = "Consultando a roleta…";
  }

  return (
    <View style={styles.secao}>
      {mensagem && (
        <Text accessibilityLiveRegion="polite" style={styles.texto}>
          {mensagem}
        </Text>
      )}
      {roleta && (
        <RoletaResponsavel
          candidatos={roleta.candidatos.map((id) => ({
            id,
            nome: perfis.get(id) ?? "",
          }))}
          sorteadoId={roleta.responsavel_id ?? undefined}
          nomeResponsavel={perfis.get(roleta.responsavel_id ?? "")}
          origem={roleta.origem}
          animarResultado={animar}
          exibirCandidatos={roleta.estado === "aberta"}
          salvando={operacao === "giro" && roleta.estado !== "atribuida"}
          onGirar={
            roleta.pode_girar && operacao !== "consulta"
              ? () => void atualizar("giro")
              : undefined
          }
        />
      )}
      {erro && (
        <Text accessibilityLiveRegion="polite" style={styles.texto}>
          {erro}
        </Text>
      )}
      {(roleta?.estado !== "atribuida" || erro) && (
        <MotionPressable
          accessibilityRole="button"
          accessibilityLabel="Atualizar roleta"
          accessibilityState={{
            busy: Boolean(operacao),
            disabled: Boolean(operacao),
          }}
          disabled={Boolean(operacao)}
          onPress={() => void atualizar()}
          style={styles.atualizar}
        >
          <Text style={styles.texto}>Atualizar</Text>
        </MotionPressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  secao: { gap: Spacing.two },
  texto: { color: Caldera.obsidian },
  atualizar: {
    alignSelf: "flex-start",
    minHeight: 44,
    justifyContent: "center",
    paddingHorizontal: Spacing.two,
    borderWidth: 1,
    borderColor: Caldera.obsidian,
    borderRadius: 20,
  },
});
