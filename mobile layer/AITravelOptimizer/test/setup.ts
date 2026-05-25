// we always make sure 'react-native' gets included first
// eslint-disable-next-line no-restricted-imports
import * as ReactNative from "react-native"

import mockFile from "./mockFile"

// libraries to mock
jest.doMock("react-native", () => {
  // Extend ReactNative
  return Object.setPrototypeOf(
    {
      Image: {
        ...ReactNative.Image,
        resolveAssetSource: jest.fn((_source) => mockFile), // eslint-disable-line @typescript-eslint/no-unused-vars
        getSize: jest.fn(
          (
            uri: string, // eslint-disable-line @typescript-eslint/no-unused-vars
            success: (width: number, height: number) => void,
            failure?: (_error: any) => void, // eslint-disable-line @typescript-eslint/no-unused-vars
          ) => success(100, 100),
        ),
      },
    },
    ReactNative,
  )
})

jest.mock("i18next", () => ({
  currentLocale: "en",
  t: (key: string, params: Record<string, string>) => {
    return `${key} ${JSON.stringify(params)}`
  },
  translate: (key: string, params: Record<string, string>) => {
    return `${key} ${JSON.stringify(params)}`
  },
}))

jest.mock("expo-localization", () => ({
  ...jest.requireActual("expo-localization"),
  getLocales: () => [{ languageTag: "en-US", textDirection: "ltr" }],
}))

jest.mock("../app/i18n/index.ts", () => ({
  i18n: {
    isInitialized: true,
    language: "en",
    t: (key: string, params: Record<string, string>) => {
      return `${key} ${JSON.stringify(params)}`
    },
    numberToCurrency: jest.fn(),
  },
}))

declare const tron // eslint-disable-line @typescript-eslint/no-unused-vars

declare global {
  let __TEST__: boolean
}

jest.mock("react-native-safe-area-context", () => {
  return {
    SafeAreaProvider: ({ children }) => children,
    SafeAreaConsumer: ({ children }) => children({ top: 0, left: 0, right: 0, bottom: 0 }),
    SafeAreaView: ({ children }) => children,
    useSafeAreaInsets: () => ({ top: 0, left: 0, right: 0, bottom: 0 }),
    useSafeAreaFrame: () => ({ x: 0, y: 0, width: 0, height: 0 }),
  }
})

jest.mock("react-native-worklets", () => {
  return {
    createSerializable: (x: any) => x,
    makeShareable: (x: any) => x,
    isWorkletFunction: () => true,
    RuntimeKind: {
      ReactNative: "ReactNative",
      UI: "UI",
    },
    scheduleOnUI: (fn: any) => fn,
    serializableMappingCache: new Map(),
    Worklets: {
      createRunOnJS: (fn: any) => fn,
      createRunOnUI: (fn: any) => fn,
    },
  }
})

jest.mock("@rnmapbox/maps", () => {
  const React = require("react")
  const MockComponent = (name: string) => {
    const Component = (props: any) => React.createElement(name, props, props.children)
    Component.displayName = name
    return Component
  }
  return {
    __esModule: true,
    default: {
      MapView: MockComponent("MapView"),
      Camera: MockComponent("Camera"),
      UserLocation: MockComponent("UserLocation"),
      PointAnnotation: MockComponent("PointAnnotation"),
      ShapeSource: MockComponent("ShapeSource"),
      LineLayer: MockComponent("LineLayer"),
      CircleLayer: MockComponent("CircleLayer"),
      SymbolLayer: MockComponent("SymbolLayer"),
      FillLayer: MockComponent("FillLayer"),
      Images: MockComponent("Images"),
      StyleSheet: {
        create: jest.fn(),
      },
      setTelemetryEnabled: jest.fn(),
    },
    MapView: MockComponent("MapView"),
    Camera: MockComponent("Camera"),
    UserLocation: MockComponent("UserLocation"),
    PointAnnotation: MockComponent("PointAnnotation"),
    ShapeSource: MockComponent("ShapeSource"),
    LineLayer: MockComponent("LineLayer"),
    CircleLayer: MockComponent("CircleLayer"),
    SymbolLayer: MockComponent("SymbolLayer"),
    FillLayer: MockComponent("FillLayer"),
    Images: MockComponent("Images"),
  }
})

jest.mock("react-native-reanimated", () => {
  const reanimated = require("react-native-reanimated/mock")

  const createMockSharedValue = (init: any) => {
    const valueObj = { value: init }
    return new Proxy(valueObj, {
      get(target, prop) {
        if (prop === "value") {
          return target.value
        }
        if (prop === "get") {
          return () => target.value
        }
        if (prop === "set") {
          return (newValue: any) => {
            if (typeof newValue === "function") {
              target.value = newValue(target.value)
            } else {
              target.value = newValue
            }
          };
        }
        if (prop === "modify") {
          return (modifier: any) => {
            const result = modifier(target.value)
            if (result !== undefined) {
              target.value = result
            }
          };
        }
        return (target as any)[prop]
      },
      set(target, prop, newValue) {
        if (prop === "value") {
          target.value = newValue
          return true
        }
        return false
      },
    })
  }

  return {
    ...reanimated,
    makeMutable: createMockSharedValue,
    useSharedValue: createMockSharedValue,
    useReducedMotion: () => false,
  }
})

