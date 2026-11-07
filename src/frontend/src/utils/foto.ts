export function uriFoto(foto: string): string | null {
  const tipo = foto.startsWith("/9j/")
    ? "image/jpeg"
    : foto.startsWith("iVBORw0KGgo")
      ? "image/png"
      : foto.startsWith("R0lGOD")
        ? "image/gif"
        : foto.startsWith("UklGR")
          ? "image/webp"
          : null;
  return tipo ? `data:${tipo};base64,${foto}` : null;
}

export const tiposFoto = ["image/jpeg", "image/png", "image/gif", "image/webp"];

export async function lerFotoSelecionada(
  tamanho: number,
  lerBase64: () => Promise<string>,
) {
  if (tamanho > 3 * 1024 * 1024) {
    throw new Error("Escolha uma imagem de até 3 MB.");
  }
  const foto = await lerBase64();
  if (!uriFoto(foto)) {
    throw new Error("Escolha uma imagem JPEG, PNG, GIF ou WebP.");
  }
  return foto;
}
