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
