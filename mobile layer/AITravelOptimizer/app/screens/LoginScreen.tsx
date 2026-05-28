import React, { FC, useRef, useState } from "react"
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StatusBar,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"

import { AppIcon } from "@/components/AppIcon"
import { Text } from "@/components/Text"
import { useAuth } from "@/context/AuthContext"
import type { AppStackScreenProps } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

interface LoginScreenProps extends AppStackScreenProps<"Login"> {}

export const LoginScreen: FC<LoginScreenProps> = ({ navigation }) => {
  const { setAuthToken } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [focusedField, setFocusedField] = useState<string | null>(null)
  const passwordRef = useRef<TextInput>(null)
  const insets = useSafeAreaInsets()

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert("Thiếu thông tin", "Vui lòng nhập email và mật khẩu.")
      return
    }
    setLoading(true)
    await new Promise((r) => setTimeout(r, 600))
    setAuthToken(String(Date.now()))
    setLoading(false)
  }

  return (
    <View style={styles.root}>
      <StatusBar barStyle="dark-content" backgroundColor="transparent" translucent />
      <LinearGradient colors={[colors.palette.appCream, "#FFFFFF"]} style={StyleSheet.absoluteFillObject} />

      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === "ios" ? "padding" : "height"}>
        <ScrollView
          contentContainerStyle={[styles.scroll, { paddingTop: insets.top + 20, paddingBottom: insets.bottom + 24 }]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <AppIcon name="back" size={20} color={colors.palette.appInk} />
          </TouchableOpacity>

          <View style={styles.logoRow}>
            <View style={styles.logoIconWrap}>
              <AppIcon name="pin" size={20} color="#FFFFFF" />
            </View>
            <View>
              <Text style={styles.logoText}>TripFlow</Text>
              <Text style={styles.logoSub}>Tối ưu hành trình thông minh</Text>
            </View>
          </View>

          <View style={styles.heroCard}>
            <Text style={styles.heading}>Chào mừng trở lại</Text>
            <Text style={styles.subheading}>Đăng nhập để tiếp tục quản lý lịch trình, GPS và reroute.</Text>
          </View>

          <View style={styles.formCard}>
            <View style={styles.fieldBlock}>
              <Text style={styles.label}>Email</Text>
              <View style={[styles.inputWrapper, focusedField === "email" && styles.inputWrapperFocused]}>
                <TextInput
                  style={styles.input}
                  value={email}
                  onChangeText={setEmail}
                  placeholder="your@email.com"
                  placeholderTextColor={colors.palette.appMuted}
                  autoCapitalize="none"
                  keyboardType="email-address"
                  returnKeyType="next"
                  onSubmitEditing={() => passwordRef.current?.focus()}
                  onFocus={() => setFocusedField("email")}
                  onBlur={() => setFocusedField(null)}
                  testID="email-input"
                />
              </View>
            </View>

            <View style={styles.fieldBlock}>
              <Text style={styles.label}>Mật khẩu</Text>
              <View style={[styles.inputWrapper, focusedField === "password" && styles.inputWrapperFocused]}>
                <TextInput
                  ref={passwordRef}
                  style={styles.input}
                  value={password}
                  onChangeText={setPassword}
                  placeholder="Nhập mật khẩu"
                  placeholderTextColor={colors.palette.appMuted}
                  secureTextEntry
                  autoCapitalize="none"
                  returnKeyType="done"
                  onSubmitEditing={handleLogin}
                  onFocus={() => setFocusedField("password")}
                  onBlur={() => setFocusedField(null)}
                  testID="password-input"
                />
              </View>
            </View>

            <TouchableOpacity style={styles.loginBtn} onPress={handleLogin} disabled={loading} testID="login-btn">
              <LinearGradient
                colors={[colors.palette.appOrange, colors.palette.appOrangeDark]}
                style={styles.loginBtnGradient}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
              >
                <Text style={styles.loginBtnText}>{loading ? "Đang đăng nhập..." : "Đăng nhập"}</Text>
              </LinearGradient>
            </TouchableOpacity>

            <TouchableOpacity style={styles.registerRow} onPress={() => navigation.navigate("Register")}>
              <Text style={styles.registerText}>
                Chưa có tài khoản? <Text style={styles.registerLink}>Đăng ký ngay</Text>
              </Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity style={styles.demoBtn} onPress={() => setAuthToken("demo_token")}>
            <Text style={styles.demoBtnText}>Demo Mode (Skip Login)</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.palette.appCream },
  flex: { flex: 1 },
  scroll: { paddingHorizontal: spacing.lg },
  backBtn: {
    width: 42,
    height: 42,
    borderRadius: 14,
    backgroundColor: "#FFFFFF",
    justifyContent: "center",
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.palette.appLine,
    marginBottom: spacing.lg,
  },
  logoRow: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: spacing.xl },
  logoIconWrap: {
    width: 44,
    height: 44,
    borderRadius: 16,
    backgroundColor: colors.palette.appOrange,
    justifyContent: "center",
    alignItems: "center",
  },
  logoText: { fontFamily: typography.primary.bold, fontSize: 24, color: colors.palette.appInk },
  logoSub: { fontFamily: typography.primary.medium, fontSize: 12, color: colors.palette.appMuted },
  heroCard: { marginBottom: spacing.lg },
  heading: { fontFamily: typography.primary.bold, fontSize: 32, color: colors.palette.appInk, lineHeight: 39 },
  subheading: {
    fontFamily: typography.primary.normal,
    fontSize: 15,
    color: colors.palette.appMuted,
    lineHeight: 23,
    marginTop: 8,
  },
  formCard: {
    backgroundColor: "#FFFFFF",
    borderRadius: 22,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.palette.appLine,
    gap: spacing.md,
  },
  fieldBlock: { gap: 8 },
  label: { fontFamily: typography.primary.semiBold, fontSize: 13, color: colors.palette.appInk },
  inputWrapper: {
    backgroundColor: colors.palette.appCream,
    borderRadius: 15,
    paddingHorizontal: spacing.md,
    height: 54,
    borderWidth: 1,
    borderColor: colors.palette.appLine,
    justifyContent: "center",
  },
  inputWrapperFocused: {
    borderColor: colors.palette.appOrange,
    backgroundColor: "#FFFFFF",
  },
  input: {
    fontFamily: typography.primary.normal,
    fontSize: 15,
    color: colors.palette.appInk,
    paddingVertical: 0,
  },
  loginBtn: { borderRadius: 16, overflow: "hidden", marginTop: spacing.xs },
  loginBtnGradient: { paddingVertical: 15, alignItems: "center", justifyContent: "center" },
  loginBtnText: { fontFamily: typography.primary.bold, fontSize: 15, color: "#FFFFFF" },
  registerRow: { alignItems: "center" },
  registerText: { fontFamily: typography.primary.normal, fontSize: 14, color: colors.palette.appMuted },
  registerLink: { fontFamily: typography.primary.bold, color: colors.palette.appOrangeDark },
  demoBtn: {
    marginTop: spacing.lg,
    alignItems: "center",
    paddingVertical: 14,
    borderRadius: 16,
    backgroundColor: colors.palette.appOrangeSoft,
    borderWidth: 1,
    borderColor: colors.palette.appLine,
  },
  demoBtnText: { fontFamily: typography.primary.semiBold, fontSize: 14, color: colors.palette.appOrangeDark },
})
