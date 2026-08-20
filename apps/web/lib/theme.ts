/**
 * Shared dark-theme color tokens. Every component imports from here
 * instead of inline hex literals, so the whole app switches together —
 * a real trading-platform look (Binance/TradingView-style dark palette),
 * not a mix of restyled and un-restyled panels.
 */
export const THEME = {
  bg: "#0b0e11",
  panelBg: "#161a1e",
  panelBgAlt: "#1e2329",
  border: "#2a2e39",
  textPrimary: "#eaecef",
  textSecondary: "#848e9c",
  textMuted: "#5e6673",
  accent: "#f0b90b",
  accentText: "#0b0e11",
  positive: "#0ecb81",
  negative: "#f6465d",
  link: "#f0b90b",
} as const;

export const FONT_FAMILY =
  "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";
