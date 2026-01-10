import { Button, Card, Grid, Group, Select, Stack, Text, TextInput, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { DateTimePicker } from "@mantine/dates";
import JobProgress from "../components/JobProgress";
import TradesTable from "../components/TradesTable";
import { getJson, postJson } from "../api/client";
import type { BacktestSummary, Strategy, CoinSummary, CreateBacktestJobRequest, RunLogItem } from "../api/types";
import { useState } from "react";

const mockTrades = [
  { id: "1", side: "buy" as const, price: 42000, qty: 0.1, ts: "2025-12-29T10:00Z" },
  { id: "2", side: "sell" as const, price: 42500, qty: 0.1, ts: "2025-12-29T12:00Z" },
];

export default function BacktestsPage() {
  const qc = useQueryClient();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["backtests"],
    queryFn: () => getJson<BacktestSummary[]>("/backtests"),
    refetchInterval: 4000,
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
    },
    onError: (err: Error) => {
      notifications.show({ title: "Backtest enqueue failed", message: err.message, color: "red" });
    },
  });

  const [instrumentId, setInstrumentId] = useState("");
  const [bar, setBar] = useState("1h");
  const [strategyId, setStrategyId] = useState<string | null>(null);
  const [startDt, setStartDt] = useState<Date | null>(null);
  const [endDt, setEndDt] = useState<Date | null>(null);

  const backtests = data ?? [];
  const strategies = strategiesQuery.data ?? [];
  const coins = coinsQuery.data ?? [];
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  const logsQuery = useQuery({
    queryKey: ["backtest-logs", selectedRunId],
    queryFn: () => getJson<RunLogItem[]>(`/backtests/${selectedRunId}/logs`),
    enabled: selectedRunId !== null,
    refetchInterval: 4000,
  });

  return (
    <Stack gap="md">
      <Title order={3}>Backtests</Title>
      <Card withBorder radius="md" className="panel">
        <Stack gap="sm">
          <Text fw={600}>Start backtest</Text>
          <Group grow>
            <Select
              label="Strategy"
              placeholder="Select strategy"
              data={strategies.map((s) => ({ value: String(s.id), label: `${s.name} (${s.status})` }))}
              value={strategyId}
              onChange={setStrategyId}
              searchable
              nothingFoundMessage="No strategies"
            />
            <Select
              label="Instrument"
              placeholder="Select instrument"
              data={coins.map((c) => ({ value: c.instrument_id, label: c.instrument_id }))}
              value={instrumentId}
              onChange={(v) => setInstrumentId(v || "")}
              searchable
              nothingFoundMessage="No instruments"
            />
            <TextInput label="Bar" value={bar} onChange={(e) => setBar(e.currentTarget.value)} placeholder="1h" />
          </Group>
          <Group grow>
            <DateTimePicker
              label="Start"
              placeholder="Pick start"
              value={startDt}
              onChange={setStartDt}
              valueFormat="YYYY-MM-DD HH:mm"
            />
            <DateTimePicker
              label="End"
              placeholder="Pick end"
              value={endDt}
              onChange={setEndDt}
              valueFormat="YYYY-MM-DD HH:mm"
            />
          </Group>
          <Group justify="flex-end">
            <Button
              onClick={() => {
                if (!strategyId || !instrumentId || !bar) {
                  notifications.show({ title: "Missing fields", message: "Select strategy, instrument, and bar", color: "yellow" });
                  return;
                }
                const start_ts = startDt ? startDt.toISOString() : undefined;
                const end_ts = endDt ? endDt.toISOString() : undefined;
                createMutation.mutate({
                  strategy_id: Number(strategyId),
                  instrument_id: instrumentId,
                  bar,
                  ...(start_ts ? { start_ts } : {}),
                  ...(end_ts ? { end_ts } : {}),
                });
              }}
              loading={createMutation.isPending}
            >
              Enqueue
            </Button>
          </Group>
        </Stack>
      </Card>
      {isError && (
        <Card withBorder radius="md" className="panel">
          <Text c="red">Failed to load backtests: {(error as Error).message}</Text>
        </Card>
      )}
      <Grid>
        {isLoading && <Text c="dimmed">Loading...</Text>}
        {!isLoading &&
          backtests.map((bt) => (
            <Grid.Col key={bt.run_id} span={{ base: 12, md: 6 }}>
              <JobProgress
                label={`${bt.strategy_name ?? "Strategy"} - ${bt.instrument_id} (${bt.bar})`}
                percent={bt.progress ?? 0}
                status={bt.status as any}
              />
              <Group justify="space-between" mt="xs">
                <Text size="sm" c="dimmed">
                  Run #{bt.run_id}
                </Text>
                <Button size="xs" variant="light" onClick={() => setSelectedRunId(bt.run_id)}>
                  View logs
                </Button>
              </Group>
              {bt.error && (
                <Text size="sm" c="red" mt="xs">
                  {bt.error}
                </Text>
              )}
            </Grid.Col>
          ))}
        {!isLoading && backtests.length === 0 && <Text c="dimmed">No backtests yet.</Text>}
      </Grid>
      {selectedRunId && (
        <Card withBorder radius="md" className="panel">
          <Group justify="space-between" mb="xs">
            <Text fw={600}>Logs for run #{selectedRunId}</Text>
            <Button size="xs" variant="subtle" onClick={() => setSelectedRunId(null)}>
              Close
            </Button>
          </Group>
          {logsQuery.isLoading && <Text c="dimmed">Loading logs...</Text>}
          {logsQuery.isError && <Text c="red">Failed to load logs</Text>}
          {!logsQuery.isLoading && logsQuery.data && (
            <Stack gap={4} style={{ maxHeight: 240, overflowY: "auto" }}>
              {logsQuery.data.map((log, idx) => (
                <Text key={idx} size="sm">
                  <Text span c="dimmed">
                    {new Date(log.ts).toISOString()} [{log.level}]
                  </Text>{" "}
                  {log.message}
                </Text>
              ))}
              {logsQuery.data.length === 0 && <Text c="dimmed">No logs yet.</Text>}
            </Stack>
          )}
        </Card>
      )}
      <TradesTable trades={mockTrades} />
    </Stack>
  );
}
