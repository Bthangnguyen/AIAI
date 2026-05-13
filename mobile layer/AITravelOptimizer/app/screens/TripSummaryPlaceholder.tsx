/**
 * TripSummaryPlaceholder — Wallet tab placeholder.
 * Shows active trip or empty state prompting user to plan.
 */
import React from "react"
import { View, Text, StyleSheet, SafeAreaView } from "react-native"
import { useNavigation } from "@react-navigation/native"
import type { NativeStackNavigationProp } from "@react-navigation/native-stack"

import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { CTAButton } from "@/components/CTAButton"
import { AppStackParamList } from "@/navigators/navigationTypes"

type Nav = NativeStackNavigationProp<AppStackParamList>

export const TripSummaryPlaceholder: React.FC = () => {
  const navigation = useNavigation<Nav>()

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.container}>
        <Text style={styles.emoji}>🗺️</Text>
        <Text style={styles.title}>No Active Trip</Text>
        <Text style={styles.subtitle}>
          Plan your next adventure and it will appear here with your full itinerary.
        </Text>
        <CTAButton
          label="Plan a Trip"
          onPress={() => navigation.navigate("ItineraryForm")}
          style={styles.cta}
        />
      </View>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.palette.figmaWhite },
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: spacing.xxl,
  },
  emoji: { fontSize: 64, marginBottom: spacing.lg },
  title: {
    fontFamily: typography.primary.bold,
    fontSize: 22,
    color: colors.palette.figmaBlack,
    marginBottom: spacing.sm,
    textAlign: "center",
  },
  subtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.figmaGrayMedium,
    textAlign: "center",
    lineHeight: 22,
    marginBottom: spacing.xl,
  },
  cta: { width: "100%" },
})
