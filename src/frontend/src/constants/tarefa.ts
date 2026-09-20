export const pesosTarefa = [1, 2, 3] as const;

export type PesoTarefa = (typeof pesosTarefa)[number];
