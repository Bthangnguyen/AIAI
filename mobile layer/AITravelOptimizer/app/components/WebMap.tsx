import React from "react"
import { View, Text, StyleSheet } from "react-native"
import { colors } from "@/theme/colors"

// Dummy fallback for Native platforms (iOS/Android).
// On Native, we use MapboxGL.MapView directly in the screen.
export const WebMap = (props: any) => {
  return (
    <View style={[StyleSheet.absoluteFill, { backgroundColor: colors.palette.figmaOffWhite, justifyContent: "center", alignItems: "center" }]}>
      <Text style={{ color: colors.palette.figmaGrayDark }}>
        WebMap should not be rendered on Native.
      </Text>
    </View>
  )
}
