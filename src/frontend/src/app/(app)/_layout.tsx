import { useStore } from "zustand";

import AppTabs from "@/components/app-tabs";
import { sessao } from "@/services/sessao-store";

export default function LayoutCasa() {
  const casaId = useStore(sessao, (estado) => estado.casaAtiva?.id);
  return <AppTabs key={casaId} />;
}
