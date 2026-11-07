import { File } from "expo-file-system";

import { lerFotoSelecionada, tiposFoto } from "./foto";

export async function selecionarFoto(): Promise<string | null> {
  const escolha = await File.pickFileAsync({ mimeTypes: tiposFoto });
  if (escolha.canceled) return null;
  const arquivo = escolha.result;
  return lerFotoSelecionada(arquivo.size, () => arquivo.base64());
}
