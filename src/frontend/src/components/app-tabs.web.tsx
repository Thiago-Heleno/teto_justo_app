import {
  Tabs,
  TabList,
  TabTrigger,
  TabSlot,
  TabTriggerSlotProps,
  TabListProps,
} from "expo-router/ui";
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
            <TabButton>Home</TabButton>
          </TabTrigger>
          <TabTrigger name="nova-tarefa" href="/nova-tarefa" asChild>
            <TabButton>Criar</TabButton>
          </TabTrigger>
          <TabTrigger name="tarefas" href="/tarefas" asChild>
            <TabButton>Tarefas</TabButton>
          </TabTrigger>
          <TabTrigger name="pontuacao" href="/pontuacao" asChild>
            <TabButton>Pontuação</TabButton>
          </TabTrigger>
        </CustomTabList>
      </TabList>
    </Tabs>
  );
}

export function TabButton({
  children,
  isFocused,
  ...props
}: TabTriggerSlotProps) {
  return (
    <MotionPressable {...props} style={undefined}>
      <ThemedView
        style={[
          styles.tabButtonView,
          isFocused && styles.tabButtonViewSelected,
        ]}
      >
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
      <ThemedView style={styles.innerContainer}>
        <ThemedText type="smallBold" style={styles.brandText}>
          TETO JUSTO
        </ThemedText>

        {props.children}
      </ThemedView>
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
  brandText: {
    marginRight: "auto",
    color: Caldera.obsidian,
    fontWeight: "500",
  },
  tabButtonView: {
    backgroundColor: Caldera.limestone,
    paddingVertical: Spacing.one,
    paddingHorizontal: Spacing.three,
    borderRadius: 800,
  },
  tabButtonViewSelected: { backgroundColor: Caldera.ember },
  tabButtonText: { color: Caldera.obsidian },
});
