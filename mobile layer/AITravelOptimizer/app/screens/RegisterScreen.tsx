/**
 * RegisterScreen - Dark Royal Hue Design
 */
import React, { FC, useState, useRef } from "react"
import {
  View, StyleSheet, StatusBar, TextInput, TouchableOpacity,
  ScrollView, KeyboardAvoidingView, Platform, Alert, Animated,
} from "react-native"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { Text } from "@/components/Text"
import { useAuth } from "@/context/AuthContext"
import type { AppStackScreenProps } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

interface RegisterScreenProps extends AppStackScreenProps<"Register"> {}

export const RegisterScreen: FC<RegisterScreenProps> = ({ navigation }) => {
  const { setAuthToken } = useAuth()
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [focusedField, setFocusedField] = useState<string | null>(null)
  const emailRef = useRef<TextInput>(null)
  const passwordRef = useRef<TextInput>(null)
  const insets = useSafeAreaInsets()
  const buttonScale = useRef(new Animated.Value(1)).current

  const handleRegister = async () => {
    if (!name.trim() || !email.trim() || !password.trim()) {
      Alert.alert("Thiếu thông tin", "Vui lòng điền đầy đủ tất cả các trường.")
      return
    }
    Animated.sequence([
      Animated.timing(buttonScale, { toValue: 0.96, duration: 100, useNativeDriver: true }),
      Animated.timing(buttonScale, { toValue: 1, duration: 100, useNativeDriver: true }),
    ]).start()
    setLoading(true)
    await new Promise((r) => setTimeout(r, 1000))
    setAuthToken(String(Date.now()))
    setLoading(false)
  }

  const fields = [
    { key: "name", label: "Họ tên", icon: "👤", placeholder: "Nguyễn Văn A", ref: null, next: emailRef, value: name, setter: setName, type: "default" as const },
    { key: "email", label: "Email", icon: "📧", placeholder: "your@email.com", ref: emailRef, next: passwordRef, value: email, setter: setEmail, type: "email-address" as const },
    { key: "password", label: "Mật khẩu", icon: "🔒", placeholder: "Ít nhất 8 ký tự", ref: passwordRef, next: null, value: password, setter: setPassword, type: "default" as const },
  ]

  return (
    <View style={styles.root}>
      <StatusBar barStyle="light-content" backgroundColor="transparent" translucent />
      <LinearGradient colors={[colors.palette.deepSlate, "#111827", "#1a0a2e"]} style={StyleSheet.absoluteFillObject} />
      <View style={styles.orb1} />
      <View style={styles.orb2} />

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : "height"}>
        <ScrollView
          contentContainerStyle={[styles.scroll, { paddingTop: insets.top + 20 }]}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <View style={styles.backBtnInner}><Text style={styles.backArrow}>←</Text></View>
          </TouchableOpacity>

          <View style={styles.logoRow}>
            <View style={styles.logoIconWrap}><Text style={styles.logoIconText}>📍</Text></View>
            <Text style={styles.logoText}>TripFlow</Text>
          </View>

          <Text style={styles.heading}>Tạo tài khoản mới 🚀</Text>
          <Text style={styles.subheading}>Bắt đầu hành trình khám phá Huế cùng AI</Text>

          {fields.map((field) => (
            <View key={field.key} style={styles.fieldBlock}>
              <Text style={styles.label}>{field.label}</Text>
              <View style={[styles.inputWrapper, focusedField === field.key && styles.inputWrapperFocused]}>
                <Text style={styles.inputIcon}>{field.icon}</Text>
                <TextInput
                  ref={field.ref as any}
                  style={[styles.input, { flex: field.key === "password" ? 1 : undefined }]}
                  value={field.value}
                  onChangeText={field.setter}
                  placeholder={field.placeholder}
                  placeholderTextColor="rgba(255,255,255,0.25)"
                  autoCapitalize={field.key === "name" ? "words" : "none"}
                  keyboardType={field.type}
                  secureTextEntry={field.key === "password" && !showPassword}
                  returnKeyType={field.next ? "next" : "done"}
                  onSubmitEditing={() => field.next?.current?.focus()}
                  onFocus={() => setFocusedField(field.key)}
                  onBlur={() => setFocusedField(null)}
                />
                {field.key === "password" && (
                  <TouchableOpacity onPress={() => setShowPassword((v) => !v)} style={styles.eyeBtn}>
                    <Text style={styles.eyeIcon}>{showPassword ? "🙈" : "👁️"}</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          ))}

          {/* Terms note */}
          <Text style={styles.termsText}>
            Bằng cách đăng ký, bạn đồng ý với{" "}
            <Text style={styles.termsLink}>Điều khoản sử dụng</Text> của chúng tôi.
          </Text>

          <Animated.View style={{ transform: [{ scale: buttonScale }] }}>
            <TouchableOpacity style={styles.registerBtn} onPress={handleRegister} disabled={loading}>
              <LinearGradient
                colors={[colors.palette.royalPurple, colors.palette.royalPurpleLight]}
                style={styles.registerBtnGradient}
                start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
              >
                <Text style={styles.registerBtnText}>
                  {loading ? "Đang tạo tài khoản..." : "Đăng Ký ✨"}
                </Text>
              </LinearGradient>
            </TouchableOpacity>
          </Animated.View>

          <TouchableOpacity style={styles.loginRow} onPress={() => navigation.navigate("Login")}>
            <Text style={styles.loginText}>
              Đã có tài khoản?{" "}
              <Text style={styles.loginLink}>Đăng nhập</Text>
            </Text>
          </TouchableOpacity>
          <View style={{ height: insets.bottom + 20 }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  )
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  orb1: { position: "absolute", top: -60, left: -80, width: 220, height: 220, borderRadius: 110, backgroundColor: colors.palette.royalPurple + "30" },
  orb2: { position: "absolute", bottom: 200, right: -60, width: 180, height: 180, borderRadius: 90, backgroundColor: colors.palette.jadeGreen + "15" },
  scroll: { paddingHorizontal: spacing.lg },
  backBtn: { marginBottom: spacing.lg },
  backBtnInner: { width: 44, height: 44, borderRadius: 14, backgroundColor: "rgba(255,255,255,0.08)", justifyContent: "center", alignItems: "center", borderWidth: 1, borderColor: "rgba(255,255,255,0.12)" },
  backArrow: { fontSize: 20, color: "#FFFFFF" },
  logoRow: { flexDirection: "row", alignItems: "center", marginBottom: spacing.xl },
  logoIconWrap: { width: 38, height: 38, borderRadius: 12, backgroundColor: colors.palette.sunsetOrange, justifyContent: "center", alignItems: "center", marginRight: 8 },
  logoIconText: { fontSize: 20 },
  logoText: { fontFamily: typography.primary.bold, fontSize: 22, color: "#FFFFFF" },
  heading: { fontFamily: typography.primary.bold, fontSize: 26, color: "#FFFFFF", marginBottom: 8 },
  subheading: { fontFamily: typography.primary.normal, fontSize: 14, color: "rgba(255,255,255,0.5)", marginBottom: spacing.xl },
  fieldBlock: { marginBottom: spacing.md },
  label: { fontFamily: typography.primary.semiBold, fontSize: 13, color: "rgba(255,255,255,0.7)", marginBottom: 8 },
  inputWrapper: { flexDirection: "row", alignItems: "center", backgroundColor: "rgba(255,255,255,0.06)", borderRadius: 14, paddingHorizontal: spacing.md, height: 54, borderWidth: 1, borderColor: "rgba(255,255,255,0.1)", gap: 10 },
  inputWrapperFocused: { borderColor: colors.palette.royalPurple, backgroundColor: "rgba(108,42,123,0.15)" },
  inputIcon: { fontSize: 18 },
  input: { fontFamily: typography.primary.normal, fontSize: 15, color: "#FFFFFF" },
  eyeBtn: { paddingLeft: spacing.sm },
  eyeIcon: { fontSize: 18 },
  termsText: { fontFamily: typography.primary.normal, fontSize: 12, color: "rgba(255,255,255,0.35)", textAlign: "center", marginBottom: spacing.lg, lineHeight: 18 },
  termsLink: { color: colors.palette.imperialGold, fontFamily: typography.primary.medium },
  registerBtn: { borderRadius: 16, overflow: "hidden", marginBottom: spacing.md },
  registerBtnGradient: { paddingVertical: 18, alignItems: "center" },
  registerBtnText: { fontFamily: typography.primary.semiBold, fontSize: 16, color: "#FFFFFF", letterSpacing: 0.3 },
  loginRow: { alignItems: "center", paddingVertical: spacing.sm },
  loginText: { fontFamily: typography.primary.normal, fontSize: 14, color: "rgba(255,255,255,0.45)" },
  loginLink: { fontFamily: typography.primary.semiBold, color: colors.palette.imperialGold },
})