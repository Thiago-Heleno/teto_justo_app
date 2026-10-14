import { useFocusEffect } from "expo-router";
import { useCallback, useRef, useState } from "react";
import { useStore } from "zustand";

import { ErroApi } from "@/services/api";
import {
  carregarCasa,
  listarMoradoresCasa,
  type Casa,
  type MoradorCasa,
} from "@/services/casas-api";
import { sessao } from "@/services/sessao-store";
import { carregarUsuarioAtual } from "@/services/tarefas-api";

export function mensagemGerenciamento(falha: unknown) {
  if (falha instanceof ErroApi && falha.validacoes.length) {
    return falha.validacoes
      .map(
        ({ loc, msg }) => `${loc.slice(1).join(".") || "Formulário"}: ${msg}`,
      )
      .join("\n");
  }
  if (falha instanceof TypeError)
    return "Falha de conexão. Atualize a lista para conferir o resultado antes de reenviar.";
  return falha instanceof Error
    ? falha.message
    : "Não foi possível concluir a operação.";
}

export function useGerenciamentoCasa(carregarMoradores = true) {
  const { casaAtiva, token } = useStore(sessao);
  const casaId = casaAtiva?.id;
  const [dados, setDados] = useState<{
    casa: Casa;
    moradores: MoradorCasa[];
    usuarioId: string;
  }>();
  const [erro, setErro] = useState<string>();
  const [ocupado, setOcupado] = useState(false);
  const [versao, setVersao] = useState(0);
  const consulta = useRef<AbortController | null>(null);
  const operacao = useRef<AbortController | null>(null);
  const enviando = useRef(false);

  useFocusEffect(
    useCallback(() => {
      const controlador = new AbortController();
      consulta.current = controlador;
      setDados(undefined);
      setErro(undefined);
      if (casaId && token) {
        void Promise.all([
          carregarCasa(casaId, controlador.signal),
          carregarMoradores
            ? listarMoradoresCasa(casaId, controlador.signal)
            : Promise.resolve([] as MoradorCasa[]),
          carregarUsuarioAtual(controlador.signal),
        ])
          .then(([casa, moradores, usuario]) => {
            if (!controlador.signal.aborted)
              setDados({ casa, moradores, usuarioId: usuario.id });
          })
          .catch((falha) => {
            if (!controlador.signal.aborted)
              setErro(mensagemGerenciamento(falha));
          });
      }
      return () => {
        controlador.abort();
        operacao.current?.abort();
        enviando.current = false;
        setOcupado(false);
      };
      // A versão força nova consulta ao atualizar sem trocar de casa.
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [casaId, token, versao, carregarMoradores]),
  );

  const admin = Boolean(dados && dados.casa.fk_usuario_id === dados.usuarioId);
  function atualizar() {
    setVersao((v) => v + 1);
  }

  async function executar<T>(
    acao: (signal: AbortSignal) => Promise<T>,
    sucesso: (valor: T) => void | Promise<void>,
  ) {
    if (!admin || enviando.current || consulta.current?.signal.aborted) return;
    const controlador = new AbortController();
    operacao.current = controlador;
    enviando.current = true;
    setOcupado(true);
    setErro(undefined);
    try {
      const valor = await acao(controlador.signal);
      if (
        !controlador.signal.aborted &&
        sessao.getState().token === token &&
        sessao.getState().casaAtiva?.id === casaId
      )
        await sucesso(valor);
    } catch (falha) {
      if (!controlador.signal.aborted) {
        if (falha instanceof ErroApi && falha.status === 403)
          setDados(undefined);
        setErro(mensagemGerenciamento(falha));
      }
    } finally {
      enviando.current = false;
      if (!controlador.signal.aborted) setOcupado(false);
    }
  }
  return { dados, admin, erro, ocupado, atualizar, executar, setErro };
}
