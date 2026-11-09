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
import { View, StyleSheet } from "react-native";

import { ThemedText } from "./themed-text";
import { ThemedView } from "./themed-view";

import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, Spacing } from "@/constants/theme";

export default function AppTabs() {
  return (
    <Tabs>
      <TabSlot style={{ height: "100%" }} />
      <TabList asChild>
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
        </CustomTabList>
      </TabList>
    </Tabs>
  );
}

export function TabButton({
  children,
  icon: Icon,
  isFocused,
  ...props
}: TabTriggerSlotProps & { icon: LucideIcon }) {
  return (
    <MotionPressable {...props} style={undefined}>
      <ThemedView
        style={[
          styles.tabButtonView,
          isFocused && styles.tabButtonViewSelected,
        ]}
      >
        <Icon color={Caldera.obsidian} size={16} />
        <ThemedText type="small" style={styles.tabButtonText}>
          {children}
        </ThemedText>
      </ThemedView>
    </MotionPressable>
  );
}

export function CustomTabList(props: TabListProps) {
  return (
    <View {...props} style={styles.tabListContainer}>
      <ThemedView style={styles.innerContainer}>{props.children}</ThemedView>
    </View>
  );
}

const styles = StyleSheet.create({
  tabListContainer: {
    position: "absolute",
    width: "100%",
    padding: Spacing.three,
    justifyContent: "center",
    alignItems: "center",
    flexDirection: "row",
  },
  innerContainer: {
    backgroundColor: Caldera.limestone,
    paddingVertical: Spacing.two,
    paddingHorizontal: Spacing.four,
    borderRadius: 800,
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
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
  tabButtonViewSelected: { backgroundColor: Caldera.ember },
  tabButtonText: { color: Caldera.obsidian },
});
