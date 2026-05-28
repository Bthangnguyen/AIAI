import React from "react"
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs"
import { View, Text, StyleSheet, Platform } from "react-native"
import { useSafeAreaInsets } from "react-native-safe-area-context"

import { AppIcon, AppIconName } from "@/components/AppIcon"
import { MainTabParamList } from "@/navigators/navigationTypes"
import { ActiveTripScreen } from "@/screens/ActiveTripScreen"
import { HomeScreen } from "@/screens/HomeScreen"
import { ProfileScreen } from "@/screens/ProfileScreen"
import { TripHistoryScreen } from "@/screens/TripHistoryScreen"
import { colors } from "@/theme/colors"
import { spacing } from "@/theme/spacing"
import { typography } from "@/theme/typography"

const Tab = createBottomTabNavigator<MainTabParamList>()

interface TabIconProps {
  icon: AppIconName
  label: string
  focused: boolean
}

const TabIcon: React.FC<TabIconProps> = ({ icon, label, focused }) => (
  <View style={[tabStyles.iconContainer, focused && tabStyles.iconContainerFocused]}>
    <AppIcon name={icon} size={21} color={focused ? colors.palette.appOrangeDark : colors.palette.appMuted} />
    <Text style={[tabStyles.label, focused && tabStyles.labelFocused]}>{label}</Text>
  </View>
)

export const MainTabNavigator: React.FC = () => {
  const insets = useSafeAreaInsets()
  const safeBottom = insets.bottom > 0 ? insets.bottom : 10
  const dynamicTabBarStyle = {
    ...styles.tabBar,
    height: Platform.OS === "ios" ? 54 + safeBottom : 64 + safeBottom,
    paddingBottom: Platform.OS === "ios" ? safeBottom : safeBottom + 2,
  }

  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: dynamicTabBarStyle,
        tabBarShowLabel: false,
        tabBarActiveTintColor: colors.palette.appOrangeDark,
        tabBarInactiveTintColor: colors.palette.appMuted,
        tabBarItemStyle: { paddingVertical: 4 },
        tabBarBackground: () => <View style={styles.tabBarBackground} />,
      }}
    >
      <Tab.Screen
        name="Explore"
        component={HomeScreen as any}
        options={{
          tabBarIcon: ({ focused }) => <TabIcon icon="home" label="Trang chủ" focused={focused} />,
        }}
      />
      <Tab.Screen
        name="MyTrip"
        component={ActiveTripScreen as any}
        options={{
          tabBarIcon: ({ focused }) => <TabIcon icon="route" label="Lộ trình" focused={focused} />,
        }}
      />
      <Tab.Screen
        name="History"
        component={TripHistoryScreen}
        options={{
          tabBarIcon: ({ focused }) => <TabIcon icon="history" label="Lịch sử" focused={focused} />,
        }}
      />
      <Tab.Screen
        name="Profile"
        component={ProfileScreen}
        options={{
          tabBarIcon: ({ focused }) => <TabIcon icon="profile" label="Tài khoản" focused={focused} />,
        }}
      />
    </Tab.Navigator>
  )
}

const tabStyles = StyleSheet.create({
  iconContainer: {
    alignItems: "center",
    justifyContent: "center",
    gap: 3,
    minWidth: 62,
    paddingVertical: 5,
    borderRadius: 14,
  },
  iconContainerFocused: {
    backgroundColor: "rgba(249, 115, 22, 0.08)",
  },
  label: {
    fontFamily: typography.primary.medium,
    fontSize: 10,
    color: colors.palette.appMuted,
  },
  labelFocused: {
    fontFamily: typography.primary.semiBold,
    color: colors.palette.appOrangeDark,
  },
})

const styles = StyleSheet.create({
  tabBar: {
    backgroundColor: "rgba(255, 255, 255, 0.94)",
    borderTopWidth: 1,
    borderTopColor: "rgba(249, 115, 22, 0.12)",
    paddingTop: spacing.xs,
    shadowColor: colors.palette.appOrangeDark,
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.06,
    shadowRadius: 10,
    elevation: 8,
  },
  tabBarBackground: {
    flex: 1,
    backgroundColor: "rgba(255, 255, 255, 0.94)",
  },
})

