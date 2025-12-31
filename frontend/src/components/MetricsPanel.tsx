import { Card, Group, Stack, Text } from "@mantine/core";

type Metric = {
  label: string;
  value: string | number;
  hint?: string;
};

export default function MetricsPanel({ metrics }: { metrics: Metric[] }) {
  return (
    <Card withBorder radius="md" className="panel">
      <Stack gap="xs">
        <Text fw={600}>Metrics</Text>
        <Group gap="md" wrap="wrap">
          {metrics.map((m) => (
            <Card key={m.label} withBorder radius="md" padding="sm" style={{ minWidth: 140 }}>
              <Stack gap={4}>
                <Text size="xs" c="dimmed">
                  {m.label}
                </Text>
                <Text fw={600}>{m.value}</Text>
                {m.hint && (
                  <Text size="xs" c="dimmed">
                    {m.hint}
                  </Text>
                )}
              </Stack>
            </Card>
          ))}
        </Group>
      </Stack>
    </Card>
  );
}
