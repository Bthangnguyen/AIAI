/**
 * MainTabNavigator - Dark Royal Hue Tab Bar
 * Design: Glassmorphism dark + Royal Purple accent
 */
import React from "react"
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs"
import { View, Text, StyleSheet, Platform } from "react-native"

import { MainTabParamList } from "@/navigators/navigationTypes"
import { HomeScreen } from "@/screens/HomeScreen"
import { TripHistoryScreen } from "@/screens/TripHistoryScreen"
import { ProfileScreen } from "@/screens/ProfileScreen"
import { TripSummaryPlaceholder } from "@/screens/TripSummaryPlaceholder"
import { ActiveTripScreen } from "@/screens/ActiveTripScreen"
import { colors } from "@/theme/colors"
import { typography } from "@/theme/typography"
import { spacing } from "@/theme/spacing"

const Tab = createBottomTabNavigator<MainTabParamList>()

interface TabIconProps {
  icon: string
  label: string
  focused: boolean
}

const TabIcon: React.FC<TabIconProps> = ({ icon, label, focused }) => (
  <View style={tabStyles.iconContainer}>
    <Text style={[tabStyles.icon]}>{icon}</Text>
    <Text style={[tabStyles.label, focused && tabStyles.labelFocused]}>{label}</Text>
    {focused && <View style={tabStyles.activeDot} />}
  </View>
)

const tabStyles = StyleSheet.create({
  iconContainer: {
    alignItems: "center",
    paddingTop: 4,
    position: "relative",
  },
  icon: {
    fontSize: 22,
    marginBottom: 2,
  },
  label: {
    fontFamily: typography.primary.normal,
    fontSize: 10,
    color: "rgba(255,255,255,0.4)",
    letterSpacing: 0.2,
  },
  labelFocused: {
    fontFamily: typography.primary.semiBold,
    color: colors.palette.imperialGold,
  },
  activeDot: {
    position: "absolute",
    bottom: -6,
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.palette.imperialGold,
  },
})

export const MainTabNavigator: React.FC = () => {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: styles.tabBar,
        tabBarShowLabel: false,
        tabBarActiveTintColor: colors.palette.imperialGold,
        tabBarInactiveTintColor: "rgba(255,255,255,0.3)",
        tabBarItemStyle: { paddingVertical: 4 },
        tabBarBackground: () => (
          <View style={styles.tabBarBackground} />
        ),
      }}
    >
      <Tab.Screen
        name="Explore"
        component={HomeScreen as any}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon icon="🏠" label="Trang chủ" focused={focused} />
          ),
        }}
      />
      <Tab.Screen
        name="MyTrip"
        component={ActiveTripScreen as any}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon icon="🗺️" label="Lộ trình" focused={focused} />
          ),
        }}
      />
      <Tab.Screen
        name="History"
        component={TripHistoryScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon icon="📖" label="Lịch sử" focused={focused} />
          ),
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon icon="👤" label="Tài khoản" focused={focused} />
          ),
        }}
      />
    </Tab.Navigator>
  )
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: "rgba(11,15,25,0.95)",
    borderTopWidth: 1,
    borderTopColor: "rgba(255,255,255,0.08)",
    height: Platform.OS === "ios" ? 84 : 64,
    paddingBottom: Platform.OS === "ios" ? 24 : 8,
    paddingTop: spacing.xs,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 20,
  },
  tabBarBackground: {
    flex: 1,
    backgroundColor: "rgba(11,15,25,0.97)",
  },
})