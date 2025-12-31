import { Card, Group, Progress, Stack, Text } from "@mantine/core";

type Props = {
  label: string;
  percent: number;
  status?: "queued" | "running" | "succeeded" | "failed";
};

const statusColors: Record<string, string> = {
  queued: "gray",
  running: "blue",
  succeeded: "green",
  failed: "red",
};

export default function JobProgress({ label, percent, status = "queued" }: Props) {
  return (
    <Card withBorder radius="md" className="panel">
      <Stack gap="xs">
        <Group justify="space-between">
          <Text fw={600}>{label}</Text>
          <Text size="sm" c="dimmed">
            {status.toUpperCase()}
          </Text>
        </Group>
        <Progress value={percent} color={statusColors[status]} />
      </Stack>
    </Card>
  );
}
