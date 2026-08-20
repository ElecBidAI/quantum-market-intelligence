export type Locale = "en" | "es";

/**
 * UI chrome translations only — labels, buttons, page copy. The broker
 * narrative text itself is generated server-side in both languages
 * (services/ai-council/src/ai_council/narrator.py) and selected via
 * `CouncilNarrative.narrativeEn`/`narrativeEs`, not translated here.
 */
const STRINGS = {
  en: {
    "page.description":
      "Live BTC/ETH spot prices from Binance only. No strategies, risk decisions, or execution capability exist yet.",
    "page.docsIntro": "See",
    "page.docsOutro": "for the target architecture and development phases.",

    "dashboard.heading": "Live prices",
    "dashboard.feedIntroPrefix": "Feed: /api (proxied) — connection",
    "dashboard.feedIntroSuffix":
      "Prices below are only ever what the exchange actually sent; a blank row means no data has arrived yet.",
    "dashboard.status.connecting": "connecting",
    "dashboard.status.connected": "connected",
    "dashboard.status.error": "error",
    "dashboard.colSymbol": "Symbol",
    "dashboard.colExchange": "Exchange",
    "dashboard.colPrice": "Last price",
    "dashboard.colUpdate": "Last update (UTC)",
    "dashboard.colLive": "Live",
    "dashboard.live": "LIVE",
    "dashboard.stale": "stale/no data",

    "authGate.checking": "Checking session…",

    "narrative.heading": "Broker narrative",
    "narrative.framing":
      "This note explains a rule-based analysis already produced by risk_engine and ai_council — nothing on this page places, sizes, or executes a trade.",
    "narrative.loading": "Loading…",
    "narrative.error": "Could not load a narrative right now.",
    "narrative.empty": "No narrative has been generated yet for these symbols.",
    "narrative.regimeLabel": "regime",
    "narrative.confidenceSuffix": "confidence",
    "narrative.strategyLabel": "strategy",
    "narrative.decisionLabel": "risk decision",
    "narrative.councilLabel": "council",
    "narrative.generatedAtPrefix": "Generated from data as of",
    "narrative.generatedAtSuffix": "(UTC).",

    "login.heading": "Log in",
    "login.email": "Email",
    "login.password": "Password",
    "login.submit": "Log in",
    "login.submitting": "Logging in…",
    "login.error": "Invalid email or password.",
    "login.noAccount": "No account?",
    "login.registerLink": "Register",

    "register.heading": "Create your organization",
    "register.orgName": "Organization name",
    "register.email": "Email",
    "register.password": "Password",
    "register.submit": "Create account",
    "register.submitting": "Creating account…",
    "register.errorDuplicate": "An account with that email already exists.",
    "register.errorGeneric": "Could not register. Check your details and try again.",
    "register.haveAccount": "Already have an account?",
    "register.loginLink": "Log in",

    "derivatives.heading": "Derivatives",
    "derivatives.framing":
      "Perpetual futures market data ingested from Binance — funding rate and futures-vs-index basis. Read-only market data, not a trading signal.",
    "derivatives.loading": "Loading…",
    "derivatives.error": "Could not load derivatives data right now.",
    "derivatives.empty": "No derivatives data has been ingested yet for these symbols.",
    "derivatives.fundingRateLabel": "Funding rate",
    "derivatives.basisLabel": "Basis (futures − index)",
    "derivatives.everyHoursSuffix": "h",
    "derivatives.noFundingRate": "No funding rate data yet.",
    "derivatives.noBasis": "No basis data yet.",

    "signals.heading": "Strategy signals & risk decisions",
    "signals.framing":
      "The latest structured strategy candidate and risk decision per symbol — the same data the broker narrative explains in prose above.",
    "signals.loading": "Loading…",
    "signals.error": "Could not load signals right now.",
    "signals.empty": "No strategy candidate has been generated yet for these symbols.",
    "signals.strategyLabel": "Strategy",
    "signals.directionLabel": "Direction",
    "signals.horizonLabel": "Horizon",
    "signals.expectedEdgeLabel": "Expected edge",
    "signals.estimatedCostsLabel": "Estimated costs",
    "signals.entryLabel": "Entry",
    "signals.stopLabel": "Stop",
    "signals.targetLabel": "Target",
    "signals.riskDecisionLabel": "Risk decision",
    "signals.noRiskDecision": "No matching risk decision found.",
    "signals.reasonsLabel": "Reasons",

    "paperTrading.heading": "Paper trading",
    "paperTrading.framing":
      "Simulated paper account only — no real capital, nothing here places a real order. Positions are replayed from the simulated fills ledger on every pipeline run.",
    "paperTrading.loading": "Loading…",
    "paperTrading.error": "Could not load paper trading data right now.",
    "paperTrading.empty": "The pipeline hasn't produced a paper trade yet.",
    "paperTrading.equityLabel": "Equity",
    "paperTrading.realizedPnlLabel": "Realized PnL",
    "paperTrading.unrealizedPnlLabel": "Unrealized PnL",
    "paperTrading.grossExposureLabel": "Gross exposure",
    "paperTrading.netExposureLabel": "Net exposure",
    "paperTrading.positionsHeading": "Open positions",
    "paperTrading.noPositions": "No open positions.",
    "paperTrading.netSizeLabel": "Net size",
    "paperTrading.avgEntryLabel": "Avg. entry",
    "paperTrading.recentOrdersHeading": "Recent orders",
    "paperTrading.noOrders": "No paper orders yet.",
  },
  es: {
    "page.description":
      "Precios spot de BTC/ETH en vivo, solo desde Binance. Aún no existen estrategias, decisiones de riesgo ni capacidad de ejecución.",
    "page.docsIntro": "Consulta",
    "page.docsOutro": "para ver la arquitectura objetivo y las fases de desarrollo.",

    "dashboard.heading": "Precios en vivo",
    "dashboard.feedIntroPrefix": "Fuente: /api (proxy) — conexión",
    "dashboard.feedIntroSuffix":
      "Los precios de abajo son siempre exactamente lo que envió el exchange; una fila vacía significa que aún no ha llegado ningún dato.",
    "dashboard.status.connecting": "conectando",
    "dashboard.status.connected": "conectado",
    "dashboard.status.error": "error",
    "dashboard.colSymbol": "Símbolo",
    "dashboard.colExchange": "Exchange",
    "dashboard.colPrice": "Último precio",
    "dashboard.colUpdate": "Última actualización (UTC)",
    "dashboard.colLive": "En vivo",
    "dashboard.live": "EN VIVO",
    "dashboard.stale": "desactualizado/sin datos",

    "authGate.checking": "Verificando sesión…",

    "narrative.heading": "Narrativa del bróker",
    "narrative.framing":
      "Esta nota explica un análisis basado en reglas ya producido por risk_engine y ai_council — nada en esta página coloca, dimensiona ni ejecuta una operación.",
    "narrative.loading": "Cargando…",
    "narrative.error": "No se pudo cargar una narrativa en este momento.",
    "narrative.empty": "Aún no se ha generado ninguna narrativa para estos símbolos.",
    "narrative.regimeLabel": "régimen",
    "narrative.confidenceSuffix": "de confianza",
    "narrative.strategyLabel": "estrategia",
    "narrative.decisionLabel": "decisión de riesgo",
    "narrative.councilLabel": "consejo",
    "narrative.generatedAtPrefix": "Generado a partir de datos al",
    "narrative.generatedAtSuffix": "(UTC).",

    "login.heading": "Iniciar sesión",
    "login.email": "Correo electrónico",
    "login.password": "Contraseña",
    "login.submit": "Iniciar sesión",
    "login.submitting": "Iniciando sesión…",
    "login.error": "Correo electrónico o contraseña inválidos.",
    "login.noAccount": "¿No tienes cuenta?",
    "login.registerLink": "Regístrate",

    "register.heading": "Crea tu organización",
    "register.orgName": "Nombre de la organización",
    "register.email": "Correo electrónico",
    "register.password": "Contraseña",
    "register.submit": "Crear cuenta",
    "register.submitting": "Creando cuenta…",
    "register.errorDuplicate": "Ya existe una cuenta con ese correo electrónico.",
    "register.errorGeneric": "No se pudo registrar. Revisa tus datos e intenta de nuevo.",
    "register.haveAccount": "¿Ya tienes una cuenta?",
    "register.loginLink": "Iniciar sesión",

    "derivatives.heading": "Derivados",
    "derivatives.framing":
      "Datos de mercado de futuros perpetuos ingeridos desde Binance — funding rate y basis futuros-vs-índice. Solo datos de mercado de lectura, no es una señal de trading.",
    "derivatives.loading": "Cargando…",
    "derivatives.error": "No se pudieron cargar los datos de derivados en este momento.",
    "derivatives.empty": "Aún no se han ingerido datos de derivados para estos símbolos.",
    "derivatives.fundingRateLabel": "Funding rate",
    "derivatives.basisLabel": "Basis (futuros − índice)",
    "derivatives.everyHoursSuffix": "h",
    "derivatives.noFundingRate": "Aún no hay datos de funding rate.",
    "derivatives.noBasis": "Aún no hay datos de basis.",

    "signals.heading": "Señales de estrategia y decisiones de riesgo",
    "signals.framing":
      "El último candidato de estrategia estructurado y su decisión de riesgo por símbolo — los mismos datos que la narrativa del bróker explica en prosa arriba.",
    "signals.loading": "Cargando…",
    "signals.error": "No se pudieron cargar las señales en este momento.",
    "signals.empty": "Aún no se ha generado ningún candidato de estrategia para estos símbolos.",
    "signals.strategyLabel": "Estrategia",
    "signals.directionLabel": "Dirección",
    "signals.horizonLabel": "Horizonte",
    "signals.expectedEdgeLabel": "Margen esperado",
    "signals.estimatedCostsLabel": "Costos estimados",
    "signals.entryLabel": "Entrada",
    "signals.stopLabel": "Stop",
    "signals.targetLabel": "Objetivo",
    "signals.riskDecisionLabel": "Decisión de riesgo",
    "signals.noRiskDecision": "No se encontró una decisión de riesgo correlacionada.",
    "signals.reasonsLabel": "Razones",

    "paperTrading.heading": "Paper trading",
    "paperTrading.framing":
      "Solo cuenta simulada de papel — sin capital real, nada aquí coloca una orden real. Las posiciones se reconstruyen desde el libro de fills simulados en cada corrida del pipeline.",
    "paperTrading.loading": "Cargando…",
    "paperTrading.error": "No se pudieron cargar los datos de paper trading en este momento.",
    "paperTrading.empty": "El pipeline aún no ha producido ninguna operación simulada.",
    "paperTrading.equityLabel": "Capital",
    "paperTrading.realizedPnlLabel": "PnL realizado",
    "paperTrading.unrealizedPnlLabel": "PnL no realizado",
    "paperTrading.grossExposureLabel": "Exposición bruta",
    "paperTrading.netExposureLabel": "Exposición neta",
    "paperTrading.positionsHeading": "Posiciones abiertas",
    "paperTrading.noPositions": "Sin posiciones abiertas.",
    "paperTrading.netSizeLabel": "Tamaño neto",
    "paperTrading.avgEntryLabel": "Entrada prom.",
    "paperTrading.recentOrdersHeading": "Órdenes recientes",
    "paperTrading.noOrders": "Aún no hay órdenes simuladas.",
  },
} as const satisfies Record<Locale, Record<string, string>>;

