import { Card, Group, Stack, Text, Title } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import StrategyForm from "../components/StrategyForm";
import { getJson, postJson } from "../api/client";
import type { CreateStrategyRequest, Strategy } from "../api/types";

export default function StrategiesPage() {
  const qc = useQueryClient();

  const strategiesQuery = useQuery({
    queryKey: ["strategies"],
    queryFn: () => getJson<Strategy[]>("/strategies"),
  });

  const createMutation = useMutation({
    mutationFn: (body: CreateStrategyRequest) => postJson<Strategy>("/strategies", body),
    onSuccess: () => {
      notifications.show({ title: "Strategy created", message: "Saved successfully", color: "green" });
      qc.invalidateQueries({ queryKey: ["strategies"] });
    },
    onError: (err: Error) => {
      notifications.show({ title: "Failed to create", message: err.message, color: "red" });
    },
  });

  const strategies = strategiesQuery.data ?? [];

  return (
    <Stack gap="md">
      <Title order={3}>Strategies</Title>
      <Group align="flex-start" grow>
        <StrategyForm
          submitting={createMutation.isPending}
          onSubmit={(vals) =>
            createMutation.mutateAsync({
              name: vals.name,
              status: vals.status,
              notes: vals.notes,
              code: vals.code,
            })
          }
        />
        <Stack gap="sm" style={{ minWidth: 320 }}>
          {strategiesQuery.isLoading && <Text c="dimmed">Loading...</Text>}
          {strategiesQuery.isError && (
            <Card withBorder radius="md" className="panel">
              <Text c="red">Failed to load strategies: {(strategiesQuery.error as Error).message}</Text>
            </Card>
          )}
          {!strategiesQuery.isLoading &&
            strategies.map((s) => (
              <Card key={s.id} withBorder radius="md" className="panel">
                <Text fw={600}>{s.name}</Text>
                <Text size="sm" c="dimmed">
                  {s.status.toUpperCase()}
                </Text>
                {s.notes && (
                  <Text size="sm" mt="xs">
                    {s.notes}
                  </Text>
                )}
              </Card>
            ))}
        </Stack>
      </Group>
    </Stack>
  );
}
