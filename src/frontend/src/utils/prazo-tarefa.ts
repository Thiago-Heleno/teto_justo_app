import type { PesoTarefa } from "@/constants/tarefa";

export type TarefaDemonstracao = {
  nome: string;
  descricao: string;
  peso: PesoTarefa;
  data_fim: string;
  usuarios_atribuidos: string[];
};

type ResultadoPrazo =
  | { data_fim: string; erroData?: never; erroHorario?: never }
  | { data_fim?: never; erroData?: string; erroHorario?: string };

export function validarPrazo(
  data: string,
  horario: string,
  agora = new Date(),
): ResultadoPrazo {
  if (!/^\d{2}\/\d{2}\/\d{4}$/.test(data)) {
    return { erroData: "Informe uma data no formato DD/MM/AAAA." };
  }

  const [dia, mes, ano] = data.split("/").map(Number);
  const calendario = new Date(0);
  calendario.setFullYear(ano, mes - 1, dia);
  calendario.setHours(12, 0, 0, 0);

  if (
    ano < 1 ||
    calendario.getFullYear() !== ano ||
    calendario.getMonth() !== mes - 1 ||
    calendario.getDate() !== dia
  ) {
    return { erroData: "Informe uma data que exista no calendário." };
  }

  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(horario)) {
    return { erroHorario: "Informe um horário válido entre 00:00 e 23:59." };
  }

  const [hora, minuto] = horario.split(":").map(Number);
  calendario.setHours(hora, minuto, 0, 0);

  if (calendario.getHours() !== hora || calendario.getMinutes() !== minuto) {
    return { erroHorario: "Esse horário não existe no fuso do dispositivo." };
  }

  if (calendario.getTime() <= agora.getTime()) {
    return { erroHorario: "Escolha uma data e um horário futuros." };
  }

  return { data_fim: calendario.toISOString() };
}
