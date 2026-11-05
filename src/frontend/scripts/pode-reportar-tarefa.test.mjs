import assert from "node:assert/strict";
import test from "node:test";
import { podeReportarTarefa } from "../src/utils/pode-reportar-tarefa.ts";

const agora = Date.parse("2026-10-31T12:00:00.000Z");
const tarefaReportavel = {
  estado_atual: "finalizado",
  concluida_em: "2026-10-30T13:00:00.000Z",
  politica_reclamacao: "votacao",
  usuarios_atribuidos: ["responsavel"],
};

test("reportagem é permitida para morador e para o dono em até 24 horas", () => {
  assert.equal(podeReportarTarefa(tarefaReportavel, "morador", agora), true);
  assert.equal(podeReportarTarefa(tarefaReportavel, "dono", agora), true);
});

test("reportagem é permitida no limite exato de 24 horas", () => {
  assert.equal(
    podeReportarTarefa(
      tarefaReportavel,
      "morador",
      Date.parse("2026-10-31T13:00:00.000Z"),
    ),
    true,
  );
});

test("reportagem é ocultada fora da janela ou sem política", () => {
  assert.equal(
    podeReportarTarefa(
      tarefaReportavel,
      "morador",
      Date.parse("2026-10-31T13:00:00.001Z"),
    ),
    false,
  );
  assert.equal(
    podeReportarTarefa(
      { ...tarefaReportavel, politica_reclamacao: "nenhuma" },
      "morador",
      agora,
    ),
    false,
  );
});

test("o responsável não reporta a própria tarefa", () => {
  assert.equal(
    podeReportarTarefa(tarefaReportavel, "responsavel", agora),
    false,
  );
});