export type TranslationKey = keyof (typeof STRINGS)["en"];

export function translate(locale: Locale, key: TranslationKey): string {
  return STRINGS[locale][key];
}

type ConnectionStatus = "connecting" | "connected" | "error";

export function statusLabel(locale: Locale, status: ConnectionStatus): string {
  return translate(locale, `dashboard.status.${status}` as TranslationKey);
}

// Display-only lookup tables for the narrative card's metadata line — the
// underlying values transmitted by the API (regime/decision/finalStance)
// are never translated, only how they're shown here. Mirrors
// narrator.py's own Spanish-only lookup tables (kept separate per the
// "share data not code" precedent used throughout this repo).
const REGIME_LABELS_ES: Record<string, string> = {
  BULLISH_TREND: "tendencia alcista",
  BEARISH_TREND: "tendencia bajista",
  SIDEWAYS: "lateral",
  HIGH_VOLATILITY: "alta volatilidad",
  LOW_VOLATILITY: "baja volatilidad",
  ACCUMULATION: "acumulación",
  DISTRIBUTION: "distribución",
  STRESS_EVENT: "evento de estrés",
};

const DECISION_LABELS_ES: Record<string, string> = {
  APPROVE: "APROBADO",
  REDUCE: "REDUCIDO",
  REJECT: "RECHAZADO",
};

const STANCE_LABELS_ES: Record<string, string> = {
  SUPPORT: "A FAVOR",
  OPPOSE: "EN CONTRA",
  NEUTRAL: "NEUTRAL",
  VETO: "VETO",
};

export function regimeLabel(locale: Locale, regime: string): string {
  return locale === "es" ? (REGIME_LABELS_ES[regime] ?? regime) : regime;
}

export function decisionLabel(locale: Locale, decision: string): string {
  return locale === "es" ? (DECISION_LABELS_ES[decision] ?? decision) : decision;
}

export function stanceLabel(locale: Locale, stance: string): string {
  return locale === "es" ? (STANCE_LABELS_ES[stance] ?? stance) : stance;
}

const DIRECTION_LABELS_ES: Record<string, string> = {
  LONG: "largo",
  SHORT: "corto",
  NEUTRAL: "neutral",
};

export function directionLabel(locale: Locale, direction: string): string {
  return locale === "es" ? (DIRECTION_LABELS_ES[direction] ?? direction) : direction;
}
