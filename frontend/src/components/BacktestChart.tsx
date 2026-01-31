import { useEffect, useRef, useState } from "react";
import type { ChartResponse } from "../api/types";

type Props = { data?: ChartResponse };

export default function BacktestChart({ data }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<any>(null);
  const candleRef = useRef<any>(null);
  const volumeRef = useRef<any>(null);
  const signalSeriesRef = useRef<any[]>([]);
  const [ohlcv, setOhlcv] = useState<{ time: string; open: number; high: number; low: number; close: number; volume: number } | null>(null);

  useEffect(() => {
    let active = true;
    if (!containerRef.current || chartRef.current) return;

    (async () => {
      try {
        const { createChart, ColorType } = await import("lightweight-charts");
        if (!active || !containerRef.current) return;

        // Get container height or default to 600px
        const containerHeight = containerRef.current.clientHeight || 600;

        const chart = createChart(containerRef.current, {
          height: containerHeight,
          layout: { background: { type: ColorType.Solid, color: "#0b0f1a" }, textColor: "#ccd" },
          grid: { vertLines: { color: "#1f2a3d" }, horzLines: { color: "#1f2a3d" } },
          timeScale: {
            borderColor: "#1f2a3d",
            timeVisible: true,
            secondsVisible: false,
            tickMarkFormatter: (time: number) => {
              const date = new Date(time * 1000);
              return date.toLocaleString("tr-TR", {
                timeZone: "Europe/Istanbul",
                year: "numeric",
                month: "2-digit",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit"
              });
            },
          },
          localization: {
            timeFormatter: (time: number) => {
              const date = new Date(time * 1000);
              return date.toLocaleString("tr-TR", {
                timeZone: "Europe/Istanbul",
                year: "numeric",
                month: "2-digit",
                day: "2-digit",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
              });
            },
          },
          rightPriceScale: { borderColor: "#1f2a3d" },
          crosshair: {
            mode: 0, // Normal mode (0 = CrosshairMode.Normal) - free movement
            vertLine: {
              color: "#6a7178",
              width: 1,
              style: 1, // LineStyle.Dashed
              labelBackgroundColor: "#1f2a3d",
            },
            horzLine: {
              color: "#6a7178",
              width: 1,
              style: 1,
              labelBackgroundColor: "#1f2a3d",
            },
          },
        });

        chartRef.current = chart;

        candleRef.current = chart.addCandlestickSeries({
          upColor: "#4ade80",
          downColor: "#f87171",
          borderDownColor: "#f87171",
          borderUpColor: "#4ade80",
          wickDownColor: "#f87171",
          wickUpColor: "#4ade80",
          priceFormat: {
            type: "price",
            precision: 8,
            minMove: 0.00000001,
          },
        });

        volumeRef.current = chart.addHistogramSeries({
          priceFormat: { type: "volume" },
          priceScaleId: "",
          color: "rgba(100,149,237,0.5)",
        });

        // Apply initial data if available
        if (data?.candles?.length) {
          const candleData = data.candles.map((c) => {
            // Parse ISO string with timezone info - Date constructor handles timezone correctly
            const timestamp = Math.floor(new Date(c.time).getTime() / 1000);
            return {
              time: timestamp,
              open: Number(c.open),
              high: Number(c.high),
              low: Number(c.low),
              close: Number(c.close),
            };
          });
          const volumeData = data.candles.map((c) => ({
            time: Math.floor(new Date(c.time).getTime() / 1000),
            value: Number(c.volume),
            color: Number(c.close) >= Number(c.open) ? "rgba(74,222,128,0.5)" : "rgba(248,113,113,0.5)",
          }));

          candleRef.current.setData(candleData);
          volumeRef.current.setData(volumeData);

          if (data.signals?.length) {
            const markers = data.signals
              .map((s) => {
                const date = new Date(s.time);
                const timeStr = date.toLocaleString("tr-TR", {
                  timeZone: "Europe/Istanbul",
                  day: "2-digit",
                  month: "2-digit",
                  hour: "2-digit",
                  minute: "2-digit"
                });
                return {
                  time: Math.floor(date.getTime() / 1000),
                  position: s.side.toUpperCase() === "BUY" ? "belowBar" : "aboveBar",
                  color: s.side.toUpperCase() === "BUY" ? "#4ade80" : "#f87171",
                  shape: s.side.toUpperCase() === "BUY" ? "arrowUp" : "arrowDown",
                  text: s.price ? `${s.side[0]} ${Number(s.price).toFixed(4)}\n${timeStr}` : `${s.side[0]}\n${timeStr}`,
                };
              })
              .sort((a, b) => a.time - b.time);
            candleRef.current.setMarkers(markers);

            // Add price lines for each signal
            data.signals.forEach((s) => {
              if (!s.price) return;
              const lineSeries = chart.addLineSeries({
                color: "#fef08a", // Fosforlu sarı (yellow-200)
                lineWidth: 2,
                priceLineVisible: false,
                lastValueVisible: false,
                crosshairMarkerVisible: false,
              });
              const timestamp = Math.floor(new Date(s.time).getTime() / 1000) as any;
              lineSeries.setData([{ time: timestamp, value: Number(s.price) }]);
              signalSeriesRef.current.push(lineSeries);
            });
          }

          chart.timeScale().fitContent();
        }

        // Subscribe to crosshair move for OHLCV display
        chart.subscribeCrosshairMove((param: any) => {
          if (!param || !param.time || !candleRef.current) {
            setOhlcv(null);
            return;
          }

          const candleData = param.seriesData.get(candleRef.current);
          if (!candleData) {
            setOhlcv(null);
            return;
          }

          const volumeData = param.seriesData.get(volumeRef.current);
          const volumeValue = volumeData?.value || 0;

          setOhlcv({
            time: new Date(param.time * 1000).toLocaleString("tr-TR", {
              timeZone: "Europe/Istanbul",
              year: "numeric",
              month: "2-digit",
              day: "2-digit",
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit"
            }),
            open: candleData.open,
            high: candleData.high,
            low: candleData.low,
            close: candleData.close,
            volume: volumeValue,
          });
        });
      } catch (err) {
        console.error("Failed to initialize chart:", err);
      }
    })();

    return () => {
      active = false;
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        candleRef.current = null;
        volumeRef.current = null;
        signalSeriesRef.current = [];
      }
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    const candle = candleRef.current;
    const volume = volumeRef.current;
    if (!chart || !candle || !volume || !data?.candles?.length) return;

    const candleData = data.candles.map((c) => {
      // Parse ISO string with timezone info - Date constructor handles timezone correctly
      const timestamp = Math.floor(new Date(c.time).getTime() / 1000);
      return {
        time: timestamp,
        open: Number(c.open),
        high: Number(c.high),
        low: Number(c.low),
        close: Number(c.close),
      };
    });
    const volumeData = data.candles.map((c) => ({
      time: Math.floor(new Date(c.time).getTime() / 1000),
      value: Number(c.volume),
      color: Number(c.close) >= Number(c.open) ? "rgba(74,222,128,0.5)" : "rgba(248,113,113,0.5)",
    }));

    candle.setData(candleData);
    volume.setData(volumeData);

    // Remove old signal series
    signalSeriesRef.current.forEach((series) => {
      chart.removeSeries(series);
    });
    signalSeriesRef.current = [];

    if (data.signals?.length) {
      const markers = data.signals
        .map((s) => {
          const date = new Date(s.time);
          const timeStr = date.toLocaleString("tr-TR", {
            timeZone: "Europe/Istanbul",
            day: "2-digit",
            month: "2-digit",
            hour: "2-digit",
            minute: "2-digit"
          });
          return {
            time: Math.floor(date.getTime() / 1000),
            position: s.side.toUpperCase() === "BUY" ? "belowBar" : "aboveBar",
            color: s.side.toUpperCase() === "BUY" ? "#4ade80" : "#f87171",
            shape: s.side.toUpperCase() === "BUY" ? "arrowUp" : "arrowDown",
            text: s.price ? `${s.side[0]} ${Number(s.price).toFixed(4)}\n${timeStr}` : `${s.side[0]}\n${timeStr}`,
          };
        })
        .sort((a, b) => a.time - b.time);
      candle.setMarkers(markers);

      // Add price lines for each signal
      data.signals.forEach((s) => {
        if (!s.price) return;
        const lineSeries = chart.addLineSeries({
          color: "#fef08a", // Fosforlu sarı (yellow-200)
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        const timestamp = Math.floor(new Date(s.time).getTime() / 1000) as any;
        lineSeries.setData([{ time: timestamp, value: Number(s.price) }]);
        signalSeriesRef.current.push(lineSeries);
      });
    }

    chart.timeScale().fitContent();
  }, [data]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
      {ohlcv && (
        <div
          style={{
            position: "absolute",
            top: 10,
            left: 10,
            backgroundColor: "rgba(11, 15, 26, 0.85)",
            border: "1px solid #1f2a3d",
            borderRadius: "4px",
            padding: "8px 12px",
            fontFamily: "monospace",
            fontSize: "12px",
            color: "#ccd",
            pointerEvents: "none",
            zIndex: 10,
          }}
        >
          <div style={{ marginBottom: "4px", fontWeight: "bold" }}>
            {ohlcv.time}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "auto auto", gap: "4px 8px" }}>
            <span style={{ color: "#888" }}>O:</span>
            <span>{ohlcv.open.toFixed(8)}</span>
            <span style={{ color: "#888" }}>H:</span>
            <span style={{ color: "#4ade80" }}>{ohlcv.high.toFixed(8)}</span>
            <span style={{ color: "#888" }}>L:</span>
            <span style={{ color: "#f87171" }}>{ohlcv.low.toFixed(8)}</span>
            <span style={{ color: "#888" }}>C:</span>
            <span>{ohlcv.close.toFixed(8)}</span>
            <span style={{ color: "#888" }}>V:</span>
            <span>{ohlcv.volume.toFixed(2)}</span>
          </div>
        </div>
      )}
    </div>
  );
}
