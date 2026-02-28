import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ActionIcon, Button, Group, Stack, Title, Table, Badge, Modal, Text, Loader, Progress, Tooltip } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import type { OptimizationSummary, OptimizationDetail, CreateOptimizationRequest, Strategy, CoinSummary } from "../api/types";
import CreateOptimizationModal from "../components/CreateOptimizationModal";
import BacktestDetailModal from "../components/BacktestDetailModal";

const TH = ({ tip, children }: { tip: string; children: React.ReactNode }) => (
  <Tooltip label={tip} withArrow position="top" multiline w={260}>
    <Table.Th style={{ cursor: "help", whiteSpace: "nowrap" }}>{children}</Table.Th>
  </Tooltip>
);

export default function OptimizationsPage() {
  const [backtestRunId, setBacktestRunId] = useState<number | null>(null);
  const [createModalOpened, setCreateModalOpened] = useState(false);
  const [selectedOptId, setSelectedOptId] = useState<number | null>(null);
  const qc = useQueryClient();

  // Fetch optimizations list
  const optimizationsQuery = useQuery<OptimizationSummary[]>({
    queryKey: ["optimizations"],
    queryFn: async () => {
      const res = await fetch("/api/optimizations");
      if (!res.ok) throw new Error("Failed to fetch optimizations");
      return res.json();
    },
    refetchInterval: 5000,
  });

  // Fetch strategies for modal
  const strategiesQuery = useQuery<Strategy[]>({
    queryKey: ["strategies"],
    queryFn: async () => {
      const res = await fetch("/api/strategies");
      if (!res.ok) throw new Error("Failed to fetch strategies");
      return res.json();
    },
  });

  // Fetch coins for modal
  const coinsQuery = useQuery<CoinSummary[]>({
    queryKey: ["coins"],
    queryFn: async () => {
      const res = await fetch("/api/coins");
      if (!res.ok) throw new Error("Failed to fetch coins");
      return res.json();
    },
  });

  // Fetch optimization detail
  const detailQuery = useQuery<OptimizationDetail>({
    queryKey: ["optimization-detail", selectedOptId],
    queryFn: async () => {
      if (!selectedOptId) throw new Error("No optimization selected");
      const res = await fetch(`/api/optimizations/${selectedOptId}?limit=50`);
      if (!res.ok) throw new Error("Failed to fetch optimization detail");
      return res.json();
    },
    enabled: !!selectedOptId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === "running" || data?.status === "queued") return 5000;
      return false;
    },
  });

  // Create optimization mutation
  const createMutation = useMutation({
    mutationFn: async (payload: CreateOptimizationRequest) => {
      const res = await fetch("/api/optimizations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(errorData.detail || "Failed to create optimization");
      }
      return res.json();
    },
    onSuccess: () => {
      notifications.show({ title: "Optimization queued", message: "Optimization job has been queued successfully", color: "green" });
      qc.invalidateQueries({ queryKey: ["optimizations"] });
      setCreateModalOpened(false);
    },
    onError: (error: Error) => {
      notifications.show({ title: "Failed to create optimization", message: error.message, color: "red" });
    },
  });

  // Run backtest from variant params
  const backtestMutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      const res = await fetch("/api/backtests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(errorData.detail || "Failed to create backtest");
      }
      return res.json();
    },
    onSuccess: (data: { run_id: number; existing?: boolean }) => {
      if (!data.existing) {
        notifications.show({ title: "Backtest queued", message: `Backtest #${data.run_id} has been queued`, color: "blue" });
      }
      qc.invalidateQueries({ queryKey: ["backtests"] });
      setBacktestRunId(data.run_id);
    },
    onError: (error: Error) => {
      notifications.show({ title: "Failed to create backtest", message: error.message, color: "red" });
    },
  });

  const handleRunBacktest = (variantParams: Record<string, unknown>) => {
    if (!detailQuery.data) return;
    const d = detailQuery.data;
    backtestMutation.mutate({
      strategy_id: d.strategy_id,
      instrument_id: d.instrument_id,
      bar: d.bar,
      start_ts: d.start_ts,
      end_ts: d.end_ts,
      params: variantParams,
      cash: d.cash,
      commission: d.commission,
      slip_perc: d.slip_perc,
      slip_fixed: d.slip_fixed,
    });
  };

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

  return (
    <Stack gap="md" style={{ height: "calc(100vh - 100px)", display: "flex", flexDirection: "column" }}>
      <Group justify="space-between">
        <Title order={3}>Optimizations</Title>
        <Button onClick={() => setCreateModalOpened(true)}>New Optimization</Button>
      </Group>

      {optimizationsQuery.isLoading && (
        <div style={{ display: "flex", justifyContent: "center", padding: "40px" }}><Loader /></div>
      )}

      {optimizationsQuery.error && (
        <Text c="red">Failed to load optimizations: {(optimizationsQuery.error as Error).message}</Text>
      )}

      {optimizationsQuery.data && optimizationsQuery.data.length === 0 && (
        <Text c="dimmed" style={{ textAlign: "center", padding: "40px" }}>
          No optimizations yet. Create your first optimization to get started.
        </Text>
      )}

      {optimizationsQuery.data && optimizationsQuery.data.length > 0 && (
        <div style={{ flex: 1, overflow: "auto" }}>
          <Table striped highlightOnHover>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>ID</Table.Th>
                <Table.Th>Strategy</Table.Th>
                <Table.Th>Instrument</Table.Th>
                <Table.Th>Bar</Table.Th>
                <Table.Th>Status</Table.Th>
                <Table.Th>Progress</Table.Th>
                <Table.Th>Variants</Table.Th>
                <Table.Th>Best Value</Table.Th>
                <Table.Th>Submitted</Table.Th>
                <Table.Th>Actions</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {optimizationsQuery.data.map((opt) => (
                <Table.Tr key={opt.run_id}>
                  <Table.Td>{opt.run_id}</Table.Td>
                  <Table.Td>{opt.strategy_name || `ID ${opt.strategy_id}`}</Table.Td>
                  <Table.Td>{opt.instrument_id}</Table.Td>
                  <Table.Td>{opt.bar}</Table.Td>
                  <Table.Td><Badge color={getStatusColor(opt.status)}>{opt.status}</Badge></Table.Td>
                  <Table.Td><Progress value={opt.progress} size="sm" style={{ width: "80px" }} /></Table.Td>
                  <Table.Td>{opt.total_variants ?? "—"}</Table.Td>
                  <Table.Td>{opt.best_final_value != null ? `$${opt.best_final_value.toFixed(2)}` : "—"}</Table.Td>
                  <Table.Td>{new Date(opt.submitted_at).toLocaleString()}</Table.Td>
                  <Table.Td>
                    <Button size="xs" variant="light" onClick={() => setSelectedOptId(opt.run_id)}>
                      View Results
                    </Button>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </div>
      )}

      {/* Create Optimization Modal */}
      <CreateOptimizationModal
        opened={createModalOpened}
        onClose={() => setCreateModalOpened(false)}
        onSubmit={(params) => createMutation.mutate(params)}
        strategies={strategiesQuery.data || []}
        coins={coinsQuery.data || []}
        isLoading={createMutation.isPending}
      />

      {/* Optimization Detail Modal */}
      <Modal
        opened={!!selectedOptId}
        onClose={() => setSelectedOptId(null)}
        title={`Optimization Results - Run #${selectedOptId}`}
        size="95vw"
        styles={{ body: { padding: "12px 16px" } }}
      >
        {detailQuery.isLoading && (
          <div style={{ display: "flex", justifyContent: "center", padding: "40px" }}><Loader /></div>
        )}

        {detailQuery.error && <Text c="red">Failed to load results: {(detailQuery.error as Error).message}</Text>}

        {detailQuery.data && (
          <Stack gap="sm">
            {/* Summary & Config */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "4px 16px", fontSize: "13px" }}>
              <Text size="sm"><Text span c="dimmed">Strategy:</Text> {detailQuery.data.strategy_name}</Text>
              <Text size="sm"><Text span c="dimmed">Instrument:</Text> {detailQuery.data.instrument_id}</Text>
              <Text size="sm"><Text span c="dimmed">Bar:</Text> {detailQuery.data.bar}</Text>
              <Text size="sm"><Text span c="dimmed">Cash:</Text> ${detailQuery.data.cash?.toLocaleString() ?? "—"}</Text>
              <Text size="sm">
                <Text span c="dimmed">Commission:</Text>{" "}
                {detailQuery.data.commission != null ? `${(detailQuery.data.commission * 100).toFixed(2)}%` : "—"}
              </Text>
              <Text size="sm">
                <Text span c="dimmed">Slippage:</Text>{" "}
                {detailQuery.data.slip_perc ? `${(detailQuery.data.slip_perc * 100).toFixed(2)}%` : detailQuery.data.slip_fixed ? `$${detailQuery.data.slip_fixed}` : "None"}
              </Text>
              <Text size="sm">
                <Text span c="dimmed">Period:</Text>{" "}
                {detailQuery.data.start_ts
                  ? `${new Date(detailQuery.data.start_ts).toLocaleDateString()} - ${detailQuery.data.end_ts ? new Date(detailQuery.data.end_ts).toLocaleDateString() : "now"}`
                  : "All available data"}
              </Text>
              <Text size="sm"><Text span c="dimmed">Max CPUs:</Text> {detailQuery.data.maxcpus ?? 1}</Text>
            </div>

            <Group gap="sm">
              <Badge color={getStatusColor(detailQuery.data.status)} size="sm">{detailQuery.data.status}</Badge>
              <Text size="xs" c="dimmed">{detailQuery.data.total_variants} variants | Progress: {detailQuery.data.progress}%</Text>
              {detailQuery.data.constraint && (
                <Text size="xs" c="dimmed">| Constraint: <code>{detailQuery.data.constraint}</code></Text>
              )}
              {detailQuery.data.error && <Text size="xs" c="red">| {detailQuery.data.error}</Text>}
            </Group>

            {/* Variants Table */}
            <div style={{ maxHeight: "60vh", overflow: "auto" }}>
              <Table striped highlightOnHover style={{ fontSize: "12px" }}>
                <Table.Thead style={{ position: "sticky", top: 0, background: "var(--mantine-color-dark-7, #fff)", zIndex: 1 }}>
                  <Table.Tr>
                    <Table.Th>#</Table.Th>
                    <Table.Th>Parameters</Table.Th>
                    <TH tip="Portfolio value at the end of backtest (cash + net PnL)">Final Value</TH>
                    <TH tip="Annualized Sharpe Ratio: risk-adjusted return. Higher is better. >1 good, >2 great">Sharpe</TH>
                    <TH tip="Maximum Drawdown: largest peak-to-trough decline (%). Lower is better">Max DD</TH>
                    <TH tip="Win Rate: percentage of winning trades out of total closed trades">Win Rate</TH>
                    <TH tip="Profit Factor: gross profit / gross loss. >1 profitable, >1.5 good, >2 great">PF</TH>
                    <TH tip="System Quality Number: measures consistency. >2 good, >3 excellent, >5 superb">SQN</TH>
                    <TH tip="Total number of closed trades during the backtest period">Trades</TH>
                    <TH tip="Number of winning trades">Won</TH>
                    <TH tip="Number of losing trades">Lost</TH>
                    <TH tip="Number of long (buy) trades">Long</TH>
                    <TH tip="Number of short (sell) trades">Short</TH>
                    <TH tip="Best single trade profit ($)">Best Trade</TH>
                    <TH tip="Worst single trade loss ($)">Worst Trade</TH>
                    <TH tip="Average net PnL per trade ($)">Avg PnL</TH>
                    <Table.Th></Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {detailQuery.data.variants.map((v, idx) => (
                    <Table.Tr key={v.id}>
                      <Table.Td>#{idx + 1}</Table.Td>
                      <Table.Td>
                        <Text size="xs" style={{ fontFamily: "monospace", whiteSpace: "nowrap" }}>
                          {Object.entries(v.variant_params).map(([k, val]) => `${k}=${val}`).join(", ")}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" fw={idx === 0 ? 700 : 400} c={idx === 0 ? "green" : undefined}>
                          {fmtDollar(v.final_value)}
                        </Text>
                      </Table.Td>
                      <Table.Td>{fmt(v.sharpe, 3)}</Table.Td>
                      <Table.Td>{fmtPct(v.maxdd)}</Table.Td>
                      <Table.Td>{fmtPct(v.winrate)}</Table.Td>
                      <Table.Td>{fmt(v.profit_factor)}</Table.Td>
                      <Table.Td>{fmt(v.sqn)}</Table.Td>
                      <Table.Td>{v.total_trades ?? "—"}</Table.Td>
                      <Table.Td>
                        <Text size="xs" c="green">{v.won_count ?? "—"}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c="red">{v.lost_count ?? "—"}</Text>
                      </Table.Td>
                      <Table.Td>{v.long_count ?? "—"}</Table.Td>
                      <Table.Td>{v.short_count ?? "—"}</Table.Td>
                      <Table.Td>
                        <Text size="xs" c={v.best_pnl != null && v.best_pnl > 0 ? "green" : undefined}>
                          {fmtDollar(v.best_pnl)}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c={v.worst_pnl != null && v.worst_pnl < 0 ? "red" : undefined}>
                          {fmtDollar(v.worst_pnl)}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" c={v.avg_pnl != null ? (v.avg_pnl >= 0 ? "green" : "red") : undefined}>
                          {fmtDollar(v.avg_pnl)}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Tooltip label="Run backtest with these parameters" withArrow>
                          <ActionIcon
                            size="xs"
                            variant="subtle"
                            color="blue"
                            onClick={() => handleRunBacktest(v.variant_params)}
                            loading={backtestMutation.isPending}
                          >
                            ▶
                          </ActionIcon>
                        </Tooltip>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </div>

            {detailQuery.data.variants.length === 0 && (
              <Text c="dimmed" style={{ textAlign: "center", padding: "20px" }}>
                No optimization results yet. The optimization is still running or has not produced any results.
              </Text>
            )}
          </Stack>
        )}
      </Modal>

      {/* Backtest detail pop-up opened from variant row */}
      <BacktestDetailModal
        runId={backtestRunId}
        onClose={() => setBacktestRunId(null)}
      />
    </Stack>
  );
}
