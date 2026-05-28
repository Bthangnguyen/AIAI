/**
 * ItineraryFormScreen - Dark Royal Hue Design
 * Date range picker + query suggestions + hotel picker + AI Generate
 */
import React, { useState } from "react"
import {
  View, StyleSheet, ScrollView, TouchableOpacity,
  TextInput, StatusBar, Dimensions, Platform,
} from "react-native"
import { LinearGradient } from "expo-linear-gradient"
import { useSafeAreaInsets } from "react-native-safe-area-context"
import { useNavigation } from "@react-navigation/native"
import type { NativeStackNavigationProp } from "@react-navigation/native-stack"
import { Text } from "@/components/Text"
import { HotelPicker, HotelSelection } from "@/components/HotelPicker"
import { DEFAULT_HOTEL } from "@/constants/presetHotels"
import { AppStackParamList } from "@/navigators/navigationTypes"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

const { width } = Dimensions.get("window")
type Nav = NativeStackNavigationProp<AppStackParamList>

const DAYS_OF_WEEK = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
const MONTH_NAMES = ["Tháng 1","Tháng 2","Tháng 3","Tháng 4","Tháng 5","Tháng 6","Tháng 7","Tháng 8","Tháng 9","Tháng 10","Tháng 11","Tháng 12"]

const getDaysInMonth = (y: number, m: number) => new Date(y, m + 1, 0).getDate()
const getFirstDay = (y: number, m: number) => { const d = new Date(y, m, 1).getDay(); return d === 0 ? 6 : d - 1 }

const PROMPT_SUGGESTIONS = [
  "🏯 Tập trung vào di tích lịch sử UNESCO",
  "🍜 Ẩm thực cung đình + chợ địa phương",
  "🛵 Tour xe máy ngoại thành thư thái",
  "👨‍👩‍👧 Phù hợp gia đình, có trẻ em",
  "💰 Tiết kiệm tối đa, ưu tiên miễn phí",
]

