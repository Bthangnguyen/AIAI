/**
 * TripHistoryScreen — List of past and upcoming trips.
 * Matches plan: card list with destination image, name, date, POI count.
 */
import React from "react"
import {
  View,
  Text,
  ScrollView,
  Image,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  StatusBar,
} from "react-native"
import { useNavigation } from "@react-navigation/native"
import type { NativeStackNavigationProp } from "@react-navigation/native-stack"

import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"
import { MOCK_TRIP_HISTORY, MockTripHistory } from "@/constants/mockUser"
import { MockTripService } from "@/services/mock/mockTripService"
import { AppStackParamList } from "@/navigators/navigationTypes"

type Nav = NativeStackNavigationProp<AppStackParamList>

const STATUS_COLORS = {
  completed: colors.palette.figmaSuccess,
  upcoming: colors.palette.figmaBlue,
  draft: colors.palette.figmaGrayMedium,
}

const STATUS_LABELS = {
  completed: "Completed",
  upcoming: "Upcoming",
  draft: "Draft",
}

export const TripHistoryScreen: React.FC = () => {
  const navigation = useNavigation<Nav>()

  const handleTripPress = (_trip: MockTripHistory) => {
    // Open the mock itinerary for this trip
    navigation.navigate("MapTimeline", {
      itinerary: MockTripService.getMockItinerary(),
    })
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar barStyle="dark-content" backgroundColor={colors.palette.figmaWhite} />
      <View style={styles.header}>
        <Text style={styles.title}>My Trips</Text>
        <Text style={styles.subtitle}>{MOCK_TRIP_HISTORY.length} trips recorded</Text>
      </View>
      <ScrollView
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
      >
        {MOCK_TRIP_HISTORY.map((trip) => (
          <TouchableOpacity
            key={trip.id}
            style={styles.card}
            onPress={() => handleTripPress(trip)}
            activeOpacity={0.85}
            testID={`trip-card-${trip.id}`}
          >
            <Image source={{ uri: trip.photoUrl }} style={styles.cardImage} resizeMode="cover" />
            <View style={styles.cardBody}>
              <View style={styles.cardTop}>
                <Text style={styles.destination}>{trip.destination}</Text>
                <View
                  style={[
                    styles.statusBadge,
                    { backgroundColor: STATUS_COLORS[trip.status] + "22" },
                  ]}
                >
                  <Text style={[styles.statusText, { color: STATUS_COLORS[trip.status] }]}>
                    {STATUS_LABELS[trip.status]}
                  </Text>
                </View>
              </View>
              <Text style={styles.dates}>
                {trip.startDate} → {trip.endDate}
              </Text>
              <Text style={styles.meta}>
                {trip.totalDays} days
                {trip.poiCount > 0 ? ` · ${trip.poiCount} places` : ""}
              </Text>
            </View>
          </TouchableOpacity>
        ))}
        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: {
    flex: 1,
    backgroundColor: colors.palette.figmaWhite,
  },
  header: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.md,
    paddingBottom: spacing.md,
  },
  title: {
    fontFamily: typography.primary.bold,
    fontSize: 24,
    color: colors.palette.figmaBlack,
  },
  subtitle: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: colors.palette.figmaGrayMedium,
    marginTop: 2,
  },
  listContent: {
    paddingHorizontal: spacing.lg,
    gap: spacing.md,
  },
  card: {
    borderRadius: 15,
    overflow: "hidden",
    backgroundColor: colors.palette.figmaWhite,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 8,
    elevation: 3,
  },
  cardImage: {
    width: "100%",
    height: 160,
  },
  cardBody: {
    padding: spacing.md,
  },
  cardTop: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.xxs,
  },
  destination: {
    fontFamily: typography.primary.semiBold,
    fontSize: 18,
    color: colors.palette.figmaBlack,
  },
  statusBadge: {
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    borderRadius: 20,
  },
  statusText: {
    fontFamily: typography.primary.semiBold,
    fontSize: 11,
  },
  dates: {
    fontFamily: typography.primary.normal,
    fontSize: 13,
    color: colors.palette.figmaGrayMedium,
    marginBottom: 2,
  },
  meta: {
    fontFamily: typography.primary.medium,
    fontSize: 12,
    color: colors.palette.figmaGrayDark,
  },
})
