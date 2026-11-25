import { Link, type Href } from "expo-router";
import { ArrowLeft } from "lucide-react-native";
import { StyleSheet, Text } from "react-native";

import { MotionPressable } from "@/components/motion-pressable";
import { Caldera, Spacing } from "@/constants/theme";

type BotaoVoltarProps = {
  texto?: string;
  href?: Href;
  onPress?: () => void;
};

export function BotaoVoltar({
  texto = "Voltar ao início",
  href = "/",
  onPress,
}: BotaoVoltarProps) {
  const conteudo = (
    <>
      <ArrowLeft color={Caldera.obsidian} size={18} />
      <Text style={styles.text}>{texto}</Text>
    </>
  );

  if (onPress) {
    return (
      <MotionPressable
        accessibilityRole="button"
        onPress={onPress}
        style={styles.link}
      >
        {conteudo}
      </MotionPressable>
    );
  }

  return (
    <Link href={href} asChild>
      <MotionPressable accessibilityRole="button" style={styles.link}>
        {conteudo}
      </MotionPressable>
    </Link>
  );
}

const styles = StyleSheet.create({
  link: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    gap: Spacing.two,
    paddingVertical: Spacing.two,
  },
  text: {
    color: Caldera.obsidian,
    fontSize: 16,
    fontWeight: "500",
  },
});
