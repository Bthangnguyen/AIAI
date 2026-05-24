/**
 * SettingsScreen - Dark Royal Hue Design
 * App settings with grouped glass cards
 */
import React, { useState } from "react"
import {
  View, StyleSheet, ScrollView, Switch, TouchableOpacity,
  StatusBar, TextInput, Alert,
} from "react-native"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { useNavigation } from "@react-navigation/native"
import { Text } from "@/components/Text"
import { useAuth } from "@/context/AuthContext"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

interface SettingToggle {
  key: string
  icon: string
  label: string
  description: string
  value: boolean
  setter: (v: boolean) => void
}

export const SettingsScreen: React.FC = () => {
  const navigation = useNavigation()
  const { logout } = useAuth()
  const insets = useSafeAreaInsets()

  const [notifications, setNotifications] = useState(true)
  const [heatWarning, setHeatWarning] = useState(true)
  const [audioGuide, setAudioGuide] = useState(true)
  const [autoReroute, setAutoReroute] = useState(false)
  const [emailAlerts, setEmailAlerts] = useState(false)
  const [darkMap, setDarkMap] = useState(true)
  const [apiUrl, setApiUrl] = useState("http://localhost:8001")
  const [apiInputFocused, setApiInputFocused] = useState(false)

  const NOTIFICATION_SETTINGS: SettingToggle[] = [
    { key: "notif", icon: "🔔", label: "Thông báo push", description: "Nhận cảnh báo và gợi ý trong chuyến đi", value: notifications, setter: setNotifications },
    { key: "heat", icon: "☀️", label: "Cảnh báo nắng nóng", description: "Thông báo khi lịch trình vào khung 12h-14h", value: heatWarning, setter: setHeatWarning },
    { key: "email", icon: "📧", label: "Email tóm tắt", description: "Nhận email tóm tắt sau mỗi chuyến đi", value: emailAlerts, setter: setEmailAlerts },
  ]

  const TRIP_SETTINGS: SettingToggle[] = [
    { key: "audio", icon: "🎧", label: "Audio Guide tự động", description: "Phát thuyết minh khi đến điểm tham quan", value: audioGuide, setter: setAudioGuide },
    { key: "reroute", icon: "🤖", label: "Tự động điều tuyến", description: "AI tự sắp xếp lại lộ trình khi có thay đổi", value: autoReroute, setter: setAutoReroute },
    { key: "darkmap", icon: "🗺️", label: "Bản đồ tối (Dark Map)", description: "Dùng bản đồ tối tiết kiệm pin ban đêm", value: darkMap, setter: setDarkMap },
  ]

  const SettingSection = ({ title, items }: { title: string; items: SettingToggle[] }) => (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <View style={styles.sectionCard}>
        {items.map((item, i) => (
          <View key={item.key} style={[styles.settingRow, i < items.length - 1 && styles.settingRowBorder]}>
            <View style={styles.settingIconWrap}>
              <Text style={styles.settingIcon}>{item.icon}</Text>
            </View>
            <View style={styles.settingInfo}>
              <Text style={styles.settingLabel}>{item.label}</Text>
              <Text style={styles.settingDesc}>{item.description}</Text>
            </View>
            <Switch
              value={item.value}
              onValueChange={item.setter}
              trackColor={{ false: "rgba(255,255,255,0.1)", true: colors.palette.royalPurple }}
              thumbColor={item.value ? colors.palette.imperialGold : "rgba(255,255,255,0.4)"}
              ios_backgroundColor="rgba(255,255,255,0.1)"
            />
          </View>
        ))}
      </View>
    </View>
  )

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <LinearGradient
        colors={[colors.palette.deepSlate, "#111827", "#1a0a2e"]}
        style={StyleSheet.absoluteFillObject}
      />

      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
          <Text style={styles.backBtnText}>←</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Cài đặt</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView
        contentContainerStyle={[styles.scroll, { paddingBottom: insets.bottom + 80 }]}
        showsVerticalScrollIndicator={false}
      >
        <SettingSection title="🔔 Thông báo" items={NOTIFICATION_SETTINGS} />
        <SettingSection title="🗺️ Chuyến đi & AI" items={TRIP_SETTINGS} />

        {/* Developer settings */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>🛠️ Cài đặt nâng cao</Text>
          <View style={styles.sectionCard}>
            <View style={styles.apiRow}>
              <View style={styles.settingIconWrap}><Text style={styles.settingIcon}>🌐</Text></View>
              <View style={styles.apiInfo}>
                <Text style={styles.settingLabel}>API Backend URL</Text>
                <View style={[styles.apiInputWrap, apiInputFocused && styles.apiInputWrapFocused]}>
                  <TextInput
                    value={apiUrl}
                    onChangeText={setApiUrl}
                    style={styles.apiInput}
                    placeholderTextColor="rgba(255,255,255,0.25)"
                    autoCapitalize="none"
                    onFocus={() => setApiInputFocused(true)}
                    onBlur={() => setApiInputFocused(false)}
                  />
                </View>
              </View>
            </View>
          </View>
        </View>

        {/* About section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>ℹ️ Thông tin ứng dụng</Text>
          <View style={styles.sectionCard}>
            {[
              { icon: "📱", label: "Phiên bản", value: "1.0.0 (Build 42)" },
              { icon: "📜", label: "Điều khoản sử dụng", value: "›" },
              { icon: "🔒", label: "Chính sách bảo mật", value: "›" },
              { icon: "⭐", label: "Đánh giá ứng dụng", value: "›" },
            ].map((item, i, arr) => (
              <TouchableOpacity
                key={i}
                style={[styles.aboutRow, i < arr.length - 1 && styles.settingRowBorder]}
              >
                <View style={styles.settingIconWrap}><Text style={styles.settingIcon}>{item.icon}</Text></View>
                <Text style={styles.aboutLabel}>{item.label}</Text>
                <Text style={styles.aboutValue}>{item.value}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Danger zone */}
        <View style={styles.section}>
          <TouchableOpacity
            style={styles.logoutBtn}
            onPress={() => Alert.alert("Đăng xuất", "Bạn có chắc muốn đăng xuất?", [
              { text: "Hủy", style: "cancel" },
              { text: "Đăng xuất", style: "destructive", onPress: logout },
            ])}
          >
            <Text style={styles.logoutIcon}>🚪</Text>
            <Text style={styles.logoutText}>Đăng xuất</Text>
          </TouchableOpacity>

          <TouchableOpacity style={styles.deleteBtn}>
            <Text style={styles.deleteIcon}>🗑️</Text>
            <Text style={styles.deleteText}>Xóa tài khoản</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: spacing.lg, paddingBottom: 12,
    borderBottomWidth: 1, borderBottomColor: "rgba(255,255,255,0.06)",
  },
  backBtn: {
    width: 44, height: 44, borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.08)",
    justifyContent: "center", alignItems: "center",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
  },
  backBtnText: { fontSize: 20, color: "#FFFFFF", fontFamily: typography.primary.bold },
  headerTitle: { fontFamily: typography.primary.bold, fontSize: 20, color: "#FFFFFF" },
  scroll: { padding: spacing.lg },
  section: { marginBottom: spacing.lg },
  sectionTitle: {
    fontFamily: typography.primary.semiBold, fontSize: 13, color: "rgba(255,255,255,0.45)",
    textTransform: "uppercase", letterSpacing: 1, marginBottom: spacing.sm,
  },
  sectionCard: {
    backgroundColor: "rgba(255,255,255,0.05)",
    borderRadius: 16, borderWidth: 1, borderColor: "rgba(255,255,255,0.08)",
    overflow: "hidden",
  },
  settingRow: {
    flexDirection: "row", alignItems: "center",
    padding: spacing.md, gap: spacing.md,
  },
  settingRowBorder: { borderBottomWidth: 1, borderBottomColor: "rgba(255,255,255,0.05)" },
  settingIconWrap: {
    width: 40, height: 40, borderRadius: 12,
    backgroundColor: "rgba(255,255,255,0.06)",
    justifyContent: "center", alignItems: "center",
  },
  settingIcon: { fontSize: 20 },
  settingInfo: { flex: 1 },
  settingLabel: { fontFamily: typography.primary.semiBold, fontSize: 14, color: "#FFFFFF" },
  settingDesc: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.4)", marginTop: 2, lineHeight: 16 },
  apiRow: { flexDirection: "row", alignItems: "flex-start", padding: spacing.md, gap: spacing.md },
  apiInfo: { flex: 1 },
  apiInputWrap: {
    marginTop: 8, backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 10, paddingHorizontal: 12, paddingVertical: 8,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
  },
  apiInputWrapFocused: { borderColor: colors.palette.royalPurple },
  apiInput: { fontFamily: typography.primary.normal, fontSize: 13, color: "#FFFFFF" },
  aboutRow: { flexDirection: "row", alignItems: "center", padding: spacing.md, gap: spacing.md },
  aboutLabel: { fontFamily: typography.primary.medium, fontSize: 14, color: "#FFFFFF", flex: 1 },
  aboutValue: { fontFamily: typography.primary.normal, fontSize: 13, color: "rgba(255,255,255,0.35)" },
  logoutBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: spacing.sm, paddingVertical: 14,
    backgroundColor: colors.palette.sunsetOrange + "15",
    borderRadius: 16, borderWidth: 1, borderColor: colors.palette.sunsetOrange + "40",
    marginBottom: spacing.sm,
  },
  logoutIcon: { fontSize: 20 },
  logoutText: { fontFamily: typography.primary.semiBold, fontSize: 15, color: colors.palette.sunsetOrange },
  deleteBtn: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    gap: spacing.sm, paddingVertical: 14,
    backgroundColor: "rgba(255,255,255,0.03)",
    borderRadius: 16, borderWidth: 1, borderColor: "rgba(255,255,255,0.08)",
  },
  deleteIcon: { fontSize: 20 },
  deleteText: { fontFamily: typography.primary.medium, fontSize: 15, color: "rgba(255,255,255,0.3)" },
})