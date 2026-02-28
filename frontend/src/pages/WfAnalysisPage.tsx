import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button, Group, Stack, Title, Table, Badge, Modal, Text, Loader, Progress, Tooltip } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import type { WfoSummary, WfoDetail, CreateWfoRequest, Strategy, CoinSummary } from "../api/types";
import CreateWfoModal from "../components/CreateWfoModal";

const TH = ({ tip, children }: { tip: string; children: React.ReactNode }) => (
  <Tooltip label={tip} withArrow position="top" multiline w={260}>
    <Table.Th style={{ cursor: "help", whiteSpace: "nowrap" }}>{children}</Table.Th>
  </Tooltip>
);

export default function WfAnalysisPage() {
  const [createModalOpened, setCreateModalOpened] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
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
                  <Table.Td>
                    <Button size="xs" variant="light" onClick={() => setSelectedRunId(wfo.run_id)}>
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
        onClose={() => setSelectedRunId(null)}
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
            </div>

            <Group gap="sm">
              <Badge color={getStatusColor(detailQuery.data.status)} size="sm">{detailQuery.data.status}</Badge>
              <Text size="xs" c="dimmed">{detailQuery.data.total_folds} folds | Progress: {detailQuery.data.progress}%</Text>
              {detailQuery.data.constraint && (
                <Text size="xs" c="dimmed">| Constraint: <code>{detailQuery.data.constraint}</code></Text>
              )}
              {detailQuery.data.error && <Text size="xs" c="red">| {detailQuery.data.error}</Text>}
            </Group>

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
                    <TH tip="Total number of closed trades during the test period">Test Trades</TH>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {detailQuery.data.folds.map((fold) => {
                    const m = fold.metrics || {};
                    const cash = detailQuery.data.cash ?? 10000;
                    const finalVal = m.final as number | undefined;
                    const isProfitable = finalVal != null && finalVal > cash;
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
                        <Table.Td>{(m.total_closed as number) ?? "—"}</Table.Td>
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
