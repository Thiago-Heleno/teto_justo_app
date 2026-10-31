import assert from "node:assert/strict";
import test from "node:test";
import { podeReportarTarefa } from "../src/utils/pode-reportar-tarefa.ts";

const agora = Date.parse("2026-10-31T12:00:00.000Z");
const tarefaReportavel = {
  estado_atual: "finalizado",
  concluida_em: "2026-10-30T13:00:00.000Z",
  politica_reclamacao: "votacao",
};

test("reportagem é permitida para morador em até 24 horas", () => {
  assert.equal(
    podeReportarTarefa(tarefaReportavel, "morador", "dono", agora),
    true,
  );
});

test("reportagem é ocultada fora da janela, sem política ou pelo dono", () => {
  assert.equal(
    podeReportarTarefa(
      tarefaReportavel,
      "morador",
      "dono",
      Date.parse("2026-10-31T13:00:01.000Z"),
    ),
    false,
  );
  assert.equal(
    podeReportarTarefa(
      { ...tarefaReportavel, politica_reclamacao: "nenhuma" },
      "morador",
      "dono",
      agora,
    ),
    false,
  );
  assert.equal(
    podeReportarTarefa(tarefaReportavel, "dono", "dono", agora),
    false,
  );
});
