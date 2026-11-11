import { useRef, useState } from "react";
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
  Menu,
  Trophy,
  User,
  X,
  type LucideIcon,
} from "lucide-react-native";
import { StyleSheet, useWindowDimensions, View } from "react-native";

import { ThemedText } from "./themed-text";
import { ThemedView } from "./themed-view";

import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, Spacing } from "@/constants/theme";

export default function AppTabs() {
  const { width } = useWindowDimensions();
  const compacto = width < 600;
  const [menuAberto, setMenuAberto] = useState(false);
  const botaoMenu = useRef<View>(null);
  const IconeMenu = menuAberto ? X : Menu;

  function recolherMenu() {
    setMenuAberto(false);
    if (compacto) botaoMenu.current?.focus();
  }

  return (
    <Tabs>
      {compacto && (
        <View style={styles.menuHeader}>
          <MotionPressable
            ref={botaoMenu}
            accessibilityRole="button"
            accessibilityLabel={menuAberto ? "Fechar menu" : "Abrir menu"}
            aria-controls="navegacao-da-casa"
            aria-expanded={menuAberto}
            onPress={() => setMenuAberto((aberto) => !aberto)}
            style={styles.menuButton}
          >
            <IconeMenu color={Caldera.obsidian} size={24} />
          </MotionPressable>
        </View>
      )}
      <TabList
        asChild
        nativeID="navegacao-da-casa"
        style={compacto && !menuAberto && styles.hidden}
      >
        <CustomTabList>
          <TabTrigger name="index" href="/" asChild onPress={recolherMenu}>
            <TabButton icon={House}>Home</TabButton>
          </TabTrigger>
          <TabTrigger
            name="nova-tarefa"
            href="/nova-tarefa"
            asChild
            onPress={recolherMenu}
          >
            <TabButton icon={CirclePlus}>Criar</TabButton>
          </TabTrigger>
          <TabTrigger
            name="tarefas"
            href="/tarefas"
            asChild
            onPress={recolherMenu}
          >
            <TabButton icon={ListChecks}>Tarefas</TabButton>
          </TabTrigger>
          <TabTrigger
            name="pontuacao"
            href="/pontuacao"
            asChild
            onPress={recolherMenu}
          >
            <TabButton icon={Trophy}>Pontuação</TabButton>
          </TabTrigger>
          <TabTrigger
            name="perfil"
            href="/perfil"
            asChild
            onPress={recolherMenu}
          >
            <TabButton icon={User}>Perfil</TabButton>
          </TabTrigger>
        </CustomTabList>
      </TabList>
      <TabSlot style={styles.tabContent} />
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

export function CustomTabList({ style, children, ...props }: TabListProps) {
  return (
    <View {...props} style={[styles.tabListContainer, style]}>
      <ThemedView style={styles.innerContainer}>{children}</ThemedView>
    </View>
  );
}

const styles = StyleSheet.create({
  menuHeader: {
    backgroundColor: Caldera.limestone,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  menuButton: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: Caldera.pumice,
  },
  hidden: { display: "none" },
  tabContent: { flex: 1, minHeight: 0 },
  tabListContainer: {
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