export const ItineraryFormScreen: React.FC = () => {
  const navigation = useNavigation<Nav>()
  const insets = useSafeAreaInsets()
  const today = new Date()
  const [viewMonth, setViewMonth] = useState(today.getMonth())
  const [viewYear, setViewYear] = useState(today.getFullYear())
  const [selectedStart, setSelectedStart] = useState<Date | null>(null)
  const [selectedEnd, setSelectedEnd] = useState<Date | null>(null)
  const [query, setQuery] = useState("")
  const [queryFocused, setQueryFocused] = useState(false)
  const [hotel, setHotel] = useState<HotelSelection>({ name: DEFAULT_HOTEL.name, lat: DEFAULT_HOTEL.lat, lon: DEFAULT_HOTEL.lon })

  const daysInMonth = getDaysInMonth(viewYear, viewMonth)
  const firstDay = getFirstDay(viewYear, viewMonth)
  const calCells: (number | null)[] = [...Array(firstDay).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => i + 1)]
  while (calCells.length % 7 !== 0) calCells.push(null)

  const handleDayPress = (day: number) => {
    const d = new Date(viewYear, viewMonth, day)
    if (!selectedStart || (selectedStart && selectedEnd)) {
      setSelectedStart(d); setSelectedEnd(null)
    } else if (d >= selectedStart) {
      setSelectedEnd(d)
    } else {
      setSelectedStart(d); setSelectedEnd(null)
    }
  }

  const isStart = (day: number) => {
    if (!selectedStart || !day) return false
    const d = new Date(viewYear, viewMonth, day)
    return d.toDateString() === selectedStart.toDateString()
  }

  const isEnd = (day: number) => {
    if (!selectedEnd || !day) return false
    const d = new Date(viewYear, viewMonth, day)
    return d.toDateString() === selectedEnd.toDateString()
  }

  const isInRange = (day: number) => {
    if (!selectedStart || !selectedEnd || !day) return false
    const d = new Date(viewYear, viewMonth, day)
    return d > selectedStart && d < selectedEnd
  }

  const isPast = (day: number) => {
    if (!day) return false
    return new Date(viewYear, viewMonth, day) < today
  }

  const numDays = selectedStart && selectedEnd
    ? Math.round((selectedEnd.getTime() - selectedStart.getTime()) / 86400000) + 1
    : 0

  const handleGenerate = () => {
    if (!selectedStart || !selectedEnd) return
    navigation.navigate("Loading", {
      prompt: query || "Lộ trình tham quan Huế",
      hotelName: hotel.name,
      hotelLat: hotel.lat,
      hotelLon: hotel.lon,
      numDays,
    })
  }

  const formatDate = (d: Date) =>
    `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`

  return (
    <View style={styles.root}>
      <StatusBar barStyle="dark-content" backgroundColor="transparent" translucent />
      <LinearGradient colors={[colors.palette.appCream, "#FFFFFF"]} style={StyleSheet.absoluteFillObject} />

      {/* Header */}
      <View style={[styles.header, { paddingTop: insets.top + 12 }]}>
        <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
          <Text style={styles.backBtnText}>←</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Lên Kế Hoạch</Text>
        <View style={{ width: 44 }} />
      </View>

      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={[styles.scroll, { paddingBottom: insets.bottom + 100 }]}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
      >
        {/* Calendar section */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>📅 Chọn ngày đi</Text>
          <View style={styles.calendarCard}>
            {/* Month nav */}
            <View style={styles.monthNav}>
              <TouchableOpacity
                style={styles.monthNavBtn}
                onPress={() => { if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1) } else setViewMonth(m => m - 1) }}
              >
                <Text style={styles.monthNavBtnText}>‹</Text>
              </TouchableOpacity>
              <Text style={styles.monthTitle}>{MONTH_NAMES[viewMonth]} {viewYear}</Text>
              <TouchableOpacity
                style={styles.monthNavBtn}
                onPress={() => { if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1) } else setViewMonth(m => m + 1) }}
              >
                <Text style={styles.monthNavBtnText}>›</Text>
              </TouchableOpacity>
            </View>

            {/* Day headers */}
            <View style={styles.dayHeaders}>
              {DAYS_OF_WEEK.map(d => (
                <Text key={d} style={styles.dayHeader}>{d}</Text>
              ))}
            </View>

            {/* Calendar grid */}
            <View style={styles.calGrid}>
              {calCells.map((day, i) => {
                const start = day ? isStart(day) : false
                const end = day ? isEnd(day) : false
                const inRange = day ? isInRange(day) : false
                const past = day ? isPast(day) : false
                return (
                  <TouchableOpacity
                    key={i}
                    style={[
                      styles.dayCell,
                      inRange && styles.dayCellInRange,
                      (start || end) && styles.dayCellSelected,
                      past && styles.dayCellPast,
                      !day && styles.dayCellEmpty,
                    ]}
                    onPress={() => day && !past && handleDayPress(day)}
                    disabled={!day || past}
                  >
                    {(start || end) ? (
                      <LinearGradient
                        colors={[colors.palette.appOrange, colors.palette.appOrangeDark]}
                        style={styles.dayCellSelectedGradient}
                      >
                        <Text style={styles.dayCellTextSelected}>{day}</Text>
                      </LinearGradient>
                    ) : (
                      <Text style={[
                        styles.dayCellText,
                        inRange && styles.dayCellTextInRange,
                        past && styles.dayCellTextPast,
                        !day && { opacity: 0 },
                      ]}>{day ?? " "}</Text>
                    )}
                  </TouchableOpacity>
                )
              })}
            </View>

            {/* Date range summary */}
            {selectedStart && (
              <View style={styles.dateRangeRow}>
                <View style={styles.dateTag}>
                  <Text style={styles.dateTagLabel}>Ngày đi</Text>
                  <Text style={styles.dateTagValue}>{formatDate(selectedStart)}</Text>
                </View>
                {selectedEnd && (
                  <>
                    <Text style={styles.dateArrow}>→</Text>
                    <View style={styles.dateTag}>
                      <Text style={styles.dateTagLabel}>Ngày về</Text>
                      <Text style={styles.dateTagValue}>{formatDate(selectedEnd)}</Text>
                    </View>
                    <View style={styles.numDaysBadge}>
                      <Text style={styles.numDaysText}>{numDays} ngày</Text>
                    </View>
                  </>
                )}
              </View>
            )}
          </View>
        </View>

        {/* Hotel picker */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>🏨 Khách sạn lưu trú</Text>
          <HotelPicker value={hotel} onChange={setHotel} />
        </View>

        {/* Query / intent */}
        <View style={styles.section}>
          <Text style={styles.sectionLabel}>💬 Mong muốn của bạn</Text>
          <View style={[styles.queryBox, queryFocused && styles.queryBoxFocused]}>
            <TextInput
              value={query}
              onChangeText={setQuery}
              placeholder="VD: Tôi muốn thăm lăng tẩm, ăn bún bò, tránh nắng..."
              placeholderTextColor={colors.palette.appMuted}
              style={styles.queryInput}
              multiline
              numberOfLines={3}
              onFocus={() => setQueryFocused(true)}
              onBlur={() => setQueryFocused(false)}
            />
          </View>

          {/* Suggestions */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.suggestionsScroll}>
            {PROMPT_SUGGESTIONS.map((s, i) => (
              <TouchableOpacity key={i} style={styles.suggestionChip} onPress={() => setQuery(s.replace(/^[^\s]+\s/, ""))}>
                <Text style={styles.suggestionText}>{s}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* Generate CTA */}
        <View style={styles.section}>
          <TouchableOpacity
            style={[styles.generateBtn, (!selectedStart || !selectedEnd) && styles.generateBtnDisabled]}
            onPress={handleGenerate}
            disabled={!selectedStart || !selectedEnd}
          >
            <LinearGradient
              colors={selectedStart && selectedEnd
                ? [colors.palette.appOrange, colors.palette.appOrangeDark]
                : ["rgba(255,255,255,0.6)", "rgba(255,255,255,0.4)"]}
              style={styles.generateBtnGradient}
              start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }}
            >
              <Text style={[styles.generateBtnText, (!selectedStart || !selectedEnd) && { color: "rgba(31, 41, 55, 0.3)" }]}>
                {selectedStart && selectedEnd
                  ? `🤖 Tạo Lộ Trình ${numDays} Ngày với AI ✨`
                  : "Chọn ngày đi để tiếp tục"}
              </Text>
            </LinearGradient>
          </TouchableOpacity>
          <Text style={styles.generateHint}>AI sẽ tối ưu theo sức bền, thời tiết và sở thích của bạn</Text>
        </View>
      </ScrollView>
    </View>
  )
}

