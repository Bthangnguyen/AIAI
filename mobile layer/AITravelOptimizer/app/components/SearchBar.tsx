/**
 * SearchBar — Figma "Front page" search input.
 * Rounded 25px, search icon left, gray border.
 */
import React from "react"
import { View, TextInput, StyleSheet, TouchableOpacity, ViewStyle } from "react-native"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

interface SearchBarProps {
  value: string
  onChangeText: (text: string) => void
  placeholder?: string
  onSubmit?: () => void
  style?: ViewStyle
  testID?: string
}

export const SearchBar: React.FC<SearchBarProps> = ({
  value,
  onChangeText,
  placeholder = "Search...",
  onSubmit,
  style,
  testID,
}) => {
  return (
    <View style={[styles.container, style]} testID={testID}>
      {/* Search Icon */}
      <View style={styles.iconContainer}>
        <View style={styles.searchIconCircle}>
          <View style={styles.searchIconLine} />
        </View>
      </View>
      <TextInput
        style={styles.input}
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder}
        placeholderTextColor={colors.palette.figmaGrayMedium}
        onSubmitEditing={onSubmit}
        returnKeyType="search"
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.palette.figmaWhite,
    borderRadius: 25,
    borderWidth: 1,
    borderColor: colors.palette.figmaGrayLight,
    paddingHorizontal: spacing.md,
    height: 50,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.06,
    shadowRadius: 4,
    elevation: 2,
  },
  iconContainer: {
    marginRight: spacing.xs,
    justifyContent: "center",
    alignItems: "center",
  },
  searchIconCircle: {
    width: 16,
    height: 16,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: colors.palette.figmaGrayMedium,
  },
  searchIconLine: {
    position: "absolute",
    bottom: -5,
    right: -3,
    width: 7,
    height: 2,
    backgroundColor: colors.palette.figmaGrayMedium,
    borderRadius: 1,
    transform: [{ rotate: "45deg" }],
  },
  input: {
    flex: 1,
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.figmaGrayDark,
    paddingVertical: 0,
  },
})
