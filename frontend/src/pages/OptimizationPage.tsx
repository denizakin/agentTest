import { Stack, Text, Title } from "@mantine/core";
import MetricsPanel from "../components/MetricsPanel";

export default function OptimizationPage() {
  return (
    <Stack gap="md">
      <Title order={3}>Optimization</Title>
      <MetricsPanel
        metrics={[
          { label: "Jobs", value: 0 },
          { label: "Pending", value: 0 },
          { label: "Completed", value: 0 },
        ]}
      />
      <Text c="dimmed">Optimization jobs will appear here (mocked for now).</Text>
    </Stack>
  );
}
