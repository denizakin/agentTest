import { Stack, Text, Title } from "@mantine/core";

const items = [
  "Backtest BTC 1h submitted",
  "Strategy SMA Crossover saved",
  "Optimization job queued",
];

export default function ActivityPage() {
  return (
    <Stack gap="md">
      <Title order={3}>Activity</Title>
      <Stack gap="xs">
        {items.map((msg, idx) => (
          <Text key={idx}>• {msg}</Text>
        ))}
      </Stack>
    </Stack>
  );
}
