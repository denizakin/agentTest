import { useState } from "react";
import type { RunResultItem } from "../api/types";

type Props = {
  results: RunResultItem[];
};

export default function BacktestResults({ results }: Props) {
  const [activeTab, setActiveTab] = useState<"metrics" | "trades">("metrics");

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
          </div>

          {/* Equity Chart Placeholder */}
          <div
            style={{
              background: "#1f2937",
              borderRadius: "8px",
              padding: "20px",
              minHeight: "300px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#9ca3af",
            }}
          >
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: "18px", marginBottom: "10px" }}>Equity Curve</div>
              <div style={{ fontSize: "14px" }}>Coming soon...</div>
            </div>
          </div>
        </div>
      )}

      {activeTab === "trades" && (
        <div
          style={{
            background: "#1f2937",
            borderRadius: "8px",
            padding: "20px",
            minHeight: "400px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#9ca3af",
          }}
        >
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "18px", marginBottom: "10px" }}>Trade List</div>
            <div style={{ fontSize: "14px" }}>Coming soon...</div>
          </div>
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
