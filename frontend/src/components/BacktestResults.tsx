import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { RunResultItem, TradeItem } from "../api/types";
import EquityChart from "./EquityChart";
import TradesTable from "./TradesTable";
import type { BacktestChartHandle } from "./BacktestChart";

type Props = {
  results: RunResultItem[];
  runId: number;
  chartRef?: React.RefObject<BacktestChartHandle>;
};

export default function BacktestResults({ results, runId, chartRef }: Props) {
  const [activeTab, setActiveTab] = useState<"metrics" | "trades">("metrics");

  const handleTradeClick = (entryTime: string, exitTime: string) => {
    // Don't switch tabs, just zoom the chart
    // Note: Chart is in metrics tab, so if user is in trades tab, they won't see the zoom
    // But this preserves their current view as requested
    chartRef?.current?.zoomToTrade(entryTime, exitTime);
  };

  // Fetch trades data - always fetch for MAE/MFE metrics
  const tradesQuery = useQuery<TradeItem[]>({
    queryKey: ["backtest-trades", runId],
    queryFn: async () => {
      const res = await fetch(`/api/backtests/${runId}/trades`, {
        cache: 'no-cache',  // Disable browser cache for trades
      });
      if (!res.ok) throw new Error("Failed to fetch trades");
      return res.json();
    },
    staleTime: 0,  // Always refetch when query is used
    cacheTime: 0,  // Don't keep in cache
  });

  // Find main and baseline results
  const mainResult = results.find((r) => r.label === "main");
  const baselineResult = results.find((r) => r.label === "baseline");

  const metrics = mainResult?.metrics || {};
  const baselineMetrics = baselineResult?.metrics || {};

  // Calculate comparison vs Buy&Hold
  const finalValue = (metrics.final as number) || 0;
  const baselineFinal = (baselineMetrics.final as number) || 0;
  const vsBaseline = finalValue - baselineFinal;
  const vsBaselinePct = baselineFinal ? ((vsBaseline / baselineFinal) * 100) : 0;

  // Extract equity curves
  const equity = (metrics.equity as Array<{ ts: string; value: number }>) || [];
  const baselineEquity = (baselineMetrics.equity as Array<{ ts: string; value: number }>) || [];
  const initialCash = equity.length > 0 ? equity[0].value : 10000;

  // Calculate MAE/MFE totals from trades
  const trades = tradesQuery.data || [];
  const totalMAE = trades.reduce((sum, t) => sum + (t.mae || 0), 0);
  const totalMFE = trades.reduce((sum, t) => sum + (t.mfe || 0), 0);
  const avgMAE = trades.length > 0 ? totalMAE / trades.length : 0;
  const avgMFE = trades.length > 0 ? totalMFE / trades.length : 0;

  // Debug log
  console.log("BacktestResults - metrics:", metrics);
  console.log("BacktestResults - equity points:", equity.length);
  console.log("BacktestResults - baseline equity points:", baselineEquity.length);
  console.log("BacktestResults - trades:", trades.length, "totalMAE:", totalMAE, "totalMFE:", totalMFE);

  return (
    <div style={{ padding: "20px" }}>
      {/* Tabs */}
      <div style={{ borderBottom: "1px solid #374151", marginBottom: "20px" }}>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={() => setActiveTab("metrics")}
            style={{
              padding: "10px 20px",
              background: activeTab === "metrics" ? "#1f2937" : "transparent",
              border: "none",
              borderBottom: activeTab === "metrics" ? "2px solid #3b82f6" : "2px solid transparent",
              color: activeTab === "metrics" ? "#fff" : "#9ca3af",
              cursor: "pointer",
              fontSize: "14px",
              fontWeight: 500,
            }}
          >
            Metrics & Equity
          </button>
          <button
            onClick={() => setActiveTab("trades")}
            style={{
              padding: "10px 20px",
              background: activeTab === "trades" ? "#1f2937" : "transparent",
              border: "none",
              borderBottom: activeTab === "trades" ? "2px solid #3b82f6" : "2px solid transparent",
              color: activeTab === "trades" ? "#9ca3af" : "#9ca3af",
              cursor: "pointer",
              fontSize: "14px",
              fontWeight: 500,
            }}
          >
            Trades
          </button>
        </div>
      </div>

      {/* Content */}
      {activeTab === "metrics" && (
        <div>
          {/* Metrics Grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "15px",
              marginBottom: "30px",
            }}
          >
            {/* Total P&L */}
            <MetricCard
              title="Total P&L"
              value={finalValue ? `$${finalValue.toFixed(2)}` : "N/A"}
              subtitle={vsBaseline !== 0 ? `vs B&H: ${vsBaseline > 0 ? "+" : ""}${vsBaseline.toFixed(2)} (${vsBaselinePct > 0 ? "+" : ""}${vsBaselinePct.toFixed(2)}%)` : undefined}
              color={vsBaseline > 0 ? "#4ade80" : vsBaseline < 0 ? "#f87171" : undefined}
            />

            {/* Max DD */}
            <MetricCard
              title="Max Drawdown"
              value={metrics.maxdd ? `${Number(metrics.maxdd).toFixed(2)}%` : "N/A"}
              color="#f87171"
            />

            {/* Trade Numbers */}
            <MetricCard
              title="Trades (W/L/T)"
              value={
                metrics.won !== undefined && metrics.lost !== undefined && metrics.closed !== undefined
                  ? `${metrics.won}/${metrics.lost}/${metrics.closed}`
                  : "N/A"
              }
            />

            {/* Win Rate */}
            <MetricCard
              title="Win Rate"
              value={metrics.winrate ? `${Number(metrics.winrate).toFixed(2)}%` : "N/A"}
              color={Number(metrics.winrate) > 50 ? "#4ade80" : "#f87171"}
            />

            {/* Profit Factor */}
            <MetricCard
              title="Profit Factor"
              value={metrics.pf ? Number(metrics.pf).toFixed(3) : "N/A"}
              color={Number(metrics.pf) > 1 ? "#4ade80" : "#f87171"}
            />

            {/* Sharpe */}
            <MetricCard
              title="Sharpe Ratio"
              value={metrics.sharpe ? Number(metrics.sharpe).toFixed(3) : "N/A"}
            />

            {/* SQN */}
            <MetricCard
              title="SQN"
              value={metrics.sqn ? Number(metrics.sqn).toFixed(2) : "N/A"}
            />

            {/* Total MAE */}
            <MetricCard
              title="Total MAE"
              value={trades.length > 0 ? `$${totalMAE.toFixed(2)}` : "N/A"}
              subtitle={trades.length > 0 ? `Avg: $${avgMAE.toFixed(2)}` : undefined}
              color="#f87171"
            />

            {/* Total MFE */}
            <MetricCard
              title="Total MFE"
              value={trades.length > 0 ? `$${totalMFE.toFixed(2)}` : "N/A"}
              subtitle={trades.length > 0 ? `Avg: $${avgMFE.toFixed(2)}` : undefined}
              color="#4ade80"
            />
          </div>

          {/* Equity Chart */}
          <div
            style={{
              background: "#1f2937",
              borderRadius: "8px",
              padding: "20px",
              minHeight: "300px",
            }}
          >
            <div style={{ fontSize: "16px", marginBottom: "15px", color: "#fff", fontWeight: 500 }}>
              Equity Curve
            </div>
            {equity.length > 0 ? (
              <EquityChart equity={equity} baselineEquity={baselineEquity} initialCash={initialCash} />
            ) : (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", minHeight: "250px", color: "#9ca3af", gap: "10px" }}>
                <div>No equity data available</div>
                <div style={{ fontSize: "12px", color: "#6b7280" }}>
                  Equity curve data is only available for backtests run after the latest update.
                  <br />
                  Please run a new backtest to see the equity curve.
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === "trades" && (
        <div>
          {tradesQuery.isLoading && (
            <div style={{ textAlign: "center", padding: "40px", color: "#9ca3af" }}>
              Loading trades...
            </div>
          )}
          {tradesQuery.isError && (
            <div style={{ textAlign: "center", padding: "40px", color: "#f87171" }}>
              Failed to load trades
            </div>
          )}
          {tradesQuery.data && <TradesTable trades={tradesQuery.data} onTradeClick={handleTradeClick} />}
        </div>
      )}
    </div>
  );
}

type MetricCardProps = {
  title: string;
  value: string;
  subtitle?: string;
  color?: string;
};

function MetricCard({ title, value, subtitle, color }: MetricCardProps) {
  return (
    <div
      style={{
        background: "#1f2937",
        borderRadius: "8px",
        padding: "15px",
        border: "1px solid #374151",
      }}
    >
      <div style={{ fontSize: "12px", color: "#9ca3af", marginBottom: "8px" }}>{title}</div>
      <div style={{ fontSize: "24px", fontWeight: "bold", color: color || "#fff", marginBottom: subtitle ? "5px" : "0" }}>
        {value}
      </div>
      {subtitle && <div style={{ fontSize: "11px", color: "#6b7280" }}>{subtitle}</div>}
    </div>
  );
}
