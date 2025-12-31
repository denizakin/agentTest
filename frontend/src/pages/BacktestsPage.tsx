import { Grid, Stack, Title } from "@mantine/core";
import JobProgress from "../components/JobProgress";
import TradesTable from "../components/TradesTable";

const mockBacktests = [
  { label: "BTC 1h SMA", percent: 70, status: "running" as const },
  { label: "ETH 4h Breakout", percent: 100, status: "succeeded" as const },
];

const mockTrades = [
  { id: "1", side: "buy" as const, price: 42000, qty: 0.1, ts: "2025-12-29T10:00Z" },
  { id: "2", side: "sell" as const, price: 42500, qty: 0.1, ts: "2025-12-29T12:00Z" },
];

export default function BacktestsPage() {
  return (
    <Stack gap="md">
      <Title order={3}>Backtests</Title>
      <Grid>
        {mockBacktests.map((bt) => (
          <Grid.Col key={bt.label} span={{ base: 12, md: 6 }}>
            <JobProgress label={bt.label} percent={bt.percent} status={bt.status} />
          </Grid.Col>
        ))}
      </Grid>
      <TradesTable trades={mockTrades} />
    </Stack>
  );
}
