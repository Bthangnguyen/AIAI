/**
 * LoginScreen - Dark Royal Hue Design
 * Glassmorphism input fields + gradient CTA
 */
import React, { FC, useState, useRef } from "react"
import {
  View,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  TextInput,
  TouchableOpacity,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
  Animated,
} from "react-native"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
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
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [focusedField, setFocusedField] = useState<string | null>(null)
  const passwordRef = useRef<TextInput>(null)
  const insets = useSafeAreaInsets()
  const buttonScale = useRef(new Animated.Value(1)).current

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert("Thiếu thông tin", "Vui lòng nhập email và mật khẩu.")
      return
    }
    Animated.sequence([
      Animated.timing(buttonScale, { toValue: 0.96, duration: 100, useNativeDriver: true }),
      Animated.timing(buttonScale, { toValue: 1, duration: 100, useNativeDriver: true }),
    ]).start()
    setLoading(true)
    await new Promise((r) => setTimeout(r, 800))
    setAuthToken(String(Date.now()))
    setLoading(false)
  }

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <LinearGradient
        colors={[colors.palette.deepSlate, "#111827", "#1a0a2e"]}
        style={StyleSheet.absoluteFillObject}
      />
      {/* Decorative orbs */}
      <View style={styles.orb1} />
      <View style={styles.orb2} />

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : "height"}>
        <ScrollView
          contentContainerStyle={[styles.scroll, { paddingTop: insets.top + 20 }]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* Back */}
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <View style={styles.backBtnInner}>
              <Text style={styles.backArrow}>←</Text>
            </View>
          </TouchableOpacity>

          {/* Logo header */}
          <View style={styles.logoRow}>
            <View style={styles.logoIconWrap}>
              <Text style={styles.logoIconText}>📍</Text>
            </View>
            <Text style={styles.logoText}>TripFlow</Text>
          </View>

          {/* Title */}
          <Text style={styles.heading}>Chào mừng trở lại! 👋</Text>
          <Text style={styles.subheading}>Đăng nhập để tiếp tục hành trình của bạn</Text>

          {/* Social login buttons */}
          <TouchableOpacity style={styles.socialBtn} onPress={() => {}}>
            <LinearGradient
              colors={["rgba(255,255,255,0.08)", "rgba(255,255,255,0.04)"]}
              style={styles.socialBtnGradient}
            >
              <Text style={styles.socialBtnIcon}>🇬</Text>
              <Text style={styles.socialBtnText}>Tiếp tục với Google</Text>
            </LinearGradient>
          </TouchableOpacity>

          {/* Divider */}
          <View style={styles.divider}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>hoặc đăng nhập bằng email</Text>
            <View style={styles.dividerLine} />
          </View>

          {/* Email Field */}
          <View style={styles.fieldBlock}>
            <Text style={styles.label}>Email</Text>
            <View style={[styles.inputWrapper, focusedField === "email" && styles.inputWrapperFocused]}>
              <Text style={styles.inputIcon}>📧</Text>
              <TextInput
                style={styles.input}
                value={email}
                onChangeText={setEmail}
                placeholder="your@email.com"
                placeholderTextColor="rgba(255,255,255,0.25)"
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

          {/* Password Field */}
          <View style={styles.fieldBlock}>
            <Text style={styles.label}>Mật khẩu</Text>
            <View style={[styles.inputWrapper, focusedField === "password" && styles.inputWrapperFocused]}>
              <Text style={styles.inputIcon}>🔒</Text>
              <TextInput
                ref={passwordRef}
                style={[styles.input, { flex: 1 }]}
                value={password}
                onChangeText={setPassword}
                placeholder="••••••••"
                placeholderTextColor="rgba(255,255,255,0.25)"
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                returnKeyType="done"
                onSubmitEditing={handleLogin}
                onFocus={() => setFocusedField("password")}
                onBlur={() => setFocusedField(null)}
                testID="password-input"
              />
              <TouchableOpacity onPress={() => setShowPassword((v) => !v)} style={styles.eyeBtn}>
                <Text style={styles.eyeIcon}>{showPassword ? "🙈" : "👁️"}</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Forgot password */}
          <TouchableOpacity style={styles.forgotRow}>
            <Text style={styles.forgotText}>Quên mật khẩu?</Text>
          </TouchableOpacity>

          {/* Login CTA */}
          <Animated.View style={{ transform: [{ scale: buttonScale }] }}>
            <TouchableOpacity style={styles.loginBtn} onPress={handleLogin} disabled={loading} testID="login-btn">
              <LinearGradient
                colors={[colors.palette.royalPurple, colors.palette.royalPurpleLight]}
                style={styles.loginBtnGradient}
                start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
              >
                <Text style={styles.loginBtnText}>
                  {loading ? "Đang đăng nhập..." : "Đăng Nhập ✨"}
                </Text>
              </LinearGradient>
            </TouchableOpacity>
          </Animated.View>

          {/* Register link */}
          <TouchableOpacity style={styles.registerRow} onPress={() => navigation.navigate("Register")}>
            <Text style={styles.registerText}>
              Chưa có tài khoản?{" "}
              <Text style={styles.registerLink}>Đăng ký ngay</Text>
            </Text>
          </TouchableOpacity>

          {/* Demo bypass */}
          <TouchableOpacity style={styles.demoBtn} onPress={() => setAuthToken("demo_token")}>
            <Text style={styles.demoBtnText}>🚀 Demo Mode (Skip Login)</Text>
          </TouchableOpacity>

          <View style={{ height: insets.bottom + 20 }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  orb1: {
    position: "absolute", top: -100, right: -80,
    width: 280, height: 280, borderRadius: 140,
    backgroundColor: colors.palette.royalPurple + "35",
  },
  orb2: {
    position: "absolute", bottom: 100, left: -100,
    width: 250, height: 250, borderRadius: 125,
    backgroundColor: colors.palette.imperialGold + "15",
  },
  scroll: { paddingHorizontal: spacing.lg },
  backBtn: { marginBottom: spacing.lg },
  backBtnInner: {
    width: 44, height: 44, borderRadius: 14,
    backgroundColor: "rgba(255,255,255,0.08)",
    justifyContent: "center", alignItems: "center",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
  },
  backArrow: { fontSize: 20, color: "#FFFFFF" },
  logoRow: { flexDirection: "row", alignItems: "center", marginBottom: spacing.xl },
  logoIconWrap: {
    width: 38, height: 38, borderRadius: 12,
    backgroundColor: colors.palette.sunsetOrange,
    justifyContent: "center", alignItems: "center", marginRight: 8,
  },
  logoIconText: { fontSize: 20 },
  logoText: { fontFamily: typography.primary.bold, fontSize: 22, color: "#FFFFFF" },
  heading: { fontFamily: typography.primary.bold, fontSize: 28, color: "#FFFFFF", marginBottom: 8 },
  subheading: { fontFamily: typography.primary.normal, fontSize: 15, color: "rgba(255,255,255,0.5)", marginBottom: spacing.xl },
  socialBtn: {
    borderRadius: 16, overflow: "hidden",
    borderWidth: 1, borderColor: "rgba(255,255,255,0.12)",
    marginBottom: spacing.sm,
  },
  socialBtnGradient: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    paddingVertical: 14, gap: 10,
  },
  socialBtnIcon: { fontSize: 20 },
  socialBtnText: { fontFamily: typography.primary.semiBold, fontSize: 15, color: "#FFFFFF" },
  divider: { flexDirection: "row", alignItems: "center", marginVertical: spacing.lg, gap: spacing.sm },
  dividerLine: { flex: 1, height: 1, backgroundColor: "rgba(255,255,255,0.1)" },
  dividerText: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.35)" },
  fieldBlock: { marginBottom: spacing.md },
  label: { fontFamily: typography.primary.semiBold, fontSize: 13, color: "rgba(255,255,255,0.7)", marginBottom: 8 },
  inputWrapper: {
    flexDirection: "row", alignItems: "center",
    backgroundColor: "rgba(255,255,255,0.06)",
    borderRadius: 14, paddingHorizontal: spacing.md, height: 54,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.1)",
    gap: 10,
  },
  inputWrapperFocused: {
    borderColor: colors.palette.royalPurple,
    backgroundColor: "rgba(108,42,123,0.15)",
  },
  inputIcon: { fontSize: 18 },
  input: {
    flex: 1,
    fontFamily: typography.primary.normal, fontSize: 15,
    color: "#FFFFFF",
  },
  eyeBtn: { paddingLeft: spacing.sm },
  eyeIcon: { fontSize: 18 },
  forgotRow: { alignItems: "flex-end", marginBottom: spacing.lg },
  forgotText: { fontFamily: typography.primary.medium, fontSize: 13, color: colors.palette.imperialGold },
  loginBtn: { borderRadius: 16, overflow: "hidden", marginBottom: spacing.md },
  loginBtnGradient: {
    paddingVertical: 18, alignItems: "center",
    shadowColor: colors.palette.royalPurple,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.4, shadowRadius: 16,
  },
  loginBtnText: { fontFamily: typography.primary.semiBold, fontSize: 16, color: "#FFFFFF", letterSpacing: 0.3 },
  registerRow: { alignItems: "center", paddingVertical: spacing.sm },
  registerText: { fontFamily: typography.primary.normal, fontSize: 14, color: "rgba(255,255,255,0.45)" },
  registerLink: { fontFamily: typography.primary.semiBold, color: colors.palette.imperialGold },
  demoBtn: {
    alignItems: "center", paddingVertical: spacing.md,
    marginTop: spacing.sm,
    backgroundColor: "rgba(255,255,255,0.04)",
    borderRadius: 12,
    borderWidth: 1, borderColor: "rgba(255,255,255,0.08)",
  },
  demoBtnText: { fontFamily: typography.primary.normal, fontSize: 13, color: "rgba(255,255,255,0.4)" },
})