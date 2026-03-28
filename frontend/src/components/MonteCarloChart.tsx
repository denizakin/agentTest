import { useEffect, useRef } from "react";
import type { MonteCarloResult } from "../api/types";

type Props = {
  data: MonteCarloResult;
};

export default function MonteCarloChart({ data }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<any>(null);

  useEffect(() => {
    let active = true;
    if (!containerRef.current || chartRef.current) return;

    (async () => {
      try {
        const { createChart, ColorType } = await import("lightweight-charts");
        if (!active || !containerRef.current) return;

        // Use real trade-exit timestamps when provided, otherwise fall back to
        // daily spacing from 2000-01-01 so lightweight-charts shows clean labels.
        const BASE_TIME = 946684800; // 2000-01-01 UTC
        const ts = data.timestamps;
        const hasRealTs = !!(ts && ts.length === data.actual.length);

        const getTime = (i: number): number =>
          hasRealTs ? ts![i] : BASE_TIME + i * 86400;

        const toSeries = (vals: number[]) =>
          vals.map((value, i) => ({
            time: getTime(i) as unknown as import("lightweight-charts").UTCTimestamp,
            value,
          }));

        const chart = createChart(containerRef.current, {
          height: 320,
          layout: {
            background: { type: ColorType.Solid, color: "#1f2937" },
            textColor: "#ccd",
          },
          grid: {
            vertLines: { color: "#374151" },
            horzLines: { color: "#374151" },
          },
          timeScale: {
            borderColor: "#374151",
            timeVisible: hasRealTs,
            secondsVisible: false,
          },
          rightPriceScale: { borderColor: "#374151" },
          crosshair: {
            mode: 0,
            vertLine: { color: "#6a7178", width: 1, style: 1, labelBackgroundColor: "#374151" },
            horzLine: { color: "#6a7178", width: 1, style: 1, labelBackgroundColor: "#374151" },
          },
        });

        chartRef.current = chart;

        chart.addLineSeries({ color: "#374151", lineWidth: 1, title: "P5" }).setData(toSeries(data.p5));
        chart.addLineSeries({ color: "#374151", lineWidth: 1, title: "P95" }).setData(toSeries(data.p95));
        chart.addLineSeries({ color: "#4b5563", lineWidth: 1, title: "P25" }).setData(toSeries(data.p25));
        chart.addLineSeries({ color: "#4b5563", lineWidth: 1, title: "P75" }).setData(toSeries(data.p75));
        chart.addLineSeries({ color: "#f59e0b", lineWidth: 2, title: "Median" }).setData(toSeries(data.p50));

        // WFO: use the full bar-level equity curve for "Actual" so inter-fold
        // gaps and intra-fold open-position moves are shown correctly.
        // Backtest: fall back to trade-exit-indexed actual series.
        const actualSeries = chart.addLineSeries({ color: "#3b82f6", lineWidth: 2, title: "Actual" });
        if (data.equity_curve && data.equity_curve.length > 0) {
          actualSeries.setData(
            data.equity_curve.map(([t, value]) => ({
              time: t as unknown as import("lightweight-charts").UTCTimestamp,
              value,
            }))
          );
        } else {
          actualSeries.setData(toSeries(data.actual));
        }

        requestAnimationFrame(() => {
          if (active && chartRef.current) chartRef.current.timeScale().fitContent();
        });
      } catch (err) {
        console.error("Failed to initialize Monte Carlo chart:", err);
      }
    })();

    return () => {
      active = false;
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, []);

  return <div ref={containerRef} style={{ width: "100%", height: "320px" }} />;
}
