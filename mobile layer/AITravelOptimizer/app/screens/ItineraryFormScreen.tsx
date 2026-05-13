/**
 * ItineraryFormScreen — Figma "Schedule page".
 * Calendar picker + query input + email toggle + Next step CTA.
 */
import React, { useState } from "react"
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  TouchableOpacity,
  TextInput,
  ScrollView,
  Switch,
  Alert,
} from "react-native"
import { useNavigation } from "@react-navigation/native"
import type { NativeStackNavigationProp } from "@react-navigation/native-stack"

import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { CTAButton } from "@/components/CTAButton"
import { HotelPicker, HotelSelection } from "@/components/HotelPicker"
import { DEFAULT_HOTEL } from "@/constants/presetHotels"
import { AppStackParamList } from "@/navigators/navigationTypes"

type Nav = NativeStackNavigationProp<AppStackParamList>

// Simple inline calendar — weeks grid for current + next month
const DAYS_OF_WEEK = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]

const getDaysInMonth = (year: number, month: number) =>
  new Date(year, month + 1, 0).getDate()

const getFirstDayOfMonth = (year: number, month: number) => {
  const d = new Date(year, month, 1).getDay()
  return d === 0 ? 6 : d - 1 // Monday=0
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
]

export const ItineraryFormScreen: React.FC = () => {
  const navigation = useNavigation<Nav>()
  const today = new Date()
  const [viewMonth, setViewMonth] = useState(today.getMonth())
  const [viewYear, setViewYear] = useState(today.getFullYear())
  const [selectedStart, setSelectedStart] = useState<Date | null>(null)
  const [selectedEnd, setSelectedEnd] = useState<Date | null>(null)
  const [query, setQuery] = useState("")
  const [sendEmail, setSendEmail] = useState(false)
  const [hotel, setHotel] = useState<HotelSelection>({
    name: DEFAULT_HOTEL.name,
    lat: DEFAULT_HOTEL.lat,
    lon: DEFAULT_HOTEL.lon,
  })

  const daysInMonth = getDaysInMonth(viewYear, viewMonth)
  const firstDay = getFirstDayOfMonth(viewYear, viewMonth)

  // Build calendar grid
  const calendarCells: (number | null)[] = [
    ...Array(firstDay).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ]
  while (calendarCells.length % 7 !== 0) calendarCells.push(null)

  const handleDayPress = (day: number) => {
    const d = new Date(viewYear, viewMonth, day)
    if (!selectedStart || (selectedStart && selectedEnd)) {
      setSelectedStart(d)
      setSelectedEnd(null)
    } else {
      if (d < selectedStart) {
        setSelectedEnd(selectedStart)
        setSelectedStart(d)
      } else {
        setSelectedEnd(d)
      }
    }
  }

  const isInRange = (day: number) => {
    if (!selectedStart || !selectedEnd) return false
    const d = new Date(viewYear, viewMonth, day)
    return d > selectedStart && d < selectedEnd
  }

  const isStart = (day: number) =>
    selectedStart?.getFullYear() === viewYear &&
    selectedStart?.getMonth() === viewMonth &&
    selectedStart?.getDate() === day

  const isEnd = (day: number) =>
    selectedEnd?.getFullYear() === viewYear &&
    selectedEnd?.getMonth() === viewMonth &&
    selectedEnd?.getDate() === day

  const numDays =
    selectedStart && selectedEnd
      ? Math.round((selectedEnd.getTime() - selectedStart.getTime()) / 86400000) + 1
      : 1

  const handleNext = () => {
    if (!query.trim()) {
      Alert.alert("Please describe your trip", "What kind of trip are you planning?")
      return
    }
    navigation.navigate("Loading", {
      prompt: query,
      hotelName: hotel.name,
      hotelLat: hotel.lat,
      hotelLon: hotel.lon,
      numDays,
    })
  }

  const prevMonth = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear((y) => y - 1) }
    else setViewMonth((m) => m - 1)
  }

  const nextMonth = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear((y) => y + 1) }
    else setViewMonth((m) => m + 1)
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.palette.figmaWhite} />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {/* ─── Header ── */}
        <View style={styles.headerRow}>
          <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
            <Text style={styles.backArrow}>←</Text>
          </TouchableOpacity>
          <Text style={styles.title}>New Plan</Text>
          <View style={{ width: 40 }} />
        </View>

        {/* ─── Calendar ── */}
        <View style={styles.calendar}>
          {/* Month nav */}
          <View style={styles.monthNav}>
            <TouchableOpacity onPress={prevMonth}>
              <Text style={styles.navArrow}>‹</Text>
            </TouchableOpacity>
            <Text style={styles.monthTitle}>
              {MONTH_NAMES[viewMonth]} {viewYear}
            </Text>
            <TouchableOpacity onPress={nextMonth}>
              <Text style={styles.navArrow}>›</Text>
            </TouchableOpacity>
          </View>

          {/* Day headers */}
          <View style={styles.weekRow}>
            {DAYS_OF_WEEK.map((d) => (
              <Text key={d} style={styles.weekDay}>{d}</Text>
            ))}
          </View>

          {/* Day grid */}
          <View style={styles.grid}>
            {calendarCells.map((day, idx) => {
              if (!day) return <View key={`empty-${idx}`} style={styles.dayCel} />
              const start = isStart(day)
              const end = isEnd(day)
              const range = isInRange(day)
              const isToday =
                day === today.getDate() &&
                viewMonth === today.getMonth() &&
                viewYear === today.getFullYear()

              return (
                <TouchableOpacity
                  key={`d-${day}`}
                  style={[
                    styles.dayCel,
                    (start || end) && styles.dayCelSelected,
                    range && styles.dayCelRange,
                  ]}
                  onPress={() => handleDayPress(day)}
                  activeOpacity={0.7}
                >
                  <Text
                    style={[
                      styles.dayText,
                      (start || end) && styles.dayTextSelected,
                      isToday && styles.dayTextToday,
                    ]}
                  >
                    {day}
                  </Text>
                </TouchableOpacity>
              )
            })}
          </View>
        </View>

        {/* ─── Duration label ── */}
        {selectedStart && (
          <Text style={styles.durationLabel}>
            {selectedEnd
              ? `${numDays} days selected · ${selectedStart.toLocaleDateString()} → ${selectedEnd.toLocaleDateString()}`
              : `Start: ${selectedStart.toLocaleDateString()} (select end date)`}
          </Text>
        )}

        {/* ─── Hotel Picker ── */}
        <HotelPicker value={hotel} onChange={setHotel} />

        {/* ─── Query Input ── */}
        <View style={styles.inputBlock}>
          <Text style={styles.inputLabel}>Query journey</Text>
          <TextInput
            style={styles.textArea}
            value={query}
            onChangeText={setQuery}
            placeholder="e.g. 3 days in Huế, cultural sites and local food..."
            placeholderTextColor={colors.palette.figmaGrayMedium}
            multiline
            numberOfLines={3}
          />
        </View>

        {/* ─── Email toggle ── */}
        <View style={styles.toggleRow}>
          <Text style={styles.toggleLabel}>Send itinerary to my email</Text>
          <Switch
            value={sendEmail}
            onValueChange={setSendEmail}
            trackColor={{ false: colors.palette.figmaGrayLight, true: colors.palette.figmaBlue }}
            thumbColor={colors.palette.figmaWhite}
          />
        </View>

        {/* ─── CTA ── */}
        <CTAButton
          label="Next step →"
          onPress={handleNext}
          style={styles.cta}
          testID="next-step-btn"
        />

        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.palette.figmaWhite },
  scroll: { paddingHorizontal: spacing.lg },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingTop: spacing.md,
    paddingBottom: spacing.lg,
  },
  backBtn: { width: 40, height: 40, justifyContent: "center" },
  backArrow: { fontSize: 22, color: colors.palette.figmaBlack },
  title: {
    fontFamily: typography.primary.bold,
    fontSize: 20,
    color: colors.palette.figmaBlack,
  },
  calendar: {
    backgroundColor: colors.palette.figmaOffWhite,
    borderRadius: 20,
    padding: spacing.md,
    marginBottom: spacing.md,
  },
  monthNav: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.md,
  },
  navArrow: {
    fontSize: 28,
    color: colors.palette.figmaBlack,
    paddingHorizontal: spacing.sm,
  },
  monthTitle: {
    fontFamily: typography.primary.semiBold,
    fontSize: 16,
    color: colors.palette.figmaBlack,
  },
  weekRow: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginBottom: spacing.xs,
  },
  weekDay: {
    width: 36,
    textAlign: "center",
    fontFamily: typography.primary.medium,
    fontSize: 12,
    color: colors.palette.figmaGrayMedium,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
  },
  dayCel: {
    width: "14.28%",
    aspectRatio: 1,
    justifyContent: "center",
    alignItems: "center",
    borderRadius: 20,
  },
  dayCelSelected: {
    backgroundColor: colors.palette.figmaPrimaryBlack,
  },
  dayCelRange: {
    backgroundColor: colors.palette.figmaGrayLight,
  },
  dayText: {
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.figmaGrayDark,
  },
  dayTextSelected: {
    color: colors.palette.figmaWhite,
    fontFamily: typography.primary.semiBold,
  },
  dayTextToday: {
    color: colors.palette.figmaBlue,
    fontFamily: typography.primary.bold,
  },
  durationLabel: {
    fontFamily: typography.primary.medium,
    fontSize: 13,
    color: colors.palette.figmaBlue,
    textAlign: "center",
    marginBottom: spacing.md,
  },
  inputBlock: {
    marginBottom: spacing.md,
  },
  inputLabel: {
    fontFamily: typography.primary.semiBold,
    fontSize: 15,
    color: colors.palette.figmaBlack,
    marginBottom: spacing.xs,
  },
  textArea: {
    backgroundColor: colors.palette.figmaOffWhite,
    borderRadius: 15,
    padding: spacing.md,
    fontFamily: typography.primary.normal,
    fontSize: 14,
    color: colors.palette.figmaGrayDark,
    minHeight: 80,
    textAlignVertical: "top",
  },
  toggleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.lg,
    backgroundColor: colors.palette.figmaOffWhite,
    borderRadius: 15,
    padding: spacing.md,
  },
  toggleLabel: {
    fontFamily: typography.primary.medium,
    fontSize: 14,
    color: colors.palette.figmaGrayDark,
  },
  cta: {},
})
