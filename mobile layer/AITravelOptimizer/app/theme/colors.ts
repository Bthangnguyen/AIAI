const palette = {
  neutral100: "#FFFFFF",
  neutral200: "#F4F2F1",
  neutral300: "#D7CEC9",
  neutral400: "#B6ACA6",
  neutral500: "#978F8A",
  neutral600: "#564E4A",
  neutral700: "#3C3836",
  neutral800: "#191015",
  neutral900: "#000000",

  primary100: "#F4E0D9",
  primary200: "#E8C1B4",
  primary300: "#DDA28E",
  primary400: "#D28468",
  primary500: "#C76542",
  primary600: "#A54F31",

  secondary100: "#DCDDE9",
  secondary200: "#BCC0D6",
  secondary300: "#9196B9",
  secondary400: "#626894",
  secondary500: "#41476E",

  accent100: "#FFEED4",
  accent200: "#FFE1B2",
  accent300: "#FDD495",
  accent400: "#FBC878",
  accent500: "#FFBB50",

  angry100: "#F2D6CD",
  angry500: "#C03403",

  overlay20: "rgba(25, 16, 21, 0.2)",
  overlay50: "rgba(25, 16, 21, 0.5)",

  // ─── Figma Travel App UI Kit Tokens ───────────────────────────
  // Extracted from Figma file N0odA22MkrdhMcXxnMIivY
  // Primary actions & text
  figmaPrimaryBlack: "#0D0D0D",    // CTA buttons, main headings
  figmaPrimary: "#0373F3",          // Legacy blue CTA (keep for compat)
  figmaWhite: "#FFFFFF",            // Screen background, cards
  figmaOffWhite: "#F5F5F5",         // Section backgrounds
  figmaBlack: "#0D0D0D",            // Primary text
  figmaGrayDark: "#272727",         // Body text
  figmaGrayMedium: "#858585",       // Subtitle / secondary text
  figmaGrayLight: "#E7E7E7",        // Borders, dividers
  figmaSurface: "#F5F5F5",          // Card/section backgrounds
  figmaInactive: "#858585",         // Inactive icons/tabs
  figmaDisabled: "#BCBCBC",         // Disabled state
  figmaPlaceholder: "#858585",      // Placeholder text

  // Accent / gradient
  figmaTeal: "#68D6CA",             // Gradient start, tag backgrounds
  figmaBlue: "#2E60F4",             // Gradient end, links, active
  figmaOrange: "#FF6B35",           // Weather alerts, warnings
  appOrange: "#F97316",
  appOrangeDark: "#EA580C",
  appOrangeSoft: "#FFF3E8",
  appOrangePale: "#FFE7D1",
  appCream: "#FFFBF7",
  appInk: "#1F2937",
  appMuted: "#6B7280",
  appLine: "#FED7AA",

  // Status
  figmaSuccess: "#4CAF50",
  figmaError: "#E74C3C",
  figmaStarYellow: "#FFD700",       // Rating stars

  // Glass effects (Glassmorphism — retained for HomeScreen hero)
  glassWhite10: "rgba(255, 255, 255, 0.1)",
  glassWhite70: "rgba(255, 255, 255, 0.7)",
  glassWhite80: "rgba(255, 255, 255, 0.8)",

  // Legacy star rating gradient endpoints
  starGold: "#F7B502",
  starOrange: "#E88405",

  // ─── Modern Royal Hue Palette (Approved) ──────────────────────
  royalPurple: "#6C2A7B",
  royalPurpleLight: "#8E3E9F",
  imperialGold: "#FFB800",
  imperialGoldLight: "#FFD066",
  jadeGreen: "#00A86B",
  jadeGreenLight: "#33C48F",
  sunsetOrange: "#FF6B6B",
  sunsetOrangeLight: "#FF8C8C",
  deepSlate: "#0B0F19",
  glassWhite: "rgba(255, 255, 255, 0.08)",
  glassBorder: "rgba(255, 255, 255, 0.15)",
} as const

export const colors = {
  /**
   * The palette is available to use, but prefer using the name.
   * This is only included for rare, one-off cases. Try to use
   * semantic names as much as possible.
   */
  palette,
  /**
   * A helper for making something see-thru.
   */
  transparent: "rgba(0, 0, 0, 0)",

  // ─── Semantic Colors (Figma Travel App UI Kit) ─────────────────
  /** Primary text — near black #0D0D0D */
  text: palette.figmaBlack,
  /** Secondary/dim text — #272727 */
  textDim: palette.figmaGrayDark,
  /** Muted/placeholder text — #858585 */
  textMuted: palette.figmaGrayMedium,
  /** Screen background — white */
  background: palette.appCream,
  /** Section/card background — off-white */
  backgroundSecondary: palette.figmaWhite,
  /** Default border/divider */
  border: palette.figmaGrayLight,
  /** Primary CTA — Royal Purple */
  tint: palette.appOrange,
  /** Link / accent blue */
  link: palette.appOrangeDark,
  /** Gradient start (teal) */
  gradientStart: palette.appOrange,
  /** Gradient end (blue) */
  gradientEnd: palette.appOrangeDark,
  /** Inactive icons / tabs */
  tintInactive: palette.figmaInactive,
  /** Dividers and separators */
  separator: palette.figmaGrayLight,
  /** Warning / alert orange */
  warning: palette.sunsetOrange,
  /** Success green */
  success: palette.jadeGreen,
  /** Rating stars */
  star: palette.figmaStarYellow,
  /** Error messages */
  error: palette.figmaError,
  /** Error background */
  errorBackground: palette.angry100,

  // ─── Glass Effects (retained for MapTimeline hero) ─────────────
  glassWhite10: palette.glassWhite10,
  glassWhite70: palette.glassWhite70,
  glassWhite80: palette.glassWhite80,

  // ─── Semantic Colors (Modern Royal Hue) ────────────────────────
  primaryRoyal: palette.appOrange,
  accentGold: palette.appOrangeDark,
  jadeGreen: palette.jadeGreen,
  sunsetOrange: palette.sunsetOrange,
  deepSlate: palette.deepSlate,
  glassWhite: palette.glassWhite,
  glassBorder: palette.glassBorder,
} as const
