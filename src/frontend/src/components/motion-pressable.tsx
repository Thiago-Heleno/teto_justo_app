import { forwardRef } from "react";
import {
  Pressable,
  type PressableProps,
  type StyleProp,
  type View,
  type ViewStyle,
} from "react-native";
import Animated, {
  ReduceMotion,
  type AnimatedStyle,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);
const timing = { duration: 120, reduceMotion: ReduceMotion.System } as const;

type MotionPressableProps = Omit<PressableProps, "style"> & {
  style?: StyleProp<AnimatedStyle<ViewStyle>>;
};

export const MotionPressable = forwardRef<View, MotionPressableProps>(
  function MotionPressable(
    {
      onBlur,
      onFocus,
      onHoverIn,
      onHoverOut,
      onPressIn,
      onPressOut,
      style,
      ...props
    },
    ref,
  ) {
    const hovered = useSharedValue(false);
    const focused = useSharedValue(false);
    const scale = useSharedValue(1);
    const animatedStyle = useAnimatedStyle(() => ({
      transform: [{ scale: scale.value }],
    }));

    function animate(value: number) {
      scale.set(withTiming(value, timing));
    }

    return (
      <AnimatedPressable
        {...props}
        ref={ref}
        onBlur={(event) => {
          focused.set(false);
          animate(hovered.get() ? 1.01 : 1);
          onBlur?.(event);
        }}
        onFocus={(event) => {
          focused.set(true);
          animate(1.01);
          onFocus?.(event);
        }}
        onHoverIn={(event) => {
          hovered.set(true);
          animate(1.01);
          onHoverIn?.(event);
        }}
        onHoverOut={(event) => {
          hovered.set(false);
          animate(focused.get() ? 1.01 : 1);
          onHoverOut?.(event);
        }}
        onPressIn={(event) => {
          animate(0.98);
          onPressIn?.(event);
        }}
        onPressOut={(event) => {
          animate(hovered.get() || focused.get() ? 1.01 : 1);
          onPressOut?.(event);
        }}
        style={[style, animatedStyle]}
      />
    );
  },
);
