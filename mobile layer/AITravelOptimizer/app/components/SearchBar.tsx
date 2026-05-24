/**
 * SearchBar - Dark Glassmorphism Design
 */
import React from "react"
import { View, TextInput, StyleSheet, TouchableOpacity, ViewStyle, Text } from "react-native"
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
  value, onChangeText, placeholder = "Tìm kiếm địa điểm...",
  onSubmit, style, testID,
}) => (
  <View style={[styles.container, style]} testID={testID}>
    <Text style={styles.searchIcon}>🔍</Text>
    <TextInput
      style={styles.input}
      value={value}
      onChangeText={onChangeText}
      placeholder={placeholder}
      placeholderTextColor="rgba(255,255,255,0.3)"
      onSubmitEditing={onSubmit}
      returnKeyType="search"
    />
    {value.length > 0 && (
      <TouchableOpacity onPress={() => onChangeText("")} style={styles.clearBtn}>
        <Text style={styles.clearIcon}>✕</Text>
      </TouchableOpacity>
    )}
  </View>
)

const styles = StyleSheet.create({
  container: {
    flexDirection: "row", alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.08)",
    borderRadius: 16, borderWidth: 1, borderColor: "rgba(255,255,255,0.15)",
    paddingHorizontal: spacing.md, height: 50,
  },
  searchIcon: { fontSize: 16, marginRight: spacing.sm },
  input: {
    flex: 1, fontFamily: typography.primary.normal,
    fontSize: 14, color: "#FFFFFF",
    paddingVertical: 0,
  },
  clearBtn: { paddingLeft: spacing.sm },
  clearIcon: { fontSize: 14, color: "rgba(255,255,255,0.4)" },
})