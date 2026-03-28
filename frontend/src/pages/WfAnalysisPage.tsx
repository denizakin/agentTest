import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button, Group, Stack, Title, Table, Badge, Modal, Text, Loader, Progress, Tooltip } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import type { WfoSummary, WfoDetail, CreateWfoRequest, Strategy, CoinSummary, MonteCarloResult, TradeItem } from "../api/types";
import CreateWfoModal from "../components/CreateWfoModal";
import EquityChart from "../components/EquityChart";
import MonteCarloChart from "../components/MonteCarloChart";
import TradesTable from "../components/TradesTable";

const TH = ({ tip, children }: { tip: string; children: React.ReactNode }) => (
  <Tooltip label={tip} withArrow position="top" multiline w={260}>
    <Table.Th style={{ cursor: "help", whiteSpace: "nowrap" }}>{children}</Table.Th>
  </Tooltip>
);

export default function WfAnalysisPage() {
  const [createModalOpened, setCreateModalOpened] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [combinedEquityRunId, setCombinedEquityRunId] = useState<number | null>(null);
  const [wfoMcRunId, setWfoMcRunId] = useState<number | null>(null);
  const [showCombinedTrades, setShowCombinedTrades] = useState(false);
  const qc = useQueryClient();

  // List WFO runs
  const wfoQuery = useQuery<WfoSummary[]>({
    queryKey: ["walkforwards"],
    queryFn: async () => {
      const res = await fetch("/api/walkforwards");
      if (!res.ok) throw new Error("Failed to fetch walk-forward runs");
      return res.json();
    },
    refetchInterval: 5000,
  });

  // Strategies & coins for the create modal
  const strategiesQuery = useQuery<Strategy[]>({
    queryKey: ["strategies"],
    queryFn: async () => {
      const res = await fetch("/api/strategies");
      if (!res.ok) throw new Error("Failed to fetch strategies");
      return res.json();
    },
  });

  const coinsQuery = useQuery<CoinSummary[]>({
    queryKey: ["coins"],
    queryFn: async () => {
      const res = await fetch("/api/coins");
      if (!res.ok) throw new Error("Failed to fetch coins");
      return res.json();
    },
  });

  // Detail query
  const detailQuery = useQuery<WfoDetail>({
    queryKey: ["wfo-detail", selectedRunId],
    queryFn: async () => {
      if (!selectedRunId) throw new Error("No run selected");
      const res = await fetch(`/api/walkforwards/${selectedRunId}`);
      if (!res.ok) throw new Error("Failed to fetch WFO detail");
      return res.json();
    },
    enabled: !!selectedRunId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === "running" || data?.status === "queued") return 5000;
      return false;
    },
  });

  // Combined equity query (lazy — only runs when combinedEquityRunId is set)
  const combinedEquityQuery = useQuery<{ equity: {ts: string; value: number}[]; baseline_equity: {ts: string; value: number}[]; trades: TradeItem[]; final_value: number; initial_cash: number }>({
    queryKey: ["wfo-combined-equity", combinedEquityRunId],
    queryFn: async () => {
      const res = await fetch(`/api/walkforwards/${combinedEquityRunId}/combined-equity`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || "Failed to compute combined equity");
      }
      return res.json();
    },
    enabled: !!combinedEquityRunId,
    staleTime: Infinity,
  });

  // WFO Monte Carlo query
  const wfoMcQuery = useQuery<MonteCarloResult>({
    queryKey: ["wfo-monte-carlo", wfoMcRunId],
    queryFn: async () => {
      const res = await fetch(`/api/walkforwards/${wfoMcRunId}/monte-carlo`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || "Failed to compute Monte Carlo");
      }
      return res.json();
    },
    enabled: !!wfoMcRunId,
    staleTime: Infinity,
  });

  // Create mutation
  const createMutation = useMutation({
    mutationFn: async (payload: CreateWfoRequest) => {
      const res = await fetch("/api/walkforwards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(errorData.detail || "Failed to create WFO");
      }
      return res.json();
    },
    onSuccess: () => {
      notifications.show({ title: "WFO queued", message: "Walk-forward analysis has been queued", color: "green" });
      qc.invalidateQueries({ queryKey: ["walkforwards"] });
      setCreateModalOpened(false);
    },
    onError: (error: Error) => {
      notifications.show({ title: "Failed to create WFO", message: error.message, color: "red" });
    },
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case "succeeded": return "green";
      case "failed": return "red";
      case "running": return "blue";
      case "queued": return "gray";
      default: return "gray";
    }
  };

  const fmt = (v: number | null | undefined, decimals = 2) => (v != null ? v.toFixed(decimals) : "—");
  const fmtDollar = (v: number | null | undefined) => (v != null ? `$${v.toFixed(2)}` : "—");
  const fmtPct = (v: number | null | undefined) => (v != null ? `${v.toFixed(2)}%` : "—");
  const fmtDate = (s: string) => new Date(s).toLocaleDateString();
  const fmtElapsed = (start?: string | null, end?: string | null) => {
    if (!start || !end) return "—";
    const secs = Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000);
    if (secs < 60) return `${secs}s`;
    if (secs < 3600) return `${Math.floor(secs / 60)}m ${secs % 60}s`;
    return `${Math.floor(secs / 3600)}h ${Math.floor((secs % 3600) / 60)}m`;
  };

  return (
    <Stack gap="md" style={{ height: "calc(100vh - 100px)", display: "flex", flexDirection: "column" }}>
      <Group justify="space-between">
        <Title order={3}>Walk-Forward Analysis</Title>
        <Button onClick={() => setCreateModalOpened(true)}>New WFO</Button>
      </Group>

      {wfoQuery.isLoading && (
        <div style={{ display: "flex", justifyContent: "center", padding: "40px" }}><Loader /></div>
      )}

      {wfoQuery.error && (
        <Text c="red">Failed to load WFO runs: {(wfoQuery.error as Error).message}</Text>
      )}

      {wfoQuery.data && wfoQuery.data.length === 0 && (
        <Text c="dimmed" style={{ textAlign: "center", padding: "40px" }}>
          No walk-forward analyses yet. Create your first WFO to get started.
        </Text>
      )}

      {wfoQuery.data && wfoQuery.data.length > 0 && (
        <div style={{ flex: 1, overflow: "auto" }}>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Strategy</Table.Th>
                <Table.Th>Instrument</Table.Th>
                <Table.Th>Bar</Table.Th>
                <Table.Th>Objective</Table.Th>
                <Table.Th>Windows</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Progress</Table.Th>
                <Table.Th>Folds</Table.Th>
                <Table.Th>Submitted</Table.Th>
                <Table.Th>Duration</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {wfoQuery.data.map((wfo) => (
                <Table.Tr key={wfo.run_id}>
                  <Table.Td>{wfo.run_id}</Table.Td>
                  <Table.Td>{wfo.strategy_name || `ID ${wfo.strategy_id}`}</Table.Td>
                  <Table.Td>{wfo.instrument_id}</Table.Td>
                  <Table.Td>{wfo.bar}</Table.Td>
                  <Table.Td>{wfo.objective ?? "—"}</Table.Td>
                  <Table.Td>
                    <Text size="xs">{wfo.train_months ?? "?"}m / {wfo.test_months ?? "?"}m / {wfo.step_months ?? "?"}m</Text>
                  </Table.Td>
                  <Table.Td><Badge color={getStatusColor(wfo.status)}>{wfo.status}</Badge></Table.Td>
                  <Table.Td><Progress value={wfo.progress} size="sm" style={{ width: "80px" }} /></Table.Td>
                  <Table.Td>{wfo.total_folds || "—"}</Table.Td>
                  <Table.Td>{new Date(wfo.submitted_at).toLocaleString()}</Table.Td>
                  <Table.Td>{fmtElapsed(wfo.submitted_at, wfo.ended_at)}</Table.Td>
                  <Table.Td>
                    <Button size="xs" variant="light" onClick={() => { setSelectedRunId(wfo.run_id); setCombinedEquityRunId(wfo.run_id); }}>
                      View Results
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      )}

      {/* Create WFO Modal */}
      <CreateWfoModal
        opened={createModalOpened}
        onClose={() => setCreateModalOpened(false)}
        onSubmit={(params) => createMutation.mutate(params)}
        strategies={strategiesQuery.data || []}
        coins={coinsQuery.data || []}
        isLoading={createMutation.isPending}
      />

      {/* WFO Detail Modal */}
      <Modal
        opened={!!selectedRunId}
        onClose={() => { setSelectedRunId(null); setCombinedEquityRunId(null); setWfoMcRunId(null); }}
        title={`Walk-Forward Results - Run #${selectedRunId}`}
        size="95vw"
        styles={{ body: { padding: "12px 16px" } }}
      >
        {detailQuery.isLoading && (
          <div style={{ display: "flex", justifyContent: "center", padding: "40px" }}><Loader /></div>
        )}

        {detailQuery.error && <Text c="red">Failed to load results: {(detailQuery.error as Error).message}</Text>}

        {detailQuery.data && (
          <Stack gap="sm">
            {/* Config summary */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "4px 16px", fontSize: "13px" }}>
              <Text size="sm"><Text span c="dimmed">Strategy:</Text> {detailQuery.data.strategy_name}</Text>
              <Text size="sm"><Text span c="dimmed">Instrument:</Text> {detailQuery.data.instrument_id}</Text>
              <Text size="sm"><Text span c="dimmed">Bar:</Text> {detailQuery.data.bar}</Text>
              <Text size="sm"><Text span c="dimmed">Objective:</Text> {detailQuery.data.objective ?? "—"}</Text>
              <Text size="sm"><Text span c="dimmed">Windows:</Text> {detailQuery.data.train_months}m train / {detailQuery.data.test_months}m test / {detailQuery.data.step_months}m step</Text>
              <Text size="sm"><Text span c="dimmed">Cash:</Text> ${detailQuery.data.cash?.toLocaleString() ?? "—"}</Text>
              <Text size="sm">
                <Text span c="dimmed">Commission:</Text>{" "}
                {detailQuery.data.commission != null ? `${(detailQuery.data.commission * 100).toFixed(2)}%` : "—"}
              </Text>
              <Text size="sm">
                <Text span c="dimmed">Period:</Text>{" "}
                {detailQuery.data.start_ts
                  ? `${new Date(detailQuery.data.start_ts).toLocaleDateString()} - ${detailQuery.data.end_ts ? new Date(detailQuery.data.end_ts).toLocaleDateString() : "now"}`
                  : "All available data"}
              </Text>
              <Text size="sm"><Text span c="dimmed">Max CPUs:</Text> {detailQuery.data.maxcpus ?? 1}</Text>
              <Text size="sm">
                <Text span c="dimmed">Started:</Text>{" "}
                {detailQuery.data.submitted_at ? new Date(detailQuery.data.submitted_at).toLocaleString() : "—"}
              </Text>
              <Text size="sm">
                <Text span c="dimmed">Ended:</Text>{" "}
                {detailQuery.data.ended_at ? new Date(detailQuery.data.ended_at).toLocaleString() : "—"}
              </Text>
              <Text size="sm">
                <Text span c="dimmed">Duration:</Text>{" "}
                {fmtElapsed(detailQuery.data.submitted_at, detailQuery.data.ended_at)}
              </Text>
            </div>

            <Group gap="sm">
              <Badge color={getStatusColor(detailQuery.data.status)} size="sm">{detailQuery.data.status}</Badge>
              <Text size="xs" c="dimmed">{detailQuery.data.total_folds} folds | Progress: {detailQuery.data.progress}%</Text>
              {detailQuery.data.constraint && (
                <Text size="xs" c="dimmed">| Constraint: <code>{detailQuery.data.constraint}</code></Text>
              )}
              {detailQuery.data.error && <Text size="xs" c="red">| {detailQuery.data.error}</Text>}
              {detailQuery.data.status === "succeeded" && detailQuery.data.total_folds > 0 && (
                <>
                  <Button
                    size="xs"
                    variant="light"
                    color="teal"
                    onClick={() => {
                      if (combinedEquityRunId === selectedRunId) {
                        setCombinedEquityRunId(null);
                      } else {
                        qc.removeQueries({ queryKey: ["wfo-combined-equity", selectedRunId] });
                        setCombinedEquityRunId(selectedRunId);
                      }
                    }}
                  >
                    {combinedEquityRunId === selectedRunId ? "Hide Combined Equity" : "Combined Equity"}
                  </Button>
                  <Button
                    size="xs"
                    variant="light"
                    color="violet"
                    onClick={() => {
                      if (wfoMcRunId === selectedRunId) {
                        setWfoMcRunId(null);
                      } else {
                        qc.removeQueries({ queryKey: ["wfo-monte-carlo", selectedRunId] });
                        setWfoMcRunId(selectedRunId);
                      }
                    }}
                  >
                    {wfoMcRunId === selectedRunId ? "Hide Monte Carlo" : "Monte Carlo"}
                  </Button>
                </>
              )}
            </Group>

            {/* Combined equity chart */}
            {combinedEquityRunId === selectedRunId && (
              <div style={{ background: "var(--mantine-color-dark-6, #f8f9fa)", padding: "8px 12px", borderRadius: "6px" }}>
                <Text size="sm" fw={600} mb={6}>Combined Out-of-Sample Equity Curve</Text>
                {combinedEquityQuery.isFetching && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "20px 0" }}>
                    <Loader size="sm" />
                    <Text size="xs" c="dimmed">Running {detailQuery.data.total_folds} test folds sequentially…</Text>
                  </div>
                )}
                {combinedEquityQuery.error && (
                  <Text size="xs" c="red">{(combinedEquityQuery.error as Error).message}</Text>
                )}
                {combinedEquityQuery.data && (
                  <>
                    <Group gap="xl" mb={6}>
                      <Text size="xs"><Text span c="dimmed">Initial:</Text> {fmtDollar(combinedEquityQuery.data.initial_cash)}</Text>
                      <Text size="xs"><Text span c="dimmed">Final:</Text> <Text span fw={700} c={combinedEquityQuery.data.final_value >= combinedEquityQuery.data.initial_cash ? "green" : "red"}>{fmtDollar(combinedEquityQuery.data.final_value)}</Text></Text>
                      <Text size="xs"><Text span c="dimmed">Return:</Text> {fmt((combinedEquityQuery.data.final_value / combinedEquityQuery.data.initial_cash - 1) * 100)}%</Text>
                      <Text size="xs"><Text span c="dimmed">Trades:</Text> {combinedEquityQuery.data.trades.length}</Text>
                      <Button size="xs" variant="subtle" color="gray" onClick={() => setShowCombinedTrades((v) => !v)}>
                        {showCombinedTrades ? "Hide Trades" : "Show Trades"}
                      </Button>
                    </Group>
                    <EquityChart key={combinedEquityQuery.data.equity.length} equity={combinedEquityQuery.data.equity} baselineEquity={combinedEquityQuery.data.baseline_equity} initialCash={combinedEquityQuery.data.initial_cash} />
                    {combinedEquityQuery.data.equity.length > 0 && (
                      <Text size="xs" c="dimmed" mt={4}>
                        {combinedEquityQuery.data.equity.length} pts &nbsp;|&nbsp; {combinedEquityQuery.data.equity[0].ts.slice(0, 10)} → {combinedEquityQuery.data.equity[combinedEquityQuery.data.equity.length - 1].ts.slice(0, 10)}
                      </Text>
                    )}
                    {showCombinedTrades && combinedEquityQuery.data.trades.length > 0 && (
                      <div style={{ marginTop: 8 }}>
                        <TradesTable trades={combinedEquityQuery.data.trades} />
                      </div>
                    )}
                  </>
                )}
              </div>
            )}

            {/* WFO Monte Carlo chart */}
            {wfoMcRunId === selectedRunId && (
              <div style={{ background: "var(--mantine-color-dark-6, #f8f9fa)", padding: "8px 12px", borderRadius: "6px" }}>
                <Text size="sm" fw={600} mb={6}>Monte Carlo — Trade Sequence Shuffling</Text>
                {wfoMcQuery.isFetching && (
                  <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "20px 0" }}>
                    <Loader size="sm" />
                    <Text size="xs" c="dimmed">Running simulations…</Text>
                  </div>
                )}
                {wfoMcQuery.error && (
                  <Text size="xs" c="red">{(wfoMcQuery.error as Error).message}</Text>
                )}
                {wfoMcQuery.data && (
                  <>
                    <Text size="xs" c="dimmed" mb={6}>
                      {wfoMcQuery.data.n_sims} simulations · {wfoMcQuery.data.n_trades} trades
                    </Text>
                    <MonteCarloChart key={wfoMcRunId} data={wfoMcQuery.data} />
                    <Group gap="xl" mt={6} style={{ fontSize: "12px" }}>
                      <span style={{ color: "#3b82f6" }}>— Actual</span>
                      <span style={{ color: "#f59e0b" }}>— Median (P50)</span>
                      <span style={{ color: "#4b5563" }}>— P25/P75</span>
                      <span style={{ color: "#374151" }}>— P5/P95</span>
                    </Group>
                    <Text size="xs" c="dimmed" mt={4}>
                      Max Drawdown distribution across {wfoMcQuery.data.n_sims} shuffled simulations — lower is better
                    </Text>
                    <Group gap="sm" mt={8}>
                      {[
                        { label: "Best 5% (P5 DD)", val: wfoMcQuery.data.dd_p5 },
                        { label: "P25 DD", val: wfoMcQuery.data.dd_p25 },
                        { label: "Median DD", val: wfoMcQuery.data.dd_p50 },
                        { label: "P75 DD", val: wfoMcQuery.data.dd_p75 },
                        { label: "Worst 5% (P95 DD)", val: wfoMcQuery.data.dd_p95 },
                        { label: "Actual Max DD", val: wfoMcQuery.data.dd_actual },
                      ].map(({ label, val }) => (
                        <div key={label} style={{ background: "#111827", borderRadius: "6px", padding: "6px 10px", border: "1px solid #374151" }}>
                          <div style={{ fontSize: "11px", color: "#9ca3af", marginBottom: "2px" }}>{label}</div>
                          <div style={{ fontSize: "14px", fontWeight: "bold", color: val < 10 ? "#4ade80" : val < 20 ? "#f59e0b" : "#f87171" }}>
                            {val.toFixed(1)}%
                          </div>
                        </div>
                      ))}
                    </Group>
                  </>
                )}
              </div>
            )}

            {/* OOS aggregate metrics */}
            {detailQuery.data.folds.length > 0 && (() => {
              const folds = detailQuery.data.folds;
              const finals = folds.map((f) => f.metrics?.final as number | undefined).filter((v): v is number => v != null);
              const sharpes = folds.map((f) => f.metrics?.sharpe as number | undefined).filter((v): v is number => v != null);
              const winrates = folds.map((f) => f.metrics?.winrate as number | undefined).filter((v): v is number => v != null);
              const avg = (arr: number[]) => arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : null;
              const profitable = finals.filter((v) => v > (detailQuery.data.cash ?? 10000)).length;
              return (
                <div style={{ background: "var(--mantine-color-dark-6, #f8f9fa)", padding: "8px 12px", borderRadius: "6px" }}>
                  <Text size="sm" fw={600} mb={4}>Out-of-Sample Summary</Text>
                  <Group gap="xl">
                    <Text size="xs"><Text span c="dimmed">Avg Final:</Text> {fmtDollar(avg(finals))}</Text>
                    <Text size="xs"><Text span c="dimmed">Avg Sharpe:</Text> {fmt(avg(sharpes), 3)}</Text>
                    <Text size="xs"><Text span c="dimmed">Avg Win Rate:</Text> {fmtPct(avg(winrates))}</Text>
                    <Text size="xs"><Text span c="dimmed">Profitable Folds:</Text> {profitable}/{finals.length}</Text>
                  </Group>
                </div>
              );
            })()}

            {/* Folds Table */}
            <div style={{ maxHeight: "60vh", overflow: "auto" }}>
              <Table striped highlightOnHover style={{ fontSize: "12px" }}>
                <Table.Thead style={{ position: "sticky", top: 0, background: "var(--mantine-color-dark-7, #fff)", zIndex: 1 }}>
                  <Table.Tr>
                    <Table.Th>#</Table.Th>
                    <TH tip="The training period used for parameter optimization">Train Period</TH>
                    <TH tip="The out-of-sample test period used to validate the best params">Test Period</TH>
                    <TH tip="Best parameters found during the training optimization">Best Params</TH>
                    <TH tip="The objective metric value achieved during training (used to select best params)">Train Obj</TH>
                    <TH tip="Portfolio value at the end of the test period (out-of-sample)">Test Final</TH>
                    <TH tip="Annualized Sharpe Ratio on test period. Higher is better">Test Sharpe</TH>
                    <TH tip="Maximum Drawdown during the test period (%)">Test Max DD</TH>
                    <TH tip="Win rate on test period trades (%)">Test Win Rate</TH>
                    <TH tip="Profit Factor on test period: gross profit / gross loss">Test PF</TH>
                    <TH tip="Test period trades: Won / Lost / Total closed">Test W/L/T</TH>
                    <TH tip="Average Maximum Adverse Excursion per trade in this fold (dollar amount of worst intra-trade drawdown)">Avg MAE</TH>
                    <TH tip="Average Maximum Favorable Excursion per trade in this fold (dollar amount of best unrealized gain during trade)">Avg MFE</TH>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {detailQuery.data.folds.map((fold) => {
                    const m = fold.metrics || {};
                    const cash = detailQuery.data.cash ?? 10000;
                    const finalVal = m.final as number | undefined;
                    const isProfitable = finalVal != null && finalVal > cash;

                    // Compute per-fold MAE/MFE from combined trades
                    const foldTrades = combinedEquityQuery.data?.trades.filter((t) => {
                      const exitTs = new Date(t.exit_ts).getTime();
                      const testStart = new Date(fold.test_start).getTime();
                      const testEnd = new Date(fold.test_end).getTime();
                      return exitTs >= testStart && exitTs <= testEnd;
                    }) ?? [];
                    const tradesWithMae = foldTrades.filter((t) => t.mae != null);
                    const tradesWithMfe = foldTrades.filter((t) => t.mfe != null);
                    const avgMae = tradesWithMae.length > 0
                      ? tradesWithMae.reduce((s, t) => s + (t.mae ?? 0), 0) / tradesWithMae.length
                      : null;
                    const avgMfe = tradesWithMfe.length > 0
                      ? tradesWithMfe.reduce((s, t) => s + (t.mfe ?? 0), 0) / tradesWithMfe.length
                      : null;

                    return (
                      <Table.Tr key={fold.id}>
                        <Table.Td>#{fold.fold_index}</Table.Td>
                        <Table.Td>
                          <Text size="xs">{fmtDate(fold.train_start)} → {fmtDate(fold.train_end)}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs">{fmtDate(fold.test_start)} → {fmtDate(fold.test_end)}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs" style={{ fontFamily: "monospace", whiteSpace: "nowrap" }}>
                            {fold.params ? Object.entries(fold.params).map(([k, v]) => `${k}=${v}`).join(", ") : "—"}
                          </Text>
                        </Table.Td>
                        <Table.Td>{fmt(fold.train_objective, 2)}</Table.Td>
                        <Table.Td>
                          <Text size="xs" fw={700} c={isProfitable ? "green" : "red"}>
                            {fmtDollar(finalVal)}
                          </Text>
                        </Table.Td>
                        <Table.Td>{fmt(m.sharpe as number | undefined, 3)}</Table.Td>
                        <Table.Td>{fmtPct(m.maxdd as number | undefined)}</Table.Td>
                        <Table.Td>{fmtPct(m.winrate as number | undefined)}</Table.Td>
                        <Table.Td>{fmt(m.pf as number | undefined)}</Table.Td>
                        <Table.Td>
                          {m.won !== undefined || m.lost !== undefined || m.closed !== undefined ? (
                            <Text size="xs" style={{ whiteSpace: "nowrap", fontFamily: "monospace" }}>
                              <Text span c="green">{(m.won as number) ?? 0}</Text>
                              {" / "}
                              <Text span c="red">{(m.lost as number) ?? 0}</Text>
                              {" / "}
                              <Text span>{(m.closed as number) ?? 0}</Text>
                            </Text>
                          ) : "—"}
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs" c="red">{avgMae != null ? `$${avgMae.toFixed(2)}` : "—"}</Text>
                        </Table.Td>
                        <Table.Td>
                          <Text size="xs" c="green">{avgMfe != null ? `$${avgMfe.toFixed(2)}` : "—"}</Text>
                        </Table.Td>
                      </Table.Tr>
                    );
                  })}
                </Table.Tbody>
              </Table>
            </div>

            {detailQuery.data.folds.length === 0 && (
              <Text c="dimmed" style={{ textAlign: "center", padding: "20px" }}>
                No folds yet. The analysis is still running or has not produced any results.
              </Text>
            )}
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
