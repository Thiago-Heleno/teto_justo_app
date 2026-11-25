export function anguloGiroRoleta(indiceSorteado: number, total: number) {
  if (total < 2 || indiceSorteado < 0 || indiceSorteado >= total) return;
  const centroDaFatia = (indiceSorteado * 360) / total;
  return 3 * 360 + ((360 - centroDaFatia) % 360);
}
export function rotulosRoleta(nomes: readonly string[]) {
  const rotulos = nomes.map((nome) => {
    const completo = nome.trim().replace(/\s+/g, " ");
    return { completo, primeiro: completo.split(" ")[0] };
  });
  const frequencias = new Map<string, number>();
  for (const { primeiro } of rotulos) {
    const chave = primeiro.toLocaleLowerCase("pt-BR");
    frequencias.set(chave, (frequencias.get(chave) ?? 0) + 1);
  }
  return rotulos.map(({ primeiro, completo }) => ({
    primeiro,
    legenda:
      (frequencias.get(primeiro.toLocaleLowerCase("pt-BR")) ?? 0) > 1
        ? completo
        : primeiro,
  }));
}
