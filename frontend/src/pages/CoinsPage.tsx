import { Card, Grid, Stack, Text, Title } from "@mantine/core";
import MetricsPanel from "../components/MetricsPanel";

const mockCoins = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "XRP-USDT"];

export default function CoinsPage() {
  return (
    <Stack gap="md">
      <Title order={3}>Coins</Title>
      <Grid>
        {mockCoins.map((c) => (
          <Grid.Col key={c} span={{ base: 12, sm: 6, md: 3 }}>
            <Card withBorder radius="md" className="panel">
              <Text fw={600}>{c}</Text>
              <Text size="sm" c="dimmed">
                Candles available
              </Text>
            </Card>
          </Grid.Col>
        ))}
      </Grid>
      <MetricsPanel
        metrics={[
          { label: "Tracked coins", value: mockCoins.length },
          { label: "Last sync", value: "just now" },
        ]}
      />
    </Stack>
  );
}
