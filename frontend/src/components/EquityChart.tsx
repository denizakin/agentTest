import { useEffect, useRef } from "react";

type EquityPoint = {
  ts: string;
  value: number;
};

type Props = {
  equity: EquityPoint[];
  baselineEquity?: EquityPoint[];
  initialCash: number;
};

export default function EquityChart({ equity, baselineEquity, initialCash }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<any>(null);
  const mainSeriesRef = useRef<any>(null);
  const baselineSeriesRef = useRef<any>(null);

  useEffect(() => {
    let active = true;
    if (!containerRef.current || chartRef.current) return;

    (async () => {
      try {
        const { createChart, ColorType } = await import("lightweight-charts");
        if (!active || !containerRef.current) return;

        const chart = createChart(containerRef.current, {
          height: 300,
          layout: { background: { type: ColorType.Solid, color: "#1f2937" }, textColor: "#ccd" },
          grid: { vertLines: { color: "#374151" }, horzLines: { color: "#374151" } },
          timeScale: {
            borderColor: "#374151",
            timeVisible: true,
            secondsVisible: false,
          },
          rightPriceScale: { borderColor: "#374151" },
          crosshair: {
            mode: 0,
            vertLine: {
              color: "#6a7178",
              width: 1,
              style: 1,
              labelBackgroundColor: "#374151",
            },
            horzLine: {
              color: "#6a7178",
              width: 1,
              style: 1,
              labelBackgroundColor: "#374151",
            },
          },
        });

        chartRef.current = chart;

        // Add main equity series
        mainSeriesRef.current = chart.addLineSeries({
          color: "#3b82f6",
          lineWidth: 2,
          title: "Strategy",
        });

        // Add baseline equity series if provided
        if (baselineEquity && baselineEquity.length > 0) {
          baselineSeriesRef.current = chart.addLineSeries({
            color: "#9ca3af",
            lineWidth: 2,
            lineStyle: 2, // Dashed
            title: "Buy & Hold",
          });
        }

        // Set data
        if (equity.length > 0) {
          const mainData = equity.map((point) => ({
            time: Math.floor(new Date(point.ts).getTime() / 1000),
            value: point.value,
          }));
          mainSeriesRef.current.setData(mainData);
        }

        if (baselineEquity && baselineEquity.length > 0 && baselineSeriesRef.current) {
          const baselineData = baselineEquity.map((point) => ({
            time: Math.floor(new Date(point.ts).getTime() / 1000),
            value: point.value,
          }));
          baselineSeriesRef.current.setData(baselineData);
        }

        chart.timeScale().fitContent();
      } catch (err) {
        console.error("Failed to initialize equity chart:", err);
      }
    })();

    return () => {
      active = false;
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        mainSeriesRef.current = null;
        baselineSeriesRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    const mainSeries = mainSeriesRef.current;
    const baselineSeries = baselineSeriesRef.current;
    if (!chart || !mainSeries) return;

    // Update main equity data
    if (equity.length > 0) {
      const mainData = equity.map((point) => ({
        time: Math.floor(new Date(point.ts).getTime() / 1000),
        value: point.value,
      }));
      mainSeries.setData(mainData);
    }

    // Update baseline equity data
    if (baselineEquity && baselineEquity.length > 0 && baselineSeries) {
      const baselineData = baselineEquity.map((point) => ({
        time: Math.floor(new Date(point.ts).getTime() / 1000),
        value: point.value,
      }));
      baselineSeries.setData(baselineData);
    }

    chart.timeScale().fitContent();
  }, [equity, baselineEquity]);

  return <div ref={containerRef} style={{ width: "100%", height: "300px" }} />;
}
