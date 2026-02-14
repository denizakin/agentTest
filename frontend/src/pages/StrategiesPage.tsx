import { Button, Card, Group, Stack, Text, Title, Table, Modal, Badge } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import StrategyForm from "../components/StrategyForm";
import { getJson, postJson, patchJson } from "../api/client";
import type { CreateStrategyRequest, Strategy } from "../api/types";

export default function StrategiesPage() {
  const qc = useQueryClient();
  const [modalOpened, setModalOpened] = useState(false);
  const [editingStrategy, setEditingStrategy] = useState<Strategy | null>(null);

  const strategiesQuery = useQuery({
    queryKey: ["strategies"],
    queryFn: () => getJson<Strategy[]>("/strategies"),
  });

  const createMutation = useMutation({
    mutationFn: (body: CreateStrategyRequest) => postJson<Strategy>("/strategies", body),
    onSuccess: () => {
      notifications.show({ title: "Strategy created", message: "Saved successfully", color: "green" });
      qc.invalidateQueries({ queryKey: ["strategies"] });
      setModalOpened(false);
    },
    onError: (err: Error) => {
      notifications.show({ title: "Failed to create", message: err.message, color: "red" });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Partial<CreateStrategyRequest> }) =>
      patchJson<Strategy>(`/strategies/${id}`, body),
    onSuccess: () => {
      notifications.show({ title: "Strategy updated", message: "Updated successfully", color: "green" });
      qc.invalidateQueries({ queryKey: ["strategies"] });
      setModalOpened(false);
      setEditingStrategy(null);
    },
    onError: (err: Error) => {
      notifications.show({ title: "Failed to update", message: err.message, color: "red" });
    },
  });

  const strategies = strategiesQuery.data ?? [];

  const handleOpenCreateModal = () => {
    setEditingStrategy(null);
    setModalOpened(true);
  };

  const handleOpenEditModal = (strategy: Strategy) => {
    setEditingStrategy(strategy);
    setModalOpened(true);
  };

  const handleCloseModal = () => {
    setModalOpened(false);
    setEditingStrategy(null);
  };

  const handleSubmit = async (vals: CreateStrategyRequest) => {
    if (editingStrategy) {
      await updateMutation.mutateAsync({
        id: editingStrategy.id,
        body: vals,
      });
    } else {
      await createMutation.mutateAsync(vals);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "prod":
        return "green";
      case "draft":
        return "blue";
      case "archived":
        return "gray";
      default:
        return "gray";
    }
  };

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Strategies</Title>
        <Button onClick={handleOpenCreateModal}>Create Strategy</Button>
      </Group>

      {strategiesQuery.isLoading && <Text c="dimmed">Loading...</Text>}
      {strategiesQuery.isError && (
        <Card withBorder radius="md" className="panel">
          <Text c="red">Failed to load strategies: {(strategiesQuery.error as Error).message}</Text>
        </Card>
      )}

      {!strategiesQuery.isLoading && strategies.length === 0 && (
        <Card withBorder radius="md" className="panel">
          <Text c="dimmed">No strategies yet. Create your first strategy!</Text>
        </Card>
      )}

      {!strategiesQuery.isLoading && strategies.length > 0 && (
        <Table highlightOnHover>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Name</Table.Th>
              <Table.Th>Status</Table.Th>
              <Table.Th>Tag</Table.Th>
              <Table.Th>Notes</Table.Th>
              <Table.Th>Actions</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {strategies.map((strategy) => (
              <Table.Tr key={strategy.id}>
                <Table.Td>
                  <Text fw={600}>{strategy.name}</Text>
                </Table.Td>
                <Table.Td>
                  <Badge color={getStatusColor(strategy.status)}>{strategy.status.toUpperCase()}</Badge>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c="dimmed">
                    {strategy.tag || "-"}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Text size="sm" c="dimmed" lineClamp={1}>
                    {strategy.notes || "-"}
                  </Text>
                </Table.Td>
                <Table.Td>
                  <Button size="xs" variant="light" onClick={() => handleOpenEditModal(strategy)}>
                    Edit
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal
        opened={modalOpened}
        onClose={handleCloseModal}
        title={editingStrategy ? "Edit Strategy" : "Create Strategy"}
        size="calc(100vw - 100px)"
        styles={{
          body: { padding: "20px" },
          header: { padding: "20px" },
        }}
      >
        <StrategyForm
          submitting={createMutation.isPending || updateMutation.isPending}
          onSubmit={handleSubmit}
          defaultValues={
            editingStrategy
              ? {
                  name: editingStrategy.name,
                  status: editingStrategy.status as "draft" | "prod" | "archived",
                  tag: editingStrategy.tag || "",
                  notes: editingStrategy.notes || "",
                  code: editingStrategy.code || "",
                }
              : undefined
          }
          submitLabel={editingStrategy ? "Update" : "Create"}
        />
      </Modal>
    </Stack>
  );
}
