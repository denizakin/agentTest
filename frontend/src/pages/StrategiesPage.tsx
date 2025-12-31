import { Card, Group, Stack, Text, Title } from "@mantine/core";
import StrategyForm from "../components/StrategyForm";

const mockStrategies = [
  { id: 1, name: "SMA Crossover", status: "draft", notes: "Short window 10/50", code: "" },
  { id: 2, name: "Breakout", status: "prod", notes: "HH/LL breakout", code: "" },
];

export default function StrategiesPage() {
  return (
    <Stack gap="md">
      <Title order={3}>Strategies</Title>
      <Group align="flex-start" grow>
        <StrategyForm onSubmit={(vals) => console.log("submit", vals)} />
        <Stack gap="sm" style={{ minWidth: 320 }}>
          {mockStrategies.map((s) => (
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
