import React, { FC, useState } from "react"
import { View, ViewStyle, TextStyle, ImageBackground, StyleSheet, Pressable, ScrollView } from "react-native"
import { Screen } from "@/components/Screen"
import { Text } from "@/components/Text"
import { TextField } from "@/components/TextField"
import type { AppStackScreenProps } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

interface HomeScreenProps extends AppStackScreenProps<"MainTabs"> {}

const BACKGROUND_URL = "https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?q=80&w=2021&auto=format&fit=crop"

export const HomeScreen: FC<HomeScreenProps> = ({ navigation }) => {
  const [prompt, setPrompt] = useState("")
  const [chatHistory, setChatHistory] = useState<{sender: string, text: string}[]>([])

  const handleSend = () => {
    if (!prompt.trim()) return
    setChatHistory([...chatHistory, { sender: 'user', text: prompt }])
    setPrompt("")
    // Trigger follow-up check or progressive loading
    setTimeout(() => {
      navigation.navigate("Loading", { prompt: prompt })
    }, 1000)
  }

  const handleChip = (chipText: string) => {
    setPrompt(chipText)
  }

  return (
    <Screen style={$root} preset="fixed" contentContainerStyle={{ flex: 1 }} safeAreaEdges={["top"]}>
      <ImageBackground source={{ uri: BACKGROUND_URL }} style={$background} blurRadius={8}>
        <View style={$overlay} />
        
        {/* Header */}
        <View style={$header}>
          <Text text="Bạn muốn đi đâu?" style={$titleHighlight} />
        </View>

        {/* Chat Area */}
        <ScrollView style={$chatArea} contentContainerStyle={{ paddingBottom: 20 }}>
          {chatHistory.length === 0 && (
            <View style={$welcomeContainer}>
              <Text text="Hãy trò chuyện để lên kế hoạch!" style={$heroSub} />
            </View>
          )}
          {chatHistory.map((msg, idx) => (
            <View key={idx} style={msg.sender === 'user' ? $userMsg : $aiMsg}>
              <Text text={msg.text} style={{ color: msg.sender === 'user' ? '#fff' : '#333' }} />
            </View>
          ))}
        </ScrollView>

        {/* Glass Input Card */}
        <View style={$glassCard}>
          {chatHistory.length === 0 && (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={$chipsContainer}>
              <Pressable style={$chip} onPress={() => handleChip("Đi Huế 3 ngày")}><Text text="Đi Huế 3 ngày" style={$chipText} /></Pressable>
              <Pressable style={$chip} onPress={() => handleChip("Du lịch Đà Lạt budget 2tr")}><Text text="Đà Lạt budget 2tr" style={$chipText} /></Pressable>
            </ScrollView>
          )}
          
          <View style={$inputRow}>
            <TextField
              value={prompt}
              onChangeText={setPrompt}
              containerStyle={$inputContainer}
              style={$promptInput}
              placeholder="Nhập lịch trình bạn muốn..."
              placeholderTextColor={colors.palette.figmaPlaceholder}
              multiline
            />
            <Pressable onPress={handleSend} style={$sendButton}>
              <Text text="Gửi" style={$buttonText} />
            </Pressable>
          </View>
        </View>
      </ImageBackground>
    </Screen>
  )
}

const $root: ViewStyle = { flex: 1 }
const $background: ViewStyle = { flex: 1, justifyContent: "space-between", paddingHorizontal: spacing.lg, paddingBottom: spacing.lg }
const $overlay: ViewStyle = { ...StyleSheet.absoluteFillObject, backgroundColor: "rgba(0, 0, 0, 0.55)" }
const $header: ViewStyle = { marginTop: spacing.xxxl, alignItems: 'center' }
const $titleHighlight: TextStyle = { fontSize: 32, fontFamily: typography.primary.bold, color: colors.tint, textAlign: 'center' }
const $heroSub: TextStyle = { fontSize: 16, color: "rgba(255, 255, 255, 0.7)", textAlign: 'center' }
const $chatArea: ViewStyle = { flex: 1, marginTop: spacing.md }
const $welcomeContainer: ViewStyle = { flex: 1, justifyContent: 'center', alignItems: 'center', marginTop: 100 }
const $userMsg: ViewStyle = { alignSelf: 'flex-end', backgroundColor: colors.tint, padding: 12, borderRadius: 16, marginVertical: 4, maxWidth: '80%' }
const $aiMsg: ViewStyle = { alignSelf: 'flex-start', backgroundColor: '#fff', padding: 12, borderRadius: 16, marginVertical: 4, maxWidth: '80%' }

const $glassCard: ViewStyle = { backgroundColor: colors.palette.glassWhite10, borderRadius: 24, padding: spacing.md, borderWidth: 1, borderColor: "rgba(255, 255, 255, 0.2)" }
const $chipsContainer: ViewStyle = { flexDirection: 'row', marginBottom: spacing.md }
const $chip: ViewStyle = { backgroundColor: 'rgba(255,255,255,0.2)', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 16, marginRight: 8 }
const $chipText: TextStyle = { color: '#fff', fontSize: 14 }
const $inputRow: ViewStyle = { flexDirection: 'row', alignItems: 'flex-end' }
const $inputContainer: ViewStyle = { flex: 1, marginRight: spacing.sm }
const $promptInput: TextStyle = { fontSize: 16, color: "#FFFFFF", minHeight: 40, maxHeight: 100 }
const $sendButton: ViewStyle = { backgroundColor: colors.tint, borderRadius: 20, paddingHorizontal: 16, paddingVertical: 12, justifyContent: 'center', alignItems: 'center' }
const $buttonText: TextStyle = { color: "#FFFFFF", fontFamily: typography.primary.semiBold, fontSize: 16 }
