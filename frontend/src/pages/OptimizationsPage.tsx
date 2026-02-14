import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button, Group, Stack, Title, Table, Badge, Modal, Text, Loader, Progress } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import type { OptimizationSummary, OptimizationDetail, CreateOptimizationRequest, Strategy, CoinSummary } from "../api/types";
import CreateOptimizationModal from "../components/CreateOptimizationModal";

export default function OptimizationsPage() {
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
    refetchInterval: 5000, // Poll every 5s
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
      if (data?.status === "running" || data?.status === "queued") {
        return 5000; // Poll while running
      }
      return false; // Don't poll when completed
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
      notifications.show({
        title: "Optimization queued",
        message: "Optimization job has been queued successfully",
        color: "green",
      });
      qc.invalidateQueries({ queryKey: ["optimizations"] });
      setCreateModalOpened(false);
    },
    onError: (error: Error) => {
      notifications.show({
        title: "Failed to create optimization",
        message: error.message,
        color: "red",
      });
    },
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case "succeeded":
        return "green";
      case "failed":
        return "red";
      case "running":
        return "blue";
      case "queued":
        return "gray";
      default:
        return "gray";
    }
  };

  return (
    <Stack gap="md" style={{ height: "calc(100vh - 100px)", display: "flex", flexDirection: "column" }}>
      <Group justify="space-between">
        <Title order={3}>Optimizations</Title>
        <Button onClick={() => setCreateModalOpened(true)}>New Optimization</Button>
      </Group>

      {optimizationsQuery.isLoading && (
        <div style={{ display: "flex", justifyContent: "center", padding: "40px" }}>
          <Loader />
        </div>
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
                  <Table.Td>
                    <Badge color={getStatusColor(opt.status)}>{opt.status}</Badge>
                  </Table.Td>
                  <Table.Td>
                    <Progress value={opt.progress} size="sm" style={{ width: "80px" }} />
                  </Table.Td>
                  <Table.Td>{opt.total_variants ?? "—"}</Table.Td>
                  <Table.Td>
                    {opt.best_final_value !== null && opt.best_final_value !== undefined
                      ? `$${opt.best_final_value.toFixed(2)}`
                      : "—"}
                  </Table.Td>
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
        size="xl"
      >
        {detailQuery.isLoading && (
          <div style={{ display: "flex", justifyContent: "center", padding: "40px" }}>
            <Loader />
          </div>
        )}

        {detailQuery.error && <Text c="red">Failed to load results: {(detailQuery.error as Error).message}</Text>}

        {detailQuery.data && (
          <Stack gap="md">
            {/* Summary */}
            <div>
              <Text size="sm" c="dimmed">
                Strategy: {detailQuery.data.strategy_name} | Instrument: {detailQuery.data.instrument_id} | Bar:{" "}
                {detailQuery.data.bar}
              </Text>
              <Text size="sm" c="dimmed">
                Status: <Badge color={getStatusColor(detailQuery.data.status)}>{detailQuery.data.status}</Badge> |
                Total Variants: {detailQuery.data.total_variants} | Progress: {detailQuery.data.progress}%
              </Text>
              {detailQuery.data.constraint && (
                <Text size="sm" c="dimmed">
                  Constraint: {detailQuery.data.constraint}
                </Text>
              )}
            </div>

            {/* Variants Table */}
            <div style={{ maxHeight: "500px", overflow: "auto" }}>
              <Table striped highlightOnHover fontSize="xs">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Rank</Table.Th>
                    <Table.Th>Parameters</Table.Th>
                    <Table.Th>Final Value</Table.Th>
                    <Table.Th>Sharpe</Table.Th>
                    <Table.Th>Max DD</Table.Th>
                    <Table.Th>Win Rate</Table.Th>
                    <Table.Th>PF</Table.Th>
                    <Table.Th>SQN</Table.Th>
                    <Table.Th>Trades</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {detailQuery.data.variants.map((variant, idx) => (
                    <Table.Tr key={variant.id}>
                      <Table.Td>#{idx + 1}</Table.Td>
                      <Table.Td>
                        <Text size="xs" style={{ fontFamily: "monospace" }}>
                          {JSON.stringify(variant.variant_params)}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Text size="xs" fw={idx === 0 ? 700 : 400} c={idx === 0 ? "green" : undefined}>
                          {variant.final_value !== null && variant.final_value !== undefined
                            ? `$${variant.final_value.toFixed(2)}`
                            : "—"}
                        </Text>
                      </Table.Td>
                      <Table.Td>{variant.sharpe !== null ? variant.sharpe.toFixed(3) : "—"}</Table.Td>
                      <Table.Td>
                        {variant.maxdd !== null && variant.maxdd !== undefined ? `${variant.maxdd.toFixed(2)}%` : "—"}
                      </Table.Td>
                      <Table.Td>
                        {variant.winrate !== null && variant.winrate !== undefined ? `${variant.winrate.toFixed(2)}%` : "—"}
                      </Table.Td>
                      <Table.Td>{variant.profit_factor !== null ? variant.profit_factor.toFixed(2) : "—"}</Table.Td>
                      <Table.Td>{variant.sqn !== null ? variant.sqn.toFixed(2) : "—"}</Table.Td>
                      <Table.Td>{variant.total_trades ?? "—"}</Table.Td>
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
    </Stack>
  );
}
