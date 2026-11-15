import {
  Tabs,
  TabList,
  TabTrigger,
  TabSlot,
  TabTriggerSlotProps,
  TabListProps,
} from "expo-router/ui";
import {
  CirclePlus,
  House,
  ListChecks,
  Trophy,
  User,
  type LucideIcon,
} from "lucide-react-native";
import { createContext, useContext } from "react";
import { StyleSheet, useWindowDimensions, View } from "react-native";

import { ThemedText } from "./themed-text";
import { ThemedView } from "./themed-view";

import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, Spacing } from "@/constants/theme";

const CompactoContext = createContext(false);

export default function AppTabs() {
  const { width } = useWindowDimensions();
  const compacto = width < 600;

  return (
    <CompactoContext.Provider value={compacto}>
      <Tabs>
        <TabList asChild nativeID="navegacao-da-casa">
          <CustomTabList>
            <TabTrigger name="index" href="/" asChild>
              <TabButton icon={House}>Home</TabButton>
            </TabTrigger>
            <TabTrigger name="nova-tarefa" href="/nova-tarefa" asChild>
              <TabButton icon={CirclePlus}>Criar</TabButton>
            </TabTrigger>
            <TabTrigger name="tarefas" href="/tarefas" asChild>
              <TabButton icon={ListChecks}>Tarefas</TabButton>
            </TabTrigger>
            <TabTrigger name="pontuacao" href="/pontuacao" asChild>
              <TabButton icon={Trophy}>Pontuação</TabButton>
            </TabTrigger>
            <TabTrigger name="perfil" href="/perfil" asChild>
              <TabButton icon={User}>Perfil</TabButton>
            </TabTrigger>
            <TabTrigger
              name="gerenciar-casa"
              href="/gerenciar-casa"
              style={styles.hiddenTrigger}
            />
            <TabTrigger
              name="rotatividades"
              href="/rotatividades"
              style={styles.hiddenTrigger}
            />
          </CustomTabList>
        </TabList>
        <TabSlot style={styles.tabContent} />
      </Tabs>
    </CompactoContext.Provider>
  );
}

export function TabButton({
  children,
  icon: Icon,
  isFocused,
  ...props
}: TabTriggerSlotProps & { icon: LucideIcon }) {
  const compacto = useContext(CompactoContext);
  return (
    <MotionPressable
      {...props}
      accessibilityLabel={compacto ? String(children) : undefined}
      style={compacto ? styles.pressableCompacto : undefined}
    >
      <ThemedView
        style={[
          styles.tabButtonView,
          compacto && styles.tabButtonViewCompacto,
          isFocused && styles.tabButtonViewSelected,
        ]}
      >
        <Icon color={Caldera.obsidian} size={16} />
        {!compacto && (
          <ThemedText type="small" style={styles.tabButtonText}>
            {children}
          </ThemedText>
        )}
      </ThemedView>
    </MotionPressable>
  );
}

export function CustomTabList({ style, children, ...props }: TabListProps) {
  return (
    <View {...props} style={[styles.tabListContainer, style]}>
      <ThemedView style={styles.innerContainer}>{children}</ThemedView>
    </View>
  );
}

const styles = StyleSheet.create({
  tabContent: { flex: 1, minHeight: 0 },
  hiddenTrigger: { display: "none" },
  tabListContainer: {
    width: "100%",
    padding: Spacing.three,
    justifyContent: "center",
    alignItems: "center",
    flexDirection: "row",
    backgroundColor: Caldera.limestone,
  },
  innerContainer: {
    backgroundColor: Caldera.limestone,
    paddingVertical: Spacing.two,
    paddingHorizontal: Spacing.four,
    borderRadius: 800,
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "nowrap",
    width: "100%",
    gap: Spacing.two,
    maxWidth: 1280,
  },
  tabButtonView: {
    alignItems: "center",
    flexDirection: "row",
    gap: Spacing.one,
    backgroundColor: Caldera.limestone,
    paddingVertical: Spacing.one,
    paddingHorizontal: Spacing.three,
    borderRadius: 800,
  },
  tabButtonViewCompacto: {
    flex: 1,
    justifyContent: "center",
    paddingHorizontal: Spacing.two,
  },
  pressableCompacto: { flex: 1 },
  tabButtonViewSelected: { backgroundColor: Caldera.ember },
  tabButtonText: { color: Caldera.obsidian },
});
