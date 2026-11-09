export function formatarDataDigitada(valor: string) {
  const entrada = valor.trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(entrada)) {
    const [ano, mes, dia] = entrada.split("-");
    return [dia, mes, ano].join("-");
  }

  const digitos = entrada.replace(/\D/g, "").slice(0, 8);
  return [digitos.slice(0, 2), digitos.slice(2, 4), digitos.slice(4)]
    .filter(Boolean)
    .join("-");
}

export function dataFixaParaIso(valor: string) {
  if (!/^\d{2}-\d{2}-\d{4}$/.test(valor)) return undefined;
  const [dia, mes, ano] = valor.split("-");
  if (ano === "0000") return undefined;

  const iso = [ano, mes, dia].join("-");
  const data = new Date(iso + "T00:00:00Z");
  if (
    !Number.isNaN(data.getTime()) &&
    data.toISOString().slice(0, 10) === iso
  ) {
    return iso;
  }
}
