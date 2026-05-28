/**
 * The app navigator (formerly "AppNavigator" and "MainNavigator") is used for the primary
 * navigation flows of your app.
 * Generally speaking, it will contain an auth flow (registration, login, forgot password)
 * and a "main" flow which the user will use once logged in.
 */
import { NavigationContainer } from "@react-navigation/native"
import { createNativeStackNavigator } from "@react-navigation/native-stack"

import Config from "@/config"
import { useAuth } from "@/context/AuthContext"
import { ErrorBoundary } from "@/screens/ErrorScreen/ErrorBoundary"
import { LoadingScreen } from "@/screens/LoadingScreen"
import { LoginScreen } from "@/screens/LoginScreen"
import { RegisterScreen } from "@/screens/RegisterScreen"
import { MapTimelineScreen } from "@/screens/MapTimelineScreen"
import { OnboardingScreen } from "@/screens/OnboardingScreen"
import { WelcomeScreen } from "@/screens/WelcomeScreen"
import { ItineraryFormScreen } from "@/screens/ItineraryFormScreen"
import { POIDetailScreen } from "@/screens/POIDetailScreen"
import { SettingsScreen } from "@/screens/SettingsScreen"
import { useAppTheme } from "@/theme/context"

import { DemoNavigator } from "./DemoNavigator"
import { MainTabNavigator } from "./MainTabNavigator"
import type { AppStackParamList, NavigationProps } from "./navigationTypes"
import { navigationRef, useBackButtonHandler } from "./navigationUtilities"

/**
 * This is a list of all the route names that will exit the app if the back button
 * is pressed while in that screen. Only affects Android.
 */
const exitRoutes = Config.exitRoutes

// Documentation: https://reactnavigation.org/docs/stack-navigator/
const Stack = createNativeStackNavigator<AppStackParamList>()

const AppStack = () => {
  const { isAuthenticated } = useAuth()

  const {
    theme: { colors },
  } = useAppTheme()

  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        navigationBarColor: colors.background,
        contentStyle: {
          backgroundColor: colors.background,
        },
      }}
      initialRouteName={isAuthenticated ? "MainTabs" : "Onboarding"}
    >
      {isAuthenticated ? (
        <>
          {/* â”€â”€â”€ Main Tab Navigator (Home / Wallet / Guide / Profile) */}
          <Stack.Screen name="MainTabs" component={MainTabNavigator} />

          {/* â”€â”€â”€ Push Screens (accessible from any tab) */}
          <Stack.Screen name="Loading" component={LoadingScreen} />
          <Stack.Screen name="MapTimeline" component={MapTimelineScreen} />
          <Stack.Screen name="POIDetail" component={POIDetailScreen} />
          <Stack.Screen name="ItineraryForm" component={ItineraryFormScreen} />
          <Stack.Screen name="Settings" component={SettingsScreen} />

          {/* Legacy Ignite screens (kept for demo) */}
          <Stack.Screen name="Welcome" component={WelcomeScreen} />
          <Stack.Screen name="Demo" component={DemoNavigator} />
        </>
      ) : (
        <>
          <Stack.Screen name="Onboarding" component={OnboardingScreen} />
          <Stack.Screen name="Login" component={LoginScreen} />
          <Stack.Screen name="Register" component={RegisterScreen} />
          {/** ðŸ”¥ Your screens go here */}
          {/* IGNITE_GENERATOR_ANCHOR_APP_STACK_SCREENS */}
        </>
      )}
    </Stack.Navigator>
  )
}

export const AppNavigator = (props: NavigationProps) => {
  const { navigationTheme } = useAppTheme()

  useBackButtonHandler((routeName) => exitRoutes.includes(routeName))

  return (
    <NavigationContainer ref={navigationRef} theme={navigationTheme} {...props}>
      <ErrorBoundary catchErrors={Config.catchErrors}>
        <AppStack />
      </ErrorBoundary>
    </NavigationContainer>
  )
}
