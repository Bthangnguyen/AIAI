/**
 * RegisterScreen — Figma "Login registration page" (register variant).
 * Name + email + password + confirm + social signup.
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

interface RegisterScreenProps extends AppStackScreenProps<"Register"> {}

export const RegisterScreen: FC<RegisterScreenProps> = ({ navigation }) => {
  const { setAuthToken } = useAuth()
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)

  const emailRef = useRef<TextInput>(null)
  const passwordRef = useRef<TextInput>(null)
  const confirmRef = useRef<TextInput>(null)

  const handleRegister = async () => {
    if (!name.trim() || !email.trim() || !password.trim()) {
      Alert.alert("Missing fields", "Please fill in all fields.")
      return
    }
    if (password !== confirm) {
      Alert.alert("Password mismatch", "Please make sure your passwords match.")
      return
    }
    setLoading(true)
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
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <Text style={styles.backArrow}>←</Text>
          </TouchableOpacity>

          <Text style={styles.heading}>Create Account ✨</Text>
          <Text style={styles.subheading}>
            Join millions of smart travelers
          </Text>

          {/* ─── Social Signup ── */}
          <SocialLoginButton
            provider="google"
            onPress={() => {}}
            style={styles.socialBtn}
          />
          <SocialLoginButton
            provider="apple"
            onPress={() => {}}
            style={styles.socialBtn}
          />

          {/* ─── Divider ── */}
          <View style={styles.divider}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>or sign up with email</Text>
            <View style={styles.dividerLine} />
          </View>

          {/* ─── Name Field ── */}
          <View style={styles.fieldBlock}>
            <Text style={styles.label}>Full Name</Text>
            <View style={styles.inputWrapper}>
              <TextInput
                style={styles.input}
                value={name}
                onChangeText={setName}
                placeholder="Nguyen Van A"
                placeholderTextColor={colors.palette.figmaGrayMedium}
                autoComplete="name"
                returnKeyType="next"
                onSubmitEditing={() => emailRef.current?.focus()}
                testID="name-input"
              />
            </View>
          </View>

          {/* ─── Email Field ── */}
          <View style={styles.fieldBlock}>
            <Text style={styles.label}>Email</Text>
            <View style={styles.inputWrapper}>
              <TextInput
                ref={emailRef}
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
                returnKeyType="next"
                onSubmitEditing={() => confirmRef.current?.focus()}
                testID="password-input"
              />
              <TouchableOpacity onPress={() => setShowPassword((v) => !v)}>
                <Text style={styles.eyeIcon}>{showPassword ? "🙈" : "👁️"}</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* ─── Confirm Password ── */}
          <View style={styles.fieldBlock}>
            <Text style={styles.label}>Confirm Password</Text>
            <View style={styles.inputWrapper}>
              <TextInput
                ref={confirmRef}
                style={styles.input}
                value={confirm}
                onChangeText={setConfirm}
                placeholder="••••••••"
                placeholderTextColor={colors.palette.figmaGrayMedium}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                returnKeyType="done"
                onSubmitEditing={handleRegister}
                testID="confirm-input"
              />
            </View>
          </View>

          {/* ─── Terms note ── */}
          <Text style={styles.terms}>
            By creating an account you agree to our{" "}
            <Text style={styles.termsLink}>Terms of Service</Text> and{" "}
            <Text style={styles.termsLink}>Privacy Policy</Text>
          </Text>

          {/* ─── Register CTA ── */}
          <CTAButton
            label={loading ? "Creating account…" : "Create Account"}
            onPress={handleRegister}
            style={styles.registerBtn}
            testID="register-btn"
          />

          {/* ─── Login Link ── */}
          <TouchableOpacity
            style={styles.loginRow}
            onPress={() => navigation.navigate("Login")}
          >
            <Text style={styles.loginText}>
              Already have an account?{" "}
              <Text style={styles.loginLink}>Sign in</Text>
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
  eyeIcon: { fontSize: 18 },
  terms: {
    fontFamily: typography.primary.normal,
    fontSize: 12,
    color: colors.palette.figmaGrayMedium,
    lineHeight: 18,
    textAlign: "center",
    marginBottom: spacing.lg,
  },
  termsLink: {
    fontFamily: typography.primary.semiBold,
    color: colors.palette.figmaBlue,
  },
  registerBtn: {
    marginBottom: spacing.md,
  },
  loginRow: {
    alignItems: "center",
    paddingVertical: spacing.xs,
  },
  loginText: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.figmaGrayMedium,
  },
  loginLink: {
    fontFamily: typography.primary.semiBold,
    color: colors.palette.figmaBlack,
  },
})
