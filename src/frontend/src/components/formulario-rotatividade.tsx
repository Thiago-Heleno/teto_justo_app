import { useState } from "react";
import { Pressable, Switch, Text, TextInput, View } from "react-native";

import { Acao, styles } from "@/components/gerenciamento-ui";
import {
  diasSemanaTarefa,
  intervalosSemanasTarefa,
  pesosTarefa,
  prazosTarefa,
  type PesoTarefa,
  type PrazoDias,
} from "@/constants/tarefa";
import type { MoradorCasa } from "@/services/casas-api";
import type {
  Rotatividade,
  RotatividadeAtualizar,
  RotatividadeCriar,
} from "@/services/rotatividade-api";

function Opcoes({
  titulo,
  valores,
  valor,
  selecionar,
  ocupado,
}: {
  titulo: string;
  valores: readonly number[];
  valor: number;
  selecionar: (v: number) => void;
  ocupado: boolean;
}) {
  return (
    <View style={{ gap: 8 }}>
      <Text style={styles.label}>{titulo}</Text>
      <View style={styles.row}>
        {valores.map((v) => (
          <Pressable
            key={v}
            accessibilityRole="radio"
            accessibilityLabel={`${titulo}: ${v}`}
            accessibilityState={{ checked: valor === v, disabled: ocupado }}
            disabled={ocupado}
            onPress={() => selecionar(v)}
            style={[
              styles.button,
              valor === v && { backgroundColor: "#fc5000" },
            ]}
          >
            <Text style={styles.buttonText}>{v}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

export function FormularioRotatividade({
  casaId,
  moradores,
  regra,
  ocupado,
  onCriar,
  onEditar,
  onCancelar,
}: {
  casaId: string;
  moradores: MoradorCasa[];
  regra: Rotatividade | null;
  ocupado: boolean;
  onCriar: (dados: RotatividadeCriar) => void;
  onEditar: (dados: RotatividadeAtualizar) => void;
  onCancelar: () => void;
}) {
  const [nome, setNome] = useState(regra?.nome ?? "");
  const [descricao, setDescricao] = useState(regra?.descricao ?? "");
  const [ativa, setAtiva] = useState(regra?.ativa ?? true);
  const [peso, setPeso] = useState(1);
  const [prazo, setPrazo] = useState(1);
  const [atraso, setAtraso] = useState(1);
  const [intervalo, setIntervalo] = useState(1);
  const [modo, setModo] = useState<"intervalo" | "dia_fixo">("intervalo");
  const [participantes, setParticipantes] = useState<string[]>([]);
  const [dias, setDias] = useState<number[]>([]);
  const [erro, setErro] = useState<string>();

  function enviar() {
    if (ocupado) return;
    if (!nome.trim()) {
      setErro("Informe o nome da regra.");
      return;
    }
    if (regra) {
      onEditar({ nome: nome.trim(), descricao: descricao.trim(), ativa });
      return;
    }
    if (participantes.length < 2) {
      setErro("Selecione pelo menos dois moradores.");
      return;
    }
    if (!dias.length) {
      setErro("Selecione pelo menos um dia da semana.");
      return;
    }
    setErro(undefined);
    onCriar({
      fk_casa_id: casaId,
      nome: nome.trim(),
      descricao: descricao.trim(),
      peso: peso as PesoTarefa,
      prazo_dias: prazo as PrazoDias,
      atraso_maximo: atraso as PrazoDias,
      modo_prazo: modo,
      participantes,
      dias_semana: [...dias].sort((a, b) => a - b),
      intervalo_semanas: intervalo,
    });
  }
  return (
    <View style={styles.card}>
      <Text style={styles.subtitle}>
        {regra ? "Editar regra" : "Nova regra"}
      </Text>
      <Text style={styles.label}>Nome</Text>
      <TextInput
        accessibilityLabel="Nome da regra"
        value={nome}
        onChangeText={setNome}
        editable={!ocupado}
        style={styles.input}
      />
      <Text style={styles.label}>Descrição</Text>
      <TextInput
        accessibilityLabel="Descrição da regra"
        value={descricao}
        onChangeText={setDescricao}
        multiline
        editable={!ocupado}
        style={styles.input}
      />
      {regra ? (
        <>
          <Text style={styles.text}>
            Nesta versão, a API permite editar nome, descrição e status.
            Calendário e participantes são definidos na criação.
          </Text>
          <View style={styles.row}>
            <Text style={styles.label}>Regra ativa</Text>
            <Switch
              accessibilityLabel="Regra ativa"
              value={ativa}
              onValueChange={setAtiva}
              disabled={ocupado}
            />
          </View>
        </>
      ) : (
        <>
          <Opcoes
            titulo="Dificuldade (1 = 10, 2 = 20, 3 = 30 pontos)"
            valores={pesosTarefa}
            valor={peso}
            selecionar={setPeso}
            ocupado={ocupado}
          />
          <Opcoes
            titulo="Prazo em dias"
            valores={prazosTarefa}
            valor={prazo}
            selecionar={setPrazo}
            ocupado={ocupado}
          />
          <Opcoes
            titulo="Atraso máximo em dias"
            valores={prazosTarefa}
            valor={atraso}
            selecionar={setAtraso}
            ocupado={ocupado}
          />
          <Opcoes
            titulo="Intervalo em semanas"
            valores={intervalosSemanasTarefa}
            valor={intervalo}
            selecionar={setIntervalo}
            ocupado={ocupado}
          />
          <Text style={styles.label}>Modo do prazo</Text>
          <View style={styles.row}>
            {(["intervalo", "dia_fixo"] as const).map((v) => (
              <Pressable
                key={v}
                accessibilityRole="radio"
                accessibilityState={{ checked: modo === v, disabled: ocupado }}
                disabled={ocupado}
                style={[
                  styles.button,
                  modo === v && { backgroundColor: "#fc5000" },
                ]}
                onPress={() => setModo(v)}
              >
                <Text style={styles.buttonText}>
                  {v === "intervalo"
                    ? "Dias após a ocorrência"
                    : "Dia da ocorrência"}
                </Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.label}>Dias da semana</Text>
          <View style={styles.row}>
            {diasSemanaTarefa.map((d) => (
              <Pressable
                key={d.valor}
                accessibilityRole="checkbox"
                accessibilityLabel={d.rotulo}
                accessibilityState={{
                  checked: dias.includes(d.valor),
                  disabled: ocupado,
                }}
                disabled={ocupado}
                style={[
                  styles.button,
                  dias.includes(d.valor) && { backgroundColor: "#fc5000" },
                ]}
                onPress={() =>
                  setDias((lista) =>
                    lista.includes(d.valor)
                      ? lista.filter((v) => v !== d.valor)
                      : [...lista, d.valor],
                  )
                }
              >
                <Text style={styles.buttonText}>{d.abreviacao}</Text>
              </Pressable>
            ))}
          </View>
          <Text style={styles.label}>Participantes — mínimo de dois</Text>
          <Text style={styles.text}>
            Ordem selecionada:{" "}
            {participantes
              .map((id) => moradores.find((m) => m.id === id)?.nome)
              .join(" → ") || "Nenhum"}
          </Text>
          {moradores.map((m) => (
            <Pressable
              key={m.id}
              accessibilityRole="checkbox"
              accessibilityLabel={`Participante ${m.nome}`}
              accessibilityState={{
                checked: participantes.includes(m.id),
                disabled: ocupado,
              }}
              disabled={ocupado}
              style={[
                styles.button,
                participantes.includes(m.id) && { backgroundColor: "#fc5000" },
              ]}
              onPress={() =>
                setParticipantes((lista) =>
                  lista.includes(m.id)
                    ? lista.filter((id) => id !== m.id)
                    : [...lista, m.id],
                )
              }
            >
              <Text style={styles.buttonText}>{m.nome}</Text>
            </Pressable>
          ))}
        </>
      )}
      {erro && (
        <Text accessibilityRole="alert" style={styles.error}>
          {erro}
        </Text>
      )}
      <View style={styles.row}>
        <Acao
          texto={ocupado ? "Salvando…" : "Salvar regra"}
          disabled={ocupado}
          onPress={enviar}
        />
        <Acao texto="Cancelar" disabled={ocupado} onPress={onCancelar} />
      </View>
    </View>
  );
}
