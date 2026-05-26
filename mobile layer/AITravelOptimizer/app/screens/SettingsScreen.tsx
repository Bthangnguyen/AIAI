/**
 * SettingsScreen — App settings: notifications, API URL (dev), logout.
 */
import React, { useState } from "react"
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  Switch,
  TouchableOpacity,
  StatusBar,
  TextInput,
} from "react-native"
import { useNavigation } from "@react-navigation/native"
import { useAuth } from "@/context/AuthContext"

import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { CTAButton } from "@/components/CTAButton"

export const SettingsScreen: React.FC = () => {
  const navigation = useNavigation()
  const { logout } = useAuth()
  const [notifications, setNotifications] = useState(true)
  const [emailAlerts, setEmailAlerts] = useState(false)
  const [apiUrl, setApiUrl] = useState(process.env.EXPO_PUBLIC_API_URL || "http://10.0.2.2:8001")

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.palette.figmaWhite} />
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backArrow}>←</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Settings</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        {/* ─── Notifications ── */}
        <Text style={styles.sectionTitle}>Notifications</Text>
        <View style={styles.section}>
          <View style={styles.settingRow}>
            <Text style={styles.settingLabel}>Push notifications</Text>
            <Switch
              value={notifications}
              onValueChange={setNotifications}
              trackColor={{ false: colors.palette.figmaGrayLight, true: colors.palette.figmaBlue }}
              thumbColor={colors.palette.figmaWhite}
            />
          </View>
          <View style={[styles.settingRow, styles.noBorder]}>
            <Text style={styles.settingLabel}>Email alerts</Text>
            <Switch
              value={emailAlerts}
              onValueChange={setEmailAlerts}
              trackColor={{ false: colors.palette.figmaGrayLight, true: colors.palette.figmaBlue }}
              thumbColor={colors.palette.figmaWhite}
            />
          </View>
        </View>

        {/* ─── Developer ── */}
        <Text style={styles.sectionTitle}>Developer</Text>
        <View style={styles.section}>
          <Text style={styles.settingLabel}>API Gateway URL</Text>
          <TextInput
            style={styles.apiInput}
            value={apiUrl}
            onChangeText={setApiUrl}
            placeholder="http://10.0.2.2:8001"
            placeholderTextColor={colors.palette.figmaGrayMedium}
            autoCapitalize="none"
          />
        </View>

        {/* ─── Logout ── */}
        <CTAButton
          label="Log out"
          onPress={logout}
          variant="outline"
          style={styles.logoutBtn}
          testID="logout-btn"
        />

        <Text style={styles.version}>AI Travel Optimizer v1.0.0-beta</Text>

        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.palette.figmaWhite },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
  },
  backBtn: { width: 40, height: 40, justifyContent: "center" },
  backArrow: { fontSize: 22, color: colors.palette.figmaBlack },
  title: {
    fontFamily: typography.primary.bold,
    fontSize: 20,
    color: colors.palette.figmaBlack,
  },
  content: { paddingHorizontal: spacing.lg, paddingTop: spacing.md },
  sectionTitle: {
    fontFamily: typography.primary.semiBold,
    fontSize: 13,
    color: colors.palette.figmaGrayMedium,
    textTransform: "uppercase",
    letterSpacing: 0.8,
    marginBottom: spacing.xs,
    marginTop: spacing.md,
  },
  section: {
    backgroundColor: colors.palette.figmaOffWhite,
    borderRadius: 15,
    overflow: "hidden",
    marginBottom: spacing.sm,
  },
  settingRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: colors.palette.figmaGrayLight,
  },
  noBorder: { borderBottomWidth: 0 },
  settingLabel: {
    fontFamily: typography.primary.medium,
    fontSize: 15,
    color: colors.palette.figmaGrayDark,
  },
  apiInput: {
    backgroundColor: colors.palette.figmaOffWhite,
    borderRadius: 10,
    padding: spacing.md,
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: colors.palette.figmaGrayDark,
  },
  logoutBtn: { marginTop: spacing.xl },
  version: {
    fontFamily: typography.primary.normal,
    fontSize: 12,
    color: colors.palette.figmaGrayMedium,
    textAlign: "center",
    marginTop: spacing.md,
  },
})
