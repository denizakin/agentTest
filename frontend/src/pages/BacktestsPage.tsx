import { Button, Card, Group, Modal, Stack, Text, Title, Table, Select, Checkbox } from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { IconRefresh } from "@tabler/icons-react";
import JobProgress from "../components/JobProgress";
import { getJson, postJson } from "../api/client";
import type { BacktestSummary, Strategy, CoinSummary, CreateBacktestJobRequest, RunLogItem, RunResultItem } from "../api/types";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import BacktestDetailModal from "../components/BacktestDetailModal";
import CreateBacktestModal, { type BacktestParams } from "../components/CreateBacktestModal";

export default function BacktestsPage() {
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [createModalOpened, setCreateModalOpened] = useState(false);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<"chart" | "logs" | null>(null);
  const [resultsMap, setResultsMap] = useState<Record<number, RunResultItem[]>>({});

  // Auto-open from URL param ?run=123
  useEffect(() => {
    const runParam = searchParams.get("run");
    if (runParam) {
      const runId = parseInt(runParam, 10);
      if (!isNaN(runId)) {
        setSelectedRunId(runId);
        setViewMode("chart");
        // Clear the param so it doesn't re-trigger
        searchParams.delete("run");
        setSearchParams(searchParams, { replace: true });
      }
    }
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  // Filter states
  const [filterStrategy, setFilterStrategy] = useState<string | null>(null);
  const [filterInstrument, setFilterInstrument] = useState<string | null>(null);
  const [filterStartDate, setFilterStartDate] = useState<Date | null>(null);
  const [filterEndDate, setFilterEndDate] = useState<Date | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["backtests"],
    queryFn: () => getJson<BacktestSummary[]>("/backtests"),
    refetchInterval: autoRefresh ? 4000 : false,
  });

  const strategiesQuery = useQuery({
    queryKey: ["strategies"],
    queryFn: () => getJson<Strategy[]>("/strategies"),
  });

  const coinsQuery = useQuery({
    queryKey: ["coins"],
    queryFn: () => getJson<CoinSummary[]>("/coins/top"),
  });

  const createMutation = useMutation({
    mutationFn: (body: CreateBacktestJobRequest) => postJson<BacktestSummary>("/jobs/backtest", body),
    onSuccess: () => {
      notifications.show({ title: "Backtest enqueued", message: "Job queued", color: "green" });
      qc.invalidateQueries({ queryKey: ["backtests"] });
      setCreateModalOpened(false);  // Close modal after successful submission
    },
    onError: (err: Error) => {
      notifications.show({ title: "Backtest enqueue failed", message: err.message, color: "red" });
    },
  });

  const logsQuery = useQuery({
    queryKey: ["backtest-logs", selectedRunId],
    queryFn: () => getJson<RunLogItem[]>(`/backtests/${selectedRunId}/logs`),
    enabled: selectedRunId !== null && viewMode === "logs",
    refetchInterval: 4000,
  });

  const resultsQuery = useQuery({
    queryKey: ["backtest-results", selectedRunId],
    queryFn: () => getJson<RunResultItem[]>(`/backtests/${selectedRunId}/results`),
    enabled: selectedRunId !== null,
    refetchInterval: 4000,
  });

  useEffect(() => {
    if (selectedRunId && resultsQuery.data) {
      setResultsMap((prev) => ({ ...prev, [selectedRunId]: resultsQuery.data }));
    }
  }, [resultsQuery.data, selectedRunId]);

  // Preload results for completed runs
  useEffect(() => {
    const loadAll = async () => {
      if (!data?.length) return;
      const entries = await Promise.all(
        data.map(async (bt) => {
          try {
            const res = await getJson<RunResultItem[]>(`/backtests/${bt.run_id}/results`);
            return [bt.run_id, res] as const;
          } catch {
            return null;
          }
        })
      );
      setResultsMap((prev) => {
        const next = { ...prev };
        for (const item of entries) {
          if (!item) continue;
          const [runId, res] = item;
          next[runId] = res;
        }
        return next;
      });
    };
    loadAll();
  }, [data]);

  const backtests = data ?? [];
  const strategies = strategiesQuery.data ?? [];
  const coins = coinsQuery.data ?? [];

  // Apply filters
  const filteredBacktests = backtests.filter((bt) => {
    if (filterStrategy && bt.strategy_id !== Number(filterStrategy)) return false;
    if (filterInstrument && bt.instrument_id !== filterInstrument) return false;
    if (filterStartDate && bt.start_ts) {
      const btStart = new Date(bt.start_ts);
      if (btStart < filterStartDate) return false;
    }
    if (filterEndDate && bt.end_ts) {
      const btEnd = new Date(bt.end_ts);
      if (btEnd > filterEndDate) return false;
    }
    return true;
  });

  const renderMetric = (value: unknown) => {
    if (value === undefined || value === null || value === "") {
      return (
        <Text size="sm" c="dimmed">
          -
        </Text>
      );
    }
    if (typeof value === "number" && Number.isFinite(value)) {
      return <Text size="sm">{value.toFixed(2)}</Text>;
    }
    return <Text size="sm">{String(value)}</Text>;
  };

  const getMetrics = (runId: number) => {
    const results = resultsMap[runId];
    if (!results) return {};
    const main = results.find((r) => !r.label.toLowerCase().includes("baseline"));
    const baseline = results.find((r) => r.label.toLowerCase().includes("baseline") || r.label.toLowerCase().includes("buy"));
    const mainMetrics = main?.metrics as any;
    const baselineMetrics = baseline?.metrics as any;
    const finalMain = Number(mainMetrics?.final);
    const finalBaseline = Number(baselineMetrics?.final);
    const hasEdge = !Number.isNaN(finalMain) && !Number.isNaN(finalBaseline);
    const edgeAbs = hasEdge ? finalMain - finalBaseline : null;
    const edgePct = hasEdge && finalBaseline !== 0 ? (edgeAbs / finalBaseline) * 100 : null;
    const plotPath = main?.plot_path || baseline?.plot_path;
    return { main: mainMetrics, baseline: baselineMetrics, edgeAbs, edgePct, plotPath };
  };

  const plotUrl = (path?: string) => {
    if (!path) return undefined;
    const normalized = path.replace(/\\/g, "/");
    const prefix = "resources/plots/";
    if (normalized.includes(prefix)) {
      const fname = normalized.slice(normalized.indexOf(prefix) + prefix.length);
      return `/plots/${fname}`;
    }
    return path;
  };

  const handleCreateBacktest = async (params: BacktestParams) => {
    const instruments = params.instrument_ids || [params.instrument_id];

    // Create a backtest job for each selected instrument
    let successCount = 0;
    let failCount = 0;

    for (const instrumentId of instruments) {
      try {
        await createMutation.mutateAsync({
          strategy_id: params.strategy_id,
          instrument_id: instrumentId,
          bar: params.bar,
          params: {
            ...(params.start_ts ? { start_ts: params.start_ts } : {}),
            ...(params.end_ts ? { end_ts: params.end_ts } : {}),
            ...(params.cash !== undefined ? { cash: params.cash } : {}),
            ...(params.commission !== undefined ? { commission: params.commission } : {}),
            ...(params.stake !== undefined ? { stake: params.stake } : {}),
            use_sizer: params.use_sizer,
            coc: params.coc,
            baseline: params.baseline,
            parallel_baseline: params.parallel_baseline,
            slip_perc: params.slip_perc,
            slip_fixed: params.slip_fixed,
            slip_open: params.slip_open,
            refresh: params.refresh,
            plot: params.plot,
            // Include strategy-specific parameters
            ...(params.params || {}),
          },
        });
        successCount++;
      } catch (err) {
        failCount++;
        console.error(`Failed to enqueue backtest for ${instrumentId}:`, err);
      }
    }

    // Show summary notification
    if (successCount > 0) {
      notifications.show({
        title: "Backtests enqueued",
        message: `${successCount} backtest${successCount > 1 ? "s" : ""} queued successfully${failCount > 0 ? `, ${failCount} failed` : ""}`,
        color: failCount > 0 ? "yellow" : "green",
      });
      qc.invalidateQueries({ queryKey: ["backtests"] });
      setCreateModalOpened(false);
    } else {
      notifications.show({
        title: "Backtest enqueue failed",
        message: `All ${failCount} backtest${failCount > 1 ? "s" : ""} failed to enqueue`,
        color: "red",
      });
    }
  };

  return (
    <Stack gap="md" style={{ height: "calc(100vh - 100px)", display: "flex", flexDirection: "column" }}>
      <Group justify="space-between">
        <Title order={3}>Backtests</Title>
        <Button onClick={() => setCreateModalOpened(true)}>New Backtest</Button>
      </Group>

      <CreateBacktestModal
        opened={createModalOpened}
        onClose={() => setCreateModalOpened(false)}
        onSubmit={handleCreateBacktest}
        strategies={strategies}
        coins={coins}
        isLoading={createMutation.isPending}
      />

      {/* Filters */}
      <Card withBorder radius="md" className="panel">
        <Stack gap="sm">
          <Group justify="space-between" align="center">
            <Text fw={600}>Filters</Text>
            <Group gap="sm">
              <Checkbox label="Auto refresh" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.currentTarget.checked)} />
              <Button size="xs" variant="light" leftSection={<IconRefresh size={16} />} onClick={() => refetch()}>
                Refresh
              </Button>
            </Group>
          </Group>
          <Group grow>
            <Select
              label="Strategy"
              placeholder="All strategies"
              data={[
                { value: "", label: "All strategies" },
                ...strategies.map((s) => ({ value: String(s.id), label: `${s.name}` })),
              ]}
              value={filterStrategy}
              onChange={setFilterStrategy}
              clearable
            />
            <Select
              label="Instrument"
              placeholder="All instruments"
              data={[
                { value: "", label: "All instruments" },
                ...Array.from(new Set(backtests.map((bt) => bt.instrument_id))).map((inst) => ({ value: inst, label: inst })),
              ]}
              value={filterInstrument}
              onChange={setFilterInstrument}
              clearable
            />
            <DateTimePicker
              label="Begin Date (from)"
              placeholder="Any start date"
              value={filterStartDate}
              onChange={setFilterStartDate}
              valueFormat="YYYY-MM-DD HH:mm"
              clearable
            />
            <DateTimePicker
              label="End Date (to)"
              placeholder="Any end date"
              value={filterEndDate}
              onChange={setFilterEndDate}
              valueFormat="YYYY-MM-DD HH:mm"
              clearable
            />
          </Group>
        </Stack>
      </Card>

      {isError && (
        <Card withBorder radius="md" className="panel">
          <Text c="red">Failed to load backtests: {(error as Error).message}</Text>
        </Card>
      )}

      <Card withBorder radius="md" className="panel" style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {isLoading && <Text c="dimmed">Loading...</Text>}
        {!isLoading && backtests.length === 0 && <Text c="dimmed">No backtests yet. Click "New Backtest" to get started.</Text>}
        {!isLoading && filteredBacktests.length === 0 && backtests.length > 0 && <Text c="dimmed">No backtests match the current filters.</Text>}
        {!isLoading && filteredBacktests.length > 0 && (
          <div style={{ flex: 1, overflowY: "auto", overflowX: "auto" }}>
            <Table striped highlightOnHover withRowBorders={false} horizontalSpacing="sm" verticalSpacing="xs" style={{ fontSize: "14px" }}>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Run</Table.Th>
                  <Table.Th>Strategy</Table.Th>
                  <Table.Th>Instrument</Table.Th>
                  <Table.Th>Bar</Table.Th>
                  <Table.Th>Params</Table.Th>
                  <Table.Th>Start</Table.Th>
                  <Table.Th>End</Table.Th>
                  <Table.Th>Status</Table.Th>
                  <Table.Th>Progress</Table.Th>
                  <Table.Th>Final</Table.Th>
                  <Table.Th>Buy&Hold</Table.Th>
                  <Table.Th>Edge</Table.Th>
                  <Table.Th>Sharpe</Table.Th>
                  <Table.Th>MaxDD</Table.Th>
                  <Table.Th>Trades</Table.Th>
                  <Table.Th>Win rate</Table.Th>
                  <Table.Th>Actions</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {filteredBacktests.map((bt) => {
                  const { main, baseline, edgeAbs, edgePct, plotPath } = getMetrics(bt.run_id);
                  const formatEdge = () => {
                    if (edgeAbs === null || edgeAbs === undefined) {
                      return renderMetric(undefined);
                    }
                    const absStr = typeof edgeAbs === "number" ? edgeAbs.toFixed(2) : String(edgeAbs);
                    if (edgePct === null || edgePct === undefined) {
                      return <Text size="sm">{absStr}</Text>;
                    }
                    const pctStr = typeof edgePct === "number" ? edgePct.toFixed(2) : String(edgePct);
                    return (
                      <Text size="sm">
                        {absStr} ({pctStr}%)
                      </Text>
                    );
                  };
                  return (
                    <Table.Tr key={bt.run_id}>
                      <Table.Td>#{bt.run_id}</Table.Td>
                      <Table.Td>{bt.strategy_name ?? "Strategy"}</Table.Td>
                      <Table.Td>{bt.instrument_id}</Table.Td>
                      <Table.Td>{bt.bar}</Table.Td>
                      <Table.Td>
                        <Text size="xs" style={{ fontFamily: "monospace", whiteSpace: "nowrap" }}>
                          {bt.strategy_params && Object.keys(bt.strategy_params).length > 0
                            ? Object.entries(bt.strategy_params).map(([k, v]) => `${k}=${v}`).join(", ")
                            : "—"}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">{bt.start_ts ? new Date(bt.start_ts).toLocaleDateString() : "-"}</Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs">{bt.end_ts ? new Date(bt.end_ts).toLocaleDateString() : "-"}</Text>
                      </Table.Td>
                      <Table.Td>{bt.status}</Table.Td>
                      <Table.Td>
                        <JobProgress label="" percent={bt.progress ?? 0} status={bt.status as any} />
                      </Table.Td>
                      <Table.Td>{renderMetric(main?.final)}</Table.Td>
                      <Table.Td>{renderMetric(baseline?.final)}</Table.Td>
                      <Table.Td>{formatEdge()}</Table.Td>
                      <Table.Td>{renderMetric(main?.sharpe)}</Table.Td>
                      <Table.Td>{renderMetric(main?.maxdd)}</Table.Td>
                      <Table.Td>{renderMetric(main?.closed ?? main?.trades_closed)}</Table.Td>
                      <Table.Td>{renderMetric(main?.winrate)}</Table.Td>
                      <Table.Td>
                        <Group gap={4}>
                          <Button
                            size="xs"
                            variant="light"
                            onClick={() => {
                              setSelectedRunId(bt.run_id);
                              setViewMode("chart");
                            }}
                          >
                            Chart
                          </Button>
                          {plotUrl(plotPath) && (
                            <Button size="xs" variant="light" component="a" href={plotUrl(plotPath)} target="_blank">
                              Plot
                            </Button>
                          )}
                          <Button
                            size="xs"
                            variant="light"
                            onClick={() => {
                              setSelectedRunId(bt.run_id);
                              setViewMode("logs");
                            }}
                          >
                            Logs
                          </Button>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  );
                })}
              </Table.Tbody>
            </Table>
          </div>
        )}
      </Card>

      {/* Chart + Results Modal */}
      <BacktestDetailModal
        runId={viewMode === "chart" ? selectedRunId : null}
        onClose={() => { setViewMode(null); setSelectedRunId(null); }}
      />

      {/* Logs Modal */}
      <Modal
        opened={viewMode === "logs" && selectedRunId !== null}
        onClose={() => {
          setViewMode(null);
          setSelectedRunId(null);
        }}
        title={`Logs for run #${selectedRunId}`}
        size="xl"
      >
        {logsQuery.isLoading && <Text c="dimmed">Loading logs...</Text>}
        {logsQuery.isError && <Text c="red">Failed to load logs</Text>}
        {!logsQuery.isLoading && logsQuery.data && (
          <Stack gap={4} style={{ maxHeight: 500, overflowY: "auto" }}>
            {logsQuery.data.map((log, idx) => (
              <Text key={idx} size="sm" style={{ fontFamily: "monospace" }}>
                <Text span c="dimmed">
                  {new Date(log.ts).toISOString()} [{log.level}]
                </Text>{" "}
                {log.message}
              </Text>
            ))}
            {logsQuery.data.length === 0 && <Text c="dimmed">No logs yet.</Text>}
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}
