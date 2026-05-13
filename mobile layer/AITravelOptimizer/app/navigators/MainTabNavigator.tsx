/**
 * MainTabNavigator — Bottom Tab Navigator matching Figma tab bar.
 * 4 tabs: Home (Explore) / Wallet (MyTrip) / Guide (History) / Chart (Profile)
 *
 * Design: white bg, rounded top corners, shadow, custom tab icons.
 */
import React from "react"
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs"
import { View, Text, StyleSheet, Platform } from "react-native"

import { MainTabParamList } from "@/navigators/navigationTypes"
import { ExploreScreen } from "@/screens/ExploreScreen"
import { TripHistoryScreen } from "@/screens/TripHistoryScreen"
import { ProfileScreen } from "@/screens/ProfileScreen"
import { TripSummaryPlaceholder } from "@/screens/TripSummaryPlaceholder"
import { colors } from "@/theme/colors"
import { typography } from "@/theme/typography"
import { spacing } from "@/theme/spacing"

const Tab = createBottomTabNavigator<MainTabParamList>()

// ─── Custom Tab Icon ──────────────────────────────────────────────────────────
interface TabIconProps {
  icon: string
  label: string
  focused: boolean
}

const TabIcon: React.FC<TabIconProps> = ({ icon, label, focused }) => (
  <View style={tabStyles.iconContainer}>
    <Text style={[tabStyles.icon, focused && tabStyles.iconFocused]}>{icon}</Text>
    <Text style={[tabStyles.label, focused && tabStyles.labelFocused]}>{label}</Text>
  </View>
)

const tabStyles = StyleSheet.create({
  iconContainer: {
    alignItems: "center",
    paddingTop: spacing.xxs,
  },
  icon: {
    fontSize: 22,
    marginBottom: 2,
  },
  iconFocused: {
    // Emoji gets a slight scale hint via label weight below
  },
  label: {
    fontFamily: typography.primary.normal,
    fontSize: 10,
    color: colors.palette.figmaGrayMedium,
    letterSpacing: 0.2,
  },
  labelFocused: {
    fontFamily: typography.primary.semiBold,
    color: colors.palette.figmaPrimaryBlack,
  },
})

// ─── Navigator ────────────────────────────────────────────────────────────────
export const MainTabNavigator: React.FC = () => {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: styles.tabBar,
        tabBarShowLabel: false,
        tabBarActiveTintColor: colors.palette.figmaPrimaryBlack,
        tabBarInactiveTintColor: colors.palette.figmaGrayMedium,
      }}
    >
      <Tab.Screen
        name="Explore"
        component={ExploreScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon icon="🏠" label="Home" focused={focused} />
          ),
        }}
      />
      <Tab.Screen
        name="MyTrip"
        component={TripSummaryPlaceholder}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon icon="💼" label="Wallet" focused={focused} />
          ),
        }}
      />
      <Tab.Screen
        name="History"
        component={TripHistoryScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon icon="📖" label="Guide" focused={focused} />
          ),
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          tabBarIcon: ({ focused }) => (
            <TabIcon icon="👤" label="Profile" focused={focused} />
          ),
        }}
      />
    </Tab.Navigator>
  )
}

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: colors.palette.figmaWhite,
    borderTopWidth: 0,
    height: Platform.OS === "ios" ? 84 : 64,
    paddingBottom: Platform.OS === "ios" ? 24 : 8,
    paddingTop: spacing.xs,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 8,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
  },
})
