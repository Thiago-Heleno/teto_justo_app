import assert from "node:assert/strict";
import test from "node:test";
import { podeReportarTarefa } from "../src/utils/pode-reportar-tarefa.ts";

const conclusao = "2026-10-30T10:00:00-03:00";
const limite = Date.parse("2026-10-31T13:00:00Z");

for (const politica of ["uma_reclamacao", "votacao"]) {
  test(`morador pode reportar no limite exato de 24 horas com ${politica}`, () => {
    assert.equal(podeReportarTarefa(conclusao, politica, false, limite), true);
  });
}

test("oculta a denúncia imediatamente após o prazo", () => {
  assert.equal(
    podeReportarTarefa(conclusao, "votacao", false, limite + 1),
    false,
  );
});

test("oculta a denúncia quando a casa desativa reclamações", () => {
  assert.equal(podeReportarTarefa(conclusao, "nenhuma", false, limite), false);
});

test("o responsável não reporta a própria tarefa", () => {
  assert.equal(podeReportarTarefa(conclusao, "votacao", true, limite), false);
});