const CELL_SIZE = (width - spacing.lg * 2 - 32) / 7

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    paddingHorizontal: spacing.lg, paddingBottom: 12,
    borderBottomWidth: 1, borderBottomColor: "rgba(249, 115, 22, 0.1)",
  },
  backBtn: {
    width: 44, height: 44, borderRadius: 14,
    backgroundColor: "rgba(255, 255, 255, 0.65)",
    justifyContent: "center", alignItems: "center",
    borderWidth: 1.5, borderColor: "rgba(255, 255, 255, 0.9)",
    ...Platform.select({
      web: {
        backdropFilter: "blur(15px)",
        WebkitBackdropFilter: "blur(15px)",
      } as any
    }),
  },
  backBtnText: { fontSize: 20, color: colors.palette.appOrangeDark, fontFamily: typography.primary.bold },
  headerTitle: { fontFamily: typography.primary.bold, fontSize: 20, color: colors.palette.appInk },
  scroll: { padding: spacing.lg, gap: 0 },
  section: { marginBottom: spacing.xl },
  sectionLabel: {
    fontFamily: typography.primary.semiBold, fontSize: 15, color: colors.palette.appInk,
    marginBottom: spacing.sm,
  },
  calendarCard: {
    backgroundColor: "rgba(255, 255, 255, 0.58)",
    borderRadius: 20, borderWidth: 1.5, borderColor: "rgba(255, 255, 255, 0.9)",
    padding: spacing.md,
    ...Platform.select({
      web: {
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
      } as any
    }),
    shadowColor: "#1F2937",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.03,
    shadowRadius: 12,
    elevation: 2,
  },
  monthNav: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: spacing.md },
  monthNavBtn: {
    width: 36, height: 36, borderRadius: 10,
    backgroundColor: "rgba(249, 115, 22, 0.06)",
    justifyContent: "center", alignItems: "center",
  },
  monthNavBtnText: { fontSize: 22, color: colors.palette.appOrangeDark, fontFamily: typography.primary.bold },
  monthTitle: { fontFamily: typography.primary.semiBold, fontSize: 16, color: colors.palette.appInk },
  dayHeaders: { flexDirection: "row", marginBottom: spacing.sm },
  dayHeader: {
    width: CELL_SIZE, textAlign: "center",
    fontFamily: typography.primary.semiBold, fontSize: 11,
    color: colors.palette.appMuted, textTransform: "uppercase",
  },
  calGrid: { flexDirection: "row", flexWrap: "wrap" },
  dayCell: {
    width: CELL_SIZE, height: CELL_SIZE,
    justifyContent: "center", alignItems: "center",
    marginBottom: 2,
  },
  dayCellEmpty: { opacity: 0 },
  dayCellPast: { opacity: 0.25 },
  dayCellInRange: { backgroundColor: "rgba(249, 115, 22, 0.08)" },
  dayCellSelected: {},
  dayCellSelectedGradient: {
    width: CELL_SIZE - 4, height: CELL_SIZE - 4,
    borderRadius: (CELL_SIZE - 4) / 2,
    justifyContent: "center", alignItems: "center",
  },
  dayCellText: { fontFamily: typography.primary.medium, fontSize: 14, color: colors.palette.appInk },
  dayCellTextSelected: { fontFamily: typography.primary.bold, fontSize: 14, color: "#FFFFFF" },
  dayCellTextInRange: { color: colors.palette.appOrangeDark },
  dayCellTextPast: { color: "rgba(31, 41, 55, 0.25)" },
  dateRangeRow: {
    flexDirection: "row", alignItems: "center", justifyContent: "center",
    marginTop: spacing.md, gap: spacing.sm, flexWrap: "wrap",
  },
  dateTag: {
    backgroundColor: "rgba(249, 115, 22, 0.08)",
    borderRadius: 12, padding: spacing.sm, alignItems: "center",
    borderWidth: 1, borderColor: "rgba(249, 115, 22, 0.3)",
  },
  dateTagLabel: { fontFamily: typography.primary.normal, fontSize: 10, color: colors.palette.appOrangeDark },
  dateTagValue: { fontFamily: typography.primary.semiBold, fontSize: 14, color: colors.palette.appInk },
  dateArrow: { fontSize: 18, color: colors.palette.appMuted },
  numDaysBadge: {
    backgroundColor: colors.palette.imperialGold + "30",
    borderRadius: 10, paddingHorizontal: 10, paddingVertical: 4,
    borderWidth: 1, borderColor: colors.palette.imperialGold + "60",
  },
  numDaysText: { fontFamily: typography.primary.semiBold, fontSize: 13, color: colors.palette.imperialGold },
  queryBox: {
    backgroundColor: "rgba(255, 255, 255, 0.58)",
    borderRadius: 16, borderWidth: 1.5, borderColor: "rgba(255, 255, 255, 0.9)",
    padding: spacing.md, marginBottom: spacing.sm,
    ...Platform.select({
      web: {
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
      } as any
    }),
    shadowColor: "#1F2937",
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.03,
    shadowRadius: 10,
    elevation: 2,
  },
  queryBoxFocused: { borderColor: colors.palette.appOrange },
  queryInput: {
    fontFamily: typography.primary.normal, fontSize: 14,
    color: colors.palette.appInk, minHeight: 70, textAlignVertical: "top",
  },
  suggestionsScroll: { flexDirection: "row", gap: 8 },
  suggestionChip: {
    backgroundColor: "rgba(255, 255, 255, 0.55)",
    borderRadius: 20, paddingHorizontal: 14, paddingVertical: 8,
    borderWidth: 1.5, borderColor: "rgba(255, 255, 255, 0.9)",
    ...Platform.select({
      web: {
        backdropFilter: "blur(15px)",
        WebkitBackdropFilter: "blur(15px)",
      } as any
    }),
    shadowColor: "#1F2937",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.02,
    shadowRadius: 8,
    elevation: 1,
  },
  suggestionText: { fontFamily: typography.primary.normal, fontSize: 13, color: colors.palette.appInk },
  generateBtn: { borderRadius: 18, overflow: "hidden", marginBottom: spacing.sm },
  generateBtnDisabled: { opacity: 0.7 },
  generateBtnGradient: { paddingVertical: 18, alignItems: "center" },
  generateBtnText: { fontFamily: typography.primary.semiBold, fontSize: 16, color: "#FFFFFF", letterSpacing: 0.3 },
  generateHint: {
    fontFamily: typography.primary.normal, fontSize: 12,
    color: colors.palette.appMuted, textAlign: "center",
  },
})