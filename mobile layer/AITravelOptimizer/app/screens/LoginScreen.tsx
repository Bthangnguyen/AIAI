/**
 * LoginScreen — Figma "Login registration page" clone.
 * Full-screen hero + white card + email/password fields + social login.
 */
import { FC, useRef, useState } from "react"
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  TextInput,
  TouchableOpacity,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from "react-native"
import { NativeStackScreenProps } from "@react-navigation/native-stack"

import { useAuth } from "@/context/AuthContext"
import type { AppStackScreenProps } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { CTAButton } from "@/components/CTAButton"
import { SocialLoginButton } from "@/components/SocialLoginButton"

interface LoginScreenProps extends AppStackScreenProps<"Login"> {}

export const LoginScreen: FC<LoginScreenProps> = ({ navigation }) => {
  const { setAuthToken } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const passwordRef = useRef<TextInput>(null)

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) {
      Alert.alert("Missing fields", "Please enter both email and password.")
      return
    }
    setLoading(true)
    // Simulate auth delay (mock)
    await new Promise((r) => setTimeout(r, 800))
    setAuthToken(String(Date.now()))
    setLoading(false)
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.palette.figmaWhite} />
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* ─── Header ── */}
          <TouchableOpacity
            style={styles.backBtn}
            onPress={() => navigation.goBack()}
          >
            <Text style={styles.backArrow}>←</Text>
          </TouchableOpacity>

          <Text style={styles.heading}>Welcome Back 👋</Text>
          <Text style={styles.subheading}>
            Sign in to continue your adventure
          </Text>

          {/* ─── Social Login ── */}
          <SocialLoginButton
            provider="google"
            onPress={() => {}}
            style={styles.socialBtn}
            testID="google-login"
          />
          <SocialLoginButton
            provider="facebook"
            onPress={() => {}}
            style={styles.socialBtn}
          />

          {/* ─── Divider ── */}
          <View style={styles.divider}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>or continue with email</Text>
            <View style={styles.dividerLine} />
          </View>

          {/* ─── Email Field ── */}
          <View style={styles.fieldBlock}>
            <Text style={styles.label}>Email</Text>
            <View style={styles.inputWrapper}>
              <TextInput
                style={styles.input}
                value={email}
                onChangeText={setEmail}
                placeholder="your@email.com"
                placeholderTextColor={colors.palette.figmaGrayMedium}
                autoCapitalize="none"
                autoComplete="email"
                keyboardType="email-address"
                returnKeyType="next"
                onSubmitEditing={() => passwordRef.current?.focus()}
                testID="email-input"
              />
            </View>
          </View>

          {/* ─── Password Field ── */}
          <View style={styles.fieldBlock}>
            <Text style={styles.label}>Password</Text>
            <View style={styles.inputWrapper}>
              <TextInput
                ref={passwordRef}
                style={[styles.input, { flex: 1 }]}
                value={password}
                onChangeText={setPassword}
                placeholder="••••••••"
                placeholderTextColor={colors.palette.figmaGrayMedium}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                returnKeyType="done"
                onSubmitEditing={handleLogin}
                testID="password-input"
              />
              <TouchableOpacity
                onPress={() => setShowPassword((v) => !v)}
                style={styles.eyeBtn}
              >
                <Text style={styles.eyeIcon}>{showPassword ? "🙈" : "👁️"}</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* ─── Forgot Password ── */}
          <TouchableOpacity style={styles.forgotRow}>
            <Text style={styles.forgotText}>Forgot password?</Text>
          </TouchableOpacity>

          {/* ─── Login CTA ── */}
          <CTAButton
            label={loading ? "Signing in…" : "Sign in"}
            onPress={handleLogin}
            style={styles.loginBtn}
            testID="login-btn"
          />

          {/* ─── Register Link ── */}
          <TouchableOpacity
            style={styles.registerRow}
            onPress={() => navigation.navigate("Register")}
          >
            <Text style={styles.registerText}>
              Don't have an account?{" "}
              <Text style={styles.registerLink}>Create one</Text>
            </Text>
          </TouchableOpacity>

          <View style={{ height: spacing.xxl }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.palette.figmaWhite,
  },
  scroll: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
  },
  backBtn: {
    width: 40,
    height: 40,
    justifyContent: "center",
    marginBottom: spacing.lg,
  },
  backArrow: { fontSize: 22, color: colors.palette.figmaBlack },
  heading: {
    fontFamily: typography.primary.bold,
    fontSize: 28,
    color: colors.palette.figmaBlack,
    marginBottom: spacing.xs,
  },
  subheading: {
    fontFamily: typography.primary.normal,
    fontSize: 15,
    color: colors.palette.figmaGrayMedium,
    marginBottom: spacing.xl,
  },
  socialBtn: {
    marginBottom: spacing.sm,
  },
  divider: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: spacing.lg,
    gap: spacing.sm,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: colors.palette.figmaGrayLight,
  },
  dividerText: {
    fontFamily: typography.primary.normal,
    fontSize: 12,
    color: colors.palette.figmaGrayMedium,
  },
  fieldBlock: {
    marginBottom: spacing.md,
  },
  label: {
    fontFamily: typography.primary.semiBold,
    fontSize: 14,
    color: colors.palette.figmaBlack,
    marginBottom: spacing.xxs,
  },
  inputWrapper: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: colors.palette.figmaOffWhite,
    borderRadius: 15,
    paddingHorizontal: spacing.md,
    height: 54,
  },
  input: {
    flex: 1,
    fontFamily: typography.primary.normal,
    fontSize: 15,
    color: colors.palette.figmaGrayDark,
  },
  eyeBtn: { paddingLeft: spacing.sm },
  eyeIcon: { fontSize: 18 },
  forgotRow: {
    alignItems: "flex-end",
    marginBottom: spacing.lg,
  },
  forgotText: {
    fontFamily: typography.primary.medium,
    fontSize: 13,
    color: colors.palette.figmaBlue,
  },
  loginBtn: {
    marginBottom: spacing.md,
  },
  registerRow: {
    alignItems: "center",
    paddingVertical: spacing.xs,
  },
  registerText: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.figmaGrayMedium,
  },
  registerLink: {
    fontFamily: typography.primary.semiBold,
    color: colors.palette.figmaBlack,
  },
})
