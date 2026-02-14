import { useState, useMemo } from "react";
import type { TradeItem } from "../api/types";

type Props = {
  trades: TradeItem[];
  onTradeClick?: (entryTime: string, exitTime: string) => void;
};

type SortField = "entry_ts" | "exit_ts" | "pnl" | "pnl_pct" | "mae" | "mfe";
type SortDirection = "asc" | "desc";

export default function TradesTable({ trades, onTradeClick }: Props) {
  const [sortField, setSortField] = useState<SortField>("entry_ts");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("asc");
    }
  };

  const sortedTrades = useMemo(() => {
    // Add original index to each trade before sorting
    const tradesWithIndex = trades.map((trade, idx) => ({ ...trade, originalIndex: idx + 1 }));

    return tradesWithIndex.sort((a, b) => {
      let aVal: any = a[sortField];
      let bVal: any = b[sortField];

      // Handle date fields
      if (sortField === "entry_ts" || sortField === "exit_ts") {
        aVal = new Date(aVal).getTime();
        bVal = new Date(bVal).getTime();
      }

      // Handle null values
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      if (sortDirection === "asc") {
        return aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
      } else {
        return aVal < bVal ? 1 : aVal > bVal ? -1 : 0;
      }
    });
  }, [trades, sortField, sortDirection]);

  const formatTimestamp = (ts: string) => {
    const date = new Date(ts);
    return date.toLocaleString("tr-TR", {
      timeZone: "Europe/Istanbul",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatDuration = (entry: string, exit: string) => {
    const entryDate = new Date(entry);
    const exitDate = new Date(exit);
    const durationMs = exitDate.getTime() - entryDate.getTime();
    const hours = Math.floor(durationMs / (1000 * 60 * 60));
    const minutes = Math.floor((durationMs % (1000 * 60 * 60)) / (1000 * 60));
    if (hours > 24) {
      const days = Math.floor(hours / 24);
      const remainingHours = hours % 24;
      return `${days}d ${remainingHours}h`;
    }
    return `${hours}h ${minutes}m`;
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <span style={{ color: "#6b7280" }}>↕</span>;
    return sortDirection === "asc" ? <span>↑</span> : <span>↓</span>;
  };

  if (trades.length === 0) {
    return (
      <div
        style={{
          background: "#1f2937",
          borderRadius: "8px",
          padding: "40px",
          textAlign: "center",
          color: "#9ca3af",
        }}
      >
        No trades executed
      </div>
    );
  }

  return (
    <div style={{ background: "#1f2937", borderRadius: "8px", overflow: "hidden" }}>
      <div style={{ overflowX: "auto", overflowY: "auto", maxHeight: "600px" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
          <thead>
            <tr style={{ background: "#111827", borderBottom: "1px solid #374151" }}>
              <th style={headerStyle}>#</th>
              <th style={headerStyle}>
                <button onClick={() => handleSort("entry_ts")} style={sortButtonStyle}>
                  Entry Time <SortIcon field="entry_ts" />
                </button>
              </th>
              <th style={headerStyle}>
                <button onClick={() => handleSort("exit_ts")} style={sortButtonStyle}>
                  Exit Time <SortIcon field="exit_ts" />
                </button>
              </th>
              <th style={headerStyle}>Duration</th>
              <th style={headerStyle}>Side</th>
              <th style={headerStyle}>Entry Price</th>
              <th style={headerStyle}>Exit Price</th>
              <th style={headerStyle}>Size</th>
              <th style={headerStyle}>
                <button onClick={() => handleSort("pnl")} style={sortButtonStyle}>
                  P&L <SortIcon field="pnl" />
                </button>
              </th>
              <th style={headerStyle}>
                <button onClick={() => handleSort("pnl_pct")} style={sortButtonStyle}>
                  P&L % <SortIcon field="pnl_pct" />
                </button>
              </th>
              <th style={headerStyle}>
                <button onClick={() => handleSort("mae")} style={sortButtonStyle}>
                  MAE <SortIcon field="mae" />
                </button>
              </th>
              <th style={headerStyle}>
                <button onClick={() => handleSort("mfe")} style={sortButtonStyle}>
                  MFE <SortIcon field="mfe" />
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {sortedTrades.map((trade, idx) => (
              <tr
                key={idx}
                style={{
                  borderBottom: "1px solid #374151",
                  background: idx % 2 === 0 ? "#1f2937" : "#1a2332",
                }}
              >
                <td style={cellStyle}>
                  {onTradeClick ? (
                    <button
                      onClick={() => onTradeClick(trade.entry_ts, trade.exit_ts)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "#3b82f6",
                        cursor: "pointer",
                        textDecoration: "underline",
                        padding: 0,
                        font: "inherit",
                      }}
                      title="Click to view on chart"
                    >
                      #{(trade as any).originalIndex}
                    </button>
                  ) : (
                    <span>#{(trade as any).originalIndex}</span>
                  )}
                </td>
                <td style={cellStyle}>{formatTimestamp(trade.entry_ts)}</td>
                <td style={cellStyle}>{formatTimestamp(trade.exit_ts)}</td>
                <td style={cellStyle}>{formatDuration(trade.entry_ts, trade.exit_ts)}</td>
                <td style={cellStyle}>
                  <span
                    style={{
                      color: trade.side === "LONG" ? "#4ade80" : "#f87171",
                      fontWeight: 600,
                    }}
                  >
                    {trade.side}
                  </span>
                </td>
                <td style={cellStyle}>{trade.entry_price.toFixed(8)}</td>
                <td style={cellStyle}>{trade.exit_price.toFixed(8)}</td>
                <td style={cellStyle}>{trade.size.toFixed(4)}</td>
                <td style={{ ...cellStyle, color: trade.pnl >= 0 ? "#4ade80" : "#f87171", fontWeight: 600 }}>
                  {trade.pnl >= 0 ? "+" : ""}
                  {trade.pnl.toFixed(2)}
                </td>
                <td style={{ ...cellStyle, color: (trade.pnl_pct || 0) >= 0 ? "#4ade80" : "#f87171" }}>
                  {trade.pnl_pct !== null && trade.pnl_pct !== undefined
                    ? `${trade.pnl_pct >= 0 ? "+" : ""}${trade.pnl_pct.toFixed(2)}%`
                    : "N/A"}
                </td>
                <td style={cellStyle}>
                  {trade.mae !== null && trade.mae !== undefined ? trade.mae.toFixed(2) : "N/A"}
                </td>
                <td style={cellStyle}>
                  {trade.mfe !== null && trade.mfe !== undefined ? trade.mfe.toFixed(2) : "N/A"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div
        style={{
          padding: "15px 20px",
          borderTop: "1px solid #374151",
          fontSize: "12px",
          color: "#9ca3af",
          display: "flex",
          justifyContent: "space-between",
        }}
      >
        <span>Total Trades: {trades.length}</span>
        <span>
          Winning: {trades.filter((t) => t.pnl > 0).length} | Losing: {trades.filter((t) => t.pnl < 0).length}
        </span>
      </div>
    </div>
  );
}

const headerStyle: React.CSSProperties = {
  padding: "12px 16px",
  textAlign: "left",
  color: "#9ca3af",
  fontWeight: 600,
  whiteSpace: "nowrap",
};

const cellStyle: React.CSSProperties = {
  padding: "12px 16px",
  color: "#ccd",
  whiteSpace: "nowrap",
};

const sortButtonStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "inherit",
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  gap: "4px",
  padding: 0,
  font: "inherit",
  fontWeight: "inherit",
};
