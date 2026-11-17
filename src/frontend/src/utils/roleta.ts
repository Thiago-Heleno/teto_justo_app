export function anguloGiroRoleta(indiceSorteado: number, total: number) {
  if (total < 2 || indiceSorteado < 0 || indiceSorteado >= total) return;
  const centroDaFatia = (indiceSorteado * 360) / total;
  return 3 * 360 + ((360 - centroDaFatia) % 360);
}
