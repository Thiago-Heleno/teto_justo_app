import { lerFotoSelecionada, tiposFoto } from "./foto";

export async function selecionarFoto(): Promise<string | null> {
  const arquivo = await new Promise<File | null>((resolve) => {
    const campo = document.createElement("input");
    campo.type = "file";
    campo.accept = tiposFoto.join(",");
    campo.onchange = () => resolve(campo.files?.[0] ?? null);
    campo.oncancel = () => resolve(null);
    campo.click();
  });
  if (!arquivo) return null;
  return lerFotoSelecionada(
    arquivo.size,
    () =>
      new Promise<string>((resolve, reject) => {
        const leitor = new FileReader();
        leitor.onload = () =>
          resolve(String(leitor.result).split(",")[1] ?? "");
        leitor.onerror = () =>
          reject(new Error("Não foi possível ler a imagem."));
        leitor.readAsDataURL(arquivo);
      }),
  );
}
