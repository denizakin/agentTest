import { Card, Grid, Stack, Text, Title } from "@mantine/core";
import { useQuery } from "@tanstack/react-query";
import MetricsPanel from "../components/MetricsPanel";
import { getJson } from "../api/client";
import type { CoinSummary } from "../api/types";

export default function CoinsPage() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["coins"],
    queryFn: () => getJson<CoinSummary[]>("/coins/top"),
  });

  const coins = data ?? [];

  return (
    <Stack gap="md">
      <Title order={3}>Coins</Title>
      {isError && (
        <Card withBorder radius="md" className="panel">
          <Text c="red">Failed to load coins: {(error as Error).message}</Text>
        </Card>
      )}
      <Grid>
        {isLoading && <Text c="dimmed">Loading...</Text>}
        {!isLoading &&
          coins.map((c) => (
            <Grid.Col key={c.instrument_id} span={{ base: 12, sm: 6, md: 3 }}>
              <Card withBorder radius="md" className="panel">
                <Text fw={600}>{c.instrument_id}</Text>
                <Text size="sm" c="dimmed">
                  Candles available
                </Text>
              </Card>
            </Grid.Col>
          ))}
      </Grid>
      <MetricsPanel
        metrics={[
          { label: "Tracked coins", value: coins.length },
          { label: "Last sync", value: "live" },
        ]}
      />
    </Stack>
  );
}
