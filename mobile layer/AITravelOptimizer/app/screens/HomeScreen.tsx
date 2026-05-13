import { FC, useState } from "react"
import { View, ViewStyle, TextStyle, ImageBackground, StyleSheet, Pressable } from "react-native"
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  FadeIn,
} from "react-native-reanimated"

import { Screen } from "@/components/Screen"
import { Text } from "@/components/Text"
import { TextField } from "@/components/TextField"
import type { AppStackScreenProps } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

// HomeScreen is now legacy — main home is ExploreScreen via MainTabNavigator
// Kept as backup glassmorphism entry point accessible from settings
interface HomeScreenProps extends AppStackScreenProps<"MainTabs"> {}


const BACKGROUND_URL =
  "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?q=80&w=2021&auto=format&fit=crop"

export const HomeScreen: FC<HomeScreenProps> = ({ navigation }) => {
  const [prompt, setPrompt] = useState("")
  const [hotelName, setHotelName] = useState("Da Lat Palace")
  const [numDays, setNumDays] = useState("3")

  // Button Animation
  const scale = useSharedValue(1)
  const animatedButtonStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
  }))

  const onPressIn = () => {
    scale.value = withSpring(0.95, { damping: 10, stiffness: 400 })
  }
  const onPressOut = () => {
    scale.value = withSpring(1, { damping: 10, stiffness: 400 })
  }

  const handleOptimize = () => {
    if (!prompt.trim()) return
    navigation.navigate("Loading", {
      prompt,
      hotelName,
      hotelLat: 11.9404,
      hotelLon: 108.4384,
      numDays: parseInt(numDays, 10) || 3,
    })
  }

  return (
    <Screen style={$root} preset="scroll" contentContainerStyle={$contentContainer}>
      <ImageBackground source={{ uri: BACKGROUND_URL }} style={$background} blurRadius={8}>
        <View style={$overlay} />

        {/* Hero Header */}
        <Animated.View entering={FadeIn.duration(800)} style={$header}>
          <Text text="Where do you want" style={$title} />
          <Text text="to explore?" style={$titleHighlight} />
          <Text text="AI-powered travel planning at your fingertips" style={$heroSub} />
        </Animated.View>

        {/* Glass Input Card */}
        <Animated.View entering={FadeIn.delay(300).duration(600)} style={$glassCard}>
          <TextField
            value={prompt}
            onChangeText={setPrompt}
            containerStyle={$inputContainer}
            style={$promptInput}
            placeholder="e.g. A romantic 3-day trip to Da Lat with local food..."
            placeholderTextColor={colors.palette.figmaPlaceholder}
            multiline
          />

          <View style={$row}>
            <TextField
              value={hotelName}
              onChangeText={setHotelName}
              containerStyle={[$inputContainer, { flex: 2, marginRight: spacing.sm }]}
              style={$smallInput}
              label="Starting Point"
              placeholder="Hotel name..."
              placeholderTextColor={colors.palette.figmaPlaceholder}
            />
            <TextField
              value={numDays}
              onChangeText={setNumDays}
              keyboardType="number-pad"
              containerStyle={[$inputContainer, { flex: 1 }]}
              style={$smallInput}
              label="Days"
              placeholder="3"
              placeholderTextColor={colors.palette.figmaPlaceholder}
            />
          </View>

          <Pressable onPressIn={onPressIn} onPressOut={onPressOut} onPress={handleOptimize}>
            <Animated.View style={[$button, animatedButtonStyle]}>
              <Text text="✨ Plan My Trip" style={$buttonText} />
            </Animated.View>
          </Pressable>
        </Animated.View>

        {/* Bottom tagline */}
        <Animated.View entering={FadeIn.delay(600).duration(600)} style={$footer}>
          <Text text="Powered by AI + OR-Tools Routing Engine" style={$footerText} />
        </Animated.View>
      </ImageBackground>
    </Screen>
  )
}

// ─── Styles ─────────────────────────────────────────────────────

const $root: ViewStyle = {
  flex: 1,
}

const $contentContainer: ViewStyle = {
  flexGrow: 1,
}

const $background: ViewStyle = {
  flex: 1,
  justifyContent: "center",
  paddingHorizontal: spacing.lg,
}

const $overlay: ViewStyle = {
  ...StyleSheet.absoluteFillObject,
  backgroundColor: "rgba(0, 0, 0, 0.45)",
}

const $header: ViewStyle = {
  marginBottom: spacing.xxl,
  marginTop: spacing.xxxl,
}

const $title: TextStyle = {
  fontSize: 42,
  fontFamily: typography.primary.bold,
  color: "#FFFFFF",
  lineHeight: 48,
}

const $titleHighlight: TextStyle = {
  fontSize: 42,
  fontFamily: typography.primary.bold,
  color: colors.tint,
  lineHeight: 48,
}

const $heroSub: TextStyle = {
  fontSize: 16,
  fontFamily: typography.primary.normal,
  color: "rgba(255, 255, 255, 0.7)",
  marginTop: spacing.sm,
  lineHeight: 24,
}

const $glassCard: ViewStyle = {
  backgroundColor: colors.palette.glassWhite10,
  borderRadius: 24,
  padding: spacing.lg,
  borderWidth: 1,
  borderColor: "rgba(255, 255, 255, 0.2)",
  // Subtle blur effect fallback
  shadowColor: "#000",
  shadowOffset: { width: 0, height: 8 },
  shadowOpacity: 0.15,
  shadowRadius: 24,
  elevation: 8,
}

const $inputContainer: ViewStyle = {
  marginBottom: spacing.md,
}

const $promptInput: TextStyle = {
  fontSize: 18,
  minHeight: 100,
  color: "#FFFFFF",
  textAlignVertical: "top",
  fontFamily: typography.primary.normal,
}

const $smallInput: TextStyle = {
  fontSize: 16,
  color: "#FFFFFF",
  fontFamily: typography.primary.normal,
}



const $row: ViewStyle = {
  flexDirection: "row",
  justifyContent: "space-between",
  marginBottom: spacing.lg,
}

const $button: ViewStyle = {
  backgroundColor: colors.tint,
  borderRadius: 38, // Figma pill shape (76/2)
  paddingVertical: 16,
  alignItems: "center",
  justifyContent: "center",
  shadowColor: colors.tint,
  shadowOffset: { width: 0, height: 4 },
  shadowOpacity: 0.3,
  shadowRadius: 12,
  elevation: 6,
}

const $buttonText: TextStyle = {
  color: "#FFFFFF",
  fontFamily: typography.primary.semiBold,
  fontSize: 18,
}

const $footer: ViewStyle = {
  alignItems: "center",
  marginTop: spacing.xxl,
  marginBottom: spacing.lg,
}

const $footerText: TextStyle = {
  fontSize: 12,
  fontFamily: typography.primary.normal,
  color: "rgba(255, 255, 255, 0.5)",
}
