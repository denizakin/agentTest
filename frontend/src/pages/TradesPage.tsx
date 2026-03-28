import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Group,
  Loader,
  Modal,
  NumberInput,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  Textarea,
  Title,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import type {
  TradeDefinition,
  TradeDefinitionStatus,
  CreateTradeDefinitionRequest,
  Strategy,
  CoinSummary,
  Account,
} from "../api/types";

const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d", "1w"];

const STATUS_COLORS: Record<TradeDefinitionStatus, string> = {
  active: "green",
  paused: "yellow",
  stopped: "red",
};

export default function TradesPage() {
  const [createOpened, setCreateOpened] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const qc = useQueryClient();

  const tradesQuery = useQuery<TradeDefinition[]>({
    queryKey: ["trade-definitions"],
    queryFn: async () => {
      const res = await fetch("/api/trades");
      if (!res.ok) throw new Error("Failed to fetch trade definitions");
      return res.json();
    },
    refetchInterval: 10000,
  });

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

  const createMutation = useMutation({
    mutationFn: async (payload: CreateTradeDefinitionRequest) => {
      const res = await fetch("/api/trades", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || "Failed to create trade definition");
      }
      return res.json();
    },
    onSuccess: () => {
      notifications.show({ title: "Trade definition created", message: "", color: "green" });
      qc.invalidateQueries({ queryKey: ["trade-definitions"] });
      setCreateOpened(false);
    },
    onError: (err: Error) => {
      notifications.show({ title: "Error", message: err.message, color: "red" });
    },
  });

  const statusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: number; status: string }) => {
      const res = await fetch(`/api/trades/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error("Failed to update status");
      return res.json();
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["trade-definitions"] });
    },
    onError: (err: Error) => {
      notifications.show({ title: "Error", message: err.message, color: "red" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => {
      const res = await fetch(`/api/trades/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Failed to delete");
    },
    onSuccess: () => {
      notifications.show({ title: "Deleted", message: "", color: "gray" });
      qc.invalidateQueries({ queryKey: ["trade-definitions"] });
      setEditId(null);
    },
    onError: (err: Error) => {
      notifications.show({ title: "Error", message: err.message, color: "red" });
    },
  });

  const accountsQuery = useQuery<Account[]>({
    queryKey: ["accounts"],
    queryFn: async () => {
      const res = await fetch("/api/accounts");
      if (!res.ok) throw new Error("Failed to fetch accounts");
      return res.json();
    },
  });

  const strategies = strategiesQuery.data || [];
  const coins = coinsQuery.data || [];
  const accounts = accountsQuery.data || [];
  const editItem = editId ? tradesQuery.data?.find((t) => t.id === editId) : null;

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Trade Definitions</Title>
        <Button onClick={() => setCreateOpened(true)}>New Trade Definition</Button>
      </Group>

      <Text size="sm" c="dimmed">
        Trade definitions specify which strategy to run on which instrument and timeframe.
        The trade worker will execute active definitions automatically.
      </Text>

      {tradesQuery.isLoading && (
        <div style={{ display: "flex", justifyContent: "center", padding: "40px" }}>
          <Loader />
        </div>
      )}
      {tradesQuery.isError && (
        <Text c="red">Failed to load trade definitions: {(tradesQuery.error as Error).message}</Text>
      )}

      {tradesQuery.data && tradesQuery.data.length === 0 && (
        <Text c="dimmed" style={{ textAlign: "center", padding: "40px" }}>
          No trade definitions yet. Create one to get started.
        </Text>
      )}

      {tradesQuery.data && tradesQuery.data.length > 0 && (
        <Table striped highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ID</Table.Th>
              <Table.Th>Strategy</Table.Th>
              <Table.Th>Account</Table.Th>
              <Table.Th>Instrument</Table.Th>
              <Table.Th>Timeframe</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Notes</Table.Th>
              <Table.Th>Created</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {tradesQuery.data.map((td) => (
              <Table.Tr key={td.id}>
                <Table.Td>{td.id}</Table.Td>
                <Table.Td>{td.strategy_name}</Table.Td>
                <Table.Td>
                  {(() => {
                    const acc = td.account_id ? accounts.find((a) => a.id === td.account_id) : null;
                    if (!acc) return <Text size="xs" c="dimmed">—</Text>;
                    return (
                      <Group gap={4} wrap="nowrap">
                        <Text size="xs">{acc.name}</Text>
                        <Badge size="xs" color={acc.is_demo ? "violet" : "teal"} variant="light">
                          {acc.is_demo ? "Demo" : "Real"}
                        </Badge>
                      </Group>
                    );
                  })()}
                </Table.Td>
                <Table.Td>{td.instrument_id}</Table.Td>
                <Table.Td>{td.timeframe}</Table.Td>
                <Table.Td>
                  <Badge color={STATUS_COLORS[td.status]}>{td.status}</Badge>
                </Table.Td>
                <Table.Td>
                  <Text size="xs" c="dimmed" lineClamp={1}>
                    {td.notes || "—"}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="xs">{new Date(td.created_at).toLocaleDateString()}</Text>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    {td.status !== "active" && (
                      <Button
                        size="xs"
                        color="green"
                        variant="light"
                        loading={statusMutation.isPending}
                        onClick={() => statusMutation.mutate({ id: td.id, status: "active" })}
                      >
                        Activate
                      </Button>
                    )}
                    {td.status === "active" && (
                      <Button
                        size="xs"
                        color="yellow"
                        variant="light"
                        loading={statusMutation.isPending}
                        onClick={() => statusMutation.mutate({ id: td.id, status: "paused" })}
                      >
                        Pause
                      </Button>
                    )}
                    {td.status !== "stopped" && (
                      <Button
                        size="xs"
                        color="red"
                        variant="light"
                        loading={statusMutation.isPending}
                        onClick={() => statusMutation.mutate({ id: td.id, status: "stopped" })}
                      >
                        Stop
                      </Button>
                    )}
                    <Button
                      size="xs"
                      variant="subtle"
                      color="gray"
                      onClick={() => setEditId(td.id)}
                    >
                      Edit
                    </Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      {/* Create Modal */}
      <CreateTradeModal
        opened={createOpened}
        onClose={() => setCreateOpened(false)}
        onSubmit={(data) => createMutation.mutate(data)}
        strategies={strategies}
        coins={coins}
        accounts={accounts}
        isLoading={createMutation.isPending}
      />

      {/* Edit/Delete Modal */}
      <Modal
        opened={!!editItem}
        onClose={() => setEditId(null)}
        title={`Trade Definition #${editItem?.id}`}
        size="sm"
      >
        {editItem && (
          <Stack gap="sm">
            <Text size="sm"><Text span c="dimmed">Strategy:</Text> {editItem.strategy_name}</Text>
            <Text size="sm">
              <Text span c="dimmed">Account:</Text>{" "}
              {editItem.account_id ? (accounts.find((a) => a.id === editItem.account_id)?.name ?? `#${editItem.account_id}`) : <Text span c="dimmed">—</Text>}
            </Text>
            <Text size="sm"><Text span c="dimmed">Instrument:</Text> {editItem.instrument_id}</Text>
            <Text size="sm"><Text span c="dimmed">Timeframe:</Text> {editItem.timeframe}</Text>
            <Text size="sm">
              <Text span c="dimmed">Status:</Text>{" "}
              <Badge color={STATUS_COLORS[editItem.status]}>{editItem.status}</Badge>
            </Text>
            {editItem.notes && <Text size="sm"><Text span c="dimmed">Notes:</Text> {editItem.notes}</Text>}
            <Button
              color="red"
              variant="outline"
              loading={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate(editItem.id)}
            >
              Delete this definition
            </Button>
          </Stack>
        )}
      </Modal>
    </Stack>
  );
}

// ── Create Modal ──────────────────────────────────────────────────────────

type CreateModalProps = {
  opened: boolean;
  onClose: () => void;
  onSubmit: (data: CreateTradeDefinitionRequest) => void;
  strategies: Strategy[];
  coins: CoinSummary[];
  accounts: Account[];
  isLoading: boolean;
};

function CreateTradeModal({ opened, onClose, onSubmit, strategies, coins, accounts, isLoading }: CreateModalProps) {
  const [strategyId, setStrategyId] = useState<string | null>(null);
  const [instrumentId, setInstrumentId] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState<string | null>("1h");
  const [accountId, setAccountId] = useState<string | null>(null);
  const [notes, setNotes] = useState("");
  const [startActive, setStartActive] = useState(false);
  const [paramValues, setParamValues] = useState<Record<string, unknown>>({});

  // Fetch default params when a strategy is selected
  const paramsQuery = useQuery<{ params: Record<string, unknown> }>({
    queryKey: ["strategy-params", strategyId],
    queryFn: async () => {
      const res = await fetch(`/api/backtests/strategies/${strategyId}/params`);
      if (!res.ok) throw new Error("Failed to fetch params");
      return res.json();
    },
    enabled: !!strategyId,
    staleTime: Infinity,
  });

  // When default params arrive, seed paramValues
  const defaultParams = paramsQuery.data?.params ?? {};
  const mergedParams: Record<string, unknown> = { ...defaultParams, ...paramValues };

  const handleStrategyChange = (val: string | null) => {
    setStrategyId(val);
    setParamValues({}); // reset overrides when strategy changes
  };

  const handleParamChange = (key: string, val: unknown) => {
    setParamValues((prev) => ({ ...prev, [key]: val }));
  };

  const handleSubmit = () => {
    if (!strategyId || !instrumentId || !timeframe) return;
    onSubmit({
      strategy_id: Number(strategyId),
      instrument_id: instrumentId,
      timeframe,
      status: startActive ? "active" : "paused",
      params: Object.keys(mergedParams).length > 0 ? mergedParams : undefined,
      notes: notes || undefined,
      account_id: accountId ? Number(accountId) : undefined,
    });
  };

  const handleClose = () => {
    setStrategyId(null);
    setInstrumentId(null);
    setTimeframe("1h");
    setAccountId(null);
    setNotes("");
    setStartActive(false);
    setParamValues({});
    onClose();
  };

  const strategyOptions = strategies.map((s) => ({ value: String(s.id), label: s.name }));
  const coinOptions = coins.map((c) => ({ value: c.instrument_id, label: c.instrument_id + (c.name ? ` (${c.name})` : "") }));
  const tfOptions = TIMEFRAMES.map((t) => ({ value: t, label: t }));
  const accountOptions = accounts.map((a) => ({ value: String(a.id), label: `${a.name} (${a.platform})` }));
  const isValid = !!strategyId && !!instrumentId && !!timeframe;

  return (
    <Modal opened={opened} onClose={handleClose} title="New Trade Definition" size="md">
      <Stack gap="sm">
        <Select
          label="Strategy"
          placeholder="Select strategy"
          data={strategyOptions}
          value={strategyId}
          onChange={handleStrategyChange}
          searchable
          required
        />
        <Select
          label="Instrument"
          placeholder="Select coin/instrument"
          data={coinOptions}
          value={instrumentId}
          onChange={setInstrumentId}
          searchable
          required
        />
        <Select
          label="Timeframe"
          data={tfOptions}
          value={timeframe}
          onChange={setTimeframe}
          required
        />
        <Select
          label="Account"
          placeholder="Select account (optional)"
          data={accountOptions}
          value={accountId}
          onChange={setAccountId}
          searchable
          clearable
        />

        {/* Strategy params */}
        {strategyId && (
          <div>
            <Text size="sm" fw={500} mb={6}>Strategy Parameters</Text>
            {paramsQuery.isLoading && <Loader size="xs" />}
            {paramsQuery.isError && <Text size="xs" c="red">Could not load default params</Text>}
            {Object.keys(defaultParams).length === 0 && !paramsQuery.isLoading && (
              <Text size="xs" c="dimmed">No configurable parameters</Text>
            )}
            <Stack gap={6}>
              {Object.entries(defaultParams).map(([key, defaultVal]) => {
                const current = key in paramValues ? paramValues[key] : defaultVal;
                const isNum = typeof defaultVal === "number";
                return (
                  <Group key={key} gap="xs" align="flex-end">
                    <Text size="xs" style={{ width: 120, paddingBottom: 4 }}>{key}</Text>
                    {isNum ? (
                      <NumberInput
                        size="xs"
                        style={{ flex: 1 }}
                        value={current as number}
                        onChange={(v) => handleParamChange(key, v)}
                        decimalScale={6}
                        step={typeof defaultVal === "number" && defaultVal < 1 ? 0.001 : 1}
                      />
                    ) : (
                      <Text size="xs" c="dimmed" style={{ flex: 1 }}>{String(current)}</Text>
                    )}
                  </Group>
                );
              })}
            </Stack>
          </div>
        )}

        <Textarea
          label="Notes"
          placeholder="Optional notes..."
          value={notes}
          onChange={(e) => setNotes(e.currentTarget.value)}
          rows={2}
        />

        <Switch
          label="Start as Active (trade worker will pick it up immediately)"
          checked={startActive}
          onChange={(e) => setStartActive(e.currentTarget.checked)}
        />

        <Group justify="flex-end" mt="sm">
          <Button variant="default" onClick={handleClose}>Cancel</Button>
          <Button onClick={handleSubmit} loading={isLoading} disabled={!isValid}>
            Create
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
