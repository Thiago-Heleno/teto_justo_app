// eslint-disable-next-line import/no-unresolved
import { NativeTabs } from "expo-router/unstable-native-tabs";

import { Caldera } from "@/constants/theme";

export default function AppTabs() {
  return (
    <NativeTabs
      backgroundColor={Caldera.limestone}
      disableTransparentOnScrollEdge
      indicatorColor={Caldera.ember}
      labelStyle={{ selected: { color: Caldera.obsidian } }}
      tabBarRespectsIMEInsets
    >
      <NativeTabs.Trigger name="index">
        <NativeTabs.Trigger.Label>Início</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="house.fill" md="home" />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="nova-tarefa">
        <NativeTabs.Trigger.Label>Criar</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="plus.circle.fill" md="add_circle" />
      </NativeTabs.Trigger>

      <NativeTabs.Trigger name="tarefas">
        <NativeTabs.Trigger.Label>Tarefas</NativeTabs.Trigger.Label>
        <NativeTabs.Trigger.Icon sf="checklist" md="checklist" />
      </NativeTabs.Trigger>
    </NativeTabs>
  );
}
