"use client";

import { useEffect, useRef } from "react";
import {
  CrosshairMode,
  LineStyle,
  createChart,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { apiFetch, apiStreamUrl } from "../lib/api-client";
import { THEME } from "../lib/theme";
import { useLocale } from "./LocaleProvider";

interface HistoryBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface StreamOhlcvEvent {
  symbol: string;
  interval: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: string;
}

interface LatestSignalResponse {
  signals: {
    symbol: string;
    candidate: {
      entryLogic: Record<string, unknown>;
      stopLogic: Record<string, unknown>;
      targetLogic: Record<string, unknown>;
    };
  }[];
}

const CHART_HEIGHT = 420;
const EMA_FAST_PERIOD = 20;
const EMA_SLOW_PERIOD = 50;

function toUnixSeconds(iso: string): UTCTimestamp {
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp;
}

/**
 * Standard exponential moving average — computed client-side over the same
 * real OHLCV bars the candlesticks render, not a separate/invented series.
 * Matches the textbook definition (packages/quant-core.technical.ema uses
 * the same smoothing convention server-side; this is a client-only render
 * concern, not a second source of truth for anything persisted).
 */
function computeEma(values: number[], period: number): number[] {
  const k = 2 / (period + 1);
  const out: number[] = [];
  let prev: number | undefined;
  for (const value of values) {
    prev = prev === undefined ? value : value * k + prev * (1 - k);
    out.push(prev);
  }
  return out;
}

function numberField(logic: Record<string, unknown>, key: string): number | undefined {
  const value = logic[key];
  return typeof value === "number" ? value : undefined;
}

/**
 * Real candlestick chart (TradingView's lightweight-charts — the same
 * library real crypto platforms build on) seeded from GET /market/history
 * and updated live over the existing /stream/market SSE feed. Overlays
 * EMA20/EMA50 (computed from the same real bars) and, when available, the
 * current strategy candidate's entry/stop/target as price lines — the
 * visual answer to "show the strategy on the chart" instead of only a
 * text table (see SignalsCard). Never renders an instrument or a bar this
 * platform hasn't actually ingested.
 */
export default function PriceChart({ symbol }: { symbol: string }) {
  const { t } = useLocale();
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const ema20SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const ema50SeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const priceLinesRef = useRef<IPriceLine[]>([]);

  // Chart lifecycle: created once, torn down on unmount.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      width: container.clientWidth,
      height: CHART_HEIGHT,
      layout: { background: { color: THEME.panelBg }, textColor: THEME.textSecondary },
      grid: {
        vertLines: { color: THEME.border },
        horzLines: { color: THEME.border },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: THEME.border },
      timeScale: { borderColor: THEME.border, timeVisible: true, secondsVisible: false },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: THEME.positive,
      downColor: THEME.negative,
      borderUpColor: THEME.positive,
      borderDownColor: THEME.negative,
      wickUpColor: THEME.positive,
      wickDownColor: THEME.negative,
    });

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
      color: THEME.textMuted,
    });
    chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });

    const ema20Series = chart.addLineSeries({
      color: THEME.accent,
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const ema50Series = chart.addLineSeries({
      color: "#8b5cf6",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;
    ema20SeriesRef.current = ema20Series;
    ema50SeriesRef.current = ema50Series;

    const resizeObserver = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width;
      if (width) chart.applyOptions({ width });
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
      ema20SeriesRef.current = null;
      ema50SeriesRef.current = null;
      priceLinesRef.current = [];
    };
  }, []);

  // History + live updates for the active symbol.
  useEffect(() => {
    let cancelled = false;
    const bars: HistoryBar[] = [];

    function redrawEma(): void {
      if (bars.length === 0) return;
      const closes = bars.map((b) => b.close);
      const ema20Values = computeEma(closes, EMA_FAST_PERIOD);
      const ema50Values = computeEma(closes, EMA_SLOW_PERIOD);
      ema20SeriesRef.current?.setData(
        bars.map((b, i) => ({ time: toUnixSeconds(b.time), value: ema20Values[i]! })),
      );
      ema50SeriesRef.current?.setData(
        bars.map((b, i) => ({ time: toUnixSeconds(b.time), value: ema50Values[i]! })),
      );
    }

    apiFetch(`/market/history?symbol=${symbol}&interval=1m&limit=200`)
      .then((res) => res.json())
      .then((body: { bars: HistoryBar[] }) => {
        if (cancelled) return;
        bars.push(...body.bars);
        candleSeriesRef.current?.setData(
          bars.map((b) => ({ time: toUnixSeconds(b.time), open: b.open, high: b.high, low: b.low, close: b.close })),
        );
        volumeSeriesRef.current?.setData(
          bars.map((b) => ({
            time: toUnixSeconds(b.time),
            value: b.volume,
            color: b.close >= b.open ? THEME.positive : THEME.negative,
          })),
        );
        redrawEma();
      })
      .catch(() => {
        // Best-effort initial history; the live stream below is still authoritative once connected.
      });

    const source = new EventSource(apiStreamUrl(`/stream/market?symbols=${symbol}`));
    source.addEventListener("ohlcv", (event: MessageEvent<string>) => {
      const bar = JSON.parse(event.data) as StreamOhlcvEvent;
      if (bar.symbol !== symbol || cancelled) return;

      const point = { time: toUnixSeconds(bar.timestamp), open: bar.open, high: bar.high, low: bar.low, close: bar.close };
      candleSeriesRef.current?.update(point);
      volumeSeriesRef.current?.update({
        time: point.time,
        value: bar.volume,
        color: bar.close >= bar.open ? THEME.positive : THEME.negative,
      });

      const historyBar: HistoryBar = {
        time: bar.timestamp,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
        volume: bar.volume,
      };
      const last = bars[bars.length - 1];
      if (last && last.time === bar.timestamp) {
        bars[bars.length - 1] = historyBar;
      } else {
        bars.push(historyBar);
        if (bars.length > 500) bars.shift();
      }
      redrawEma();
    });

    return () => {
      cancelled = true;
      source.close();
    };
  }, [symbol]);

  // Strategy price-line overlay (entry/stop/target) for the active symbol.
  useEffect(() => {
    let cancelled = false;

    apiFetch(`/signals/latest?symbols=${symbol}`)
      .then((res) => res.json())
      .then((body: LatestSignalResponse) => {
        if (cancelled) return;
        const series = candleSeriesRef.current;
        if (!series) return;

        for (const line of priceLinesRef.current) series.removePriceLine(line);
        priceLinesRef.current = [];

        const signal = body.signals.find((s) => s.symbol === symbol);
        if (!signal) return;

        const entry = numberField(signal.candidate.entryLogic, "entryPrice");
        const stop = numberField(signal.candidate.stopLogic, "stopPrice");
        const target = numberField(signal.candidate.targetLogic, "targetPrice");

        if (entry !== undefined) {
          priceLinesRef.current.push(
            series.createPriceLine({
              price: entry,
              color: THEME.accent,
              lineWidth: 1,
              lineStyle: LineStyle.Dashed,
              title: t("chart.entryLine"),
            }),
          );
        }
        if (stop !== undefined) {
          priceLinesRef.current.push(
            series.createPriceLine({
              price: stop,
              color: THEME.negative,
              lineWidth: 1,
              lineStyle: LineStyle.Dashed,
              title: t("chart.stopLine"),
            }),
          );
        }
        if (target !== undefined) {
          priceLinesRef.current.push(
            series.createPriceLine({
              price: target,
              color: THEME.positive,
              lineWidth: 1,
              lineStyle: LineStyle.Dashed,
              title: t("chart.targetLine"),
            }),
          );
        }
      })
      .catch(() => {
        // No signal overlay is a normal, honest state (e.g. no candidate for the current regime).
      });

    return () => {
      cancelled = true;
    };
  }, [symbol, t]);

  return <div ref={containerRef} style={{ width: "100%", height: CHART_HEIGHT }} />;
}
