import assert from "node:assert/strict";
import test from "node:test";

import { lerFotoSelecionada, uriFoto } from "../src/utils/foto.ts";

test("uriFoto identifica prefixos JPEG, PNG, GIF e WebP e rejeita outros", () => {
  assert.equal(uriFoto("/9j/abc"), "data:image/jpeg;base64,/9j/abc");
  assert.equal(
    uriFoto("iVBORw0KGgoAAA"),
    "data:image/png;base64,iVBORw0KGgoAAA",
  );
  assert.equal(uriFoto("R0lGODlh"), "data:image/gif;base64,R0lGODlh");
  assert.equal(uriFoto("UklGRg=="), "data:image/webp;base64,UklGRg==");
  assert.equal(uriFoto("invalido"), null);
  assert.equal(uriFoto(""), null);
});

test("lerFotoSelecionada rejeita arquivo acima de 3 MB antes de ler base64", async () => {
  let leu = false;
  await assert.rejects(
    lerFotoSelecionada(3 * 1024 * 1024 + 1, async () => {
      leu = true;
      return "iVBORw0KGgoAAA";
    }),
    /até 3 MB/,
  );
  assert.equal(leu, false);
});

test("lerFotoSelecionada rejeita formato não suportado e aceita imagem válida no limite", async () => {
  await assert.rejects(
    lerFotoSelecionada(1024, async () => "conteudo-texto"),
    /JPEG, PNG, GIF ou WebP/,
  );

  const foto = await lerFotoSelecionada(
    3 * 1024 * 1024,
    async () => "iVBORw0KGgoAAA",
  );
  assert.equal(foto, "iVBORw0KGgoAAA");
});
