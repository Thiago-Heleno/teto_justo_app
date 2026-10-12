import assert from "node:assert/strict";
import test from "node:test";
import { podeReabrirTarefa } from "../src/utils/reabertura.ts";

const finalizada = { estado_atual: "finalizado", usuarios_atribuidos: ["ana"] };

test("reabertura é oferecida ao responsável e ao dono da casa", () => {
  assert.equal(podeReabrirTarefa(finalizada, "ana", "dono"), true);
  assert.equal(podeReabrirTarefa(finalizada, "dono", "dono"), true);
});

test("outros moradores e tarefas não finalizadas não veem a reabertura", () => {
  assert.equal(podeReabrirTarefa(finalizada, "bruno", "dono"), false);
  assert.equal(
    podeReabrirTarefa(
      { ...finalizada, estado_atual: "pendente" },
      "ana",
      "dono",
    ),
    false,
  );
});
