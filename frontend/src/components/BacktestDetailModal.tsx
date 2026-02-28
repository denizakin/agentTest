import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Modal, Text, Stack } from "@mantine/core";
import { getJson } from "../api/client";
import type { RunResultItem, ChartResponse, RunLogItem } from "../api/types";
import BacktestChart, { type BacktestChartHandle } from "./BacktestChart";
import BacktestResults from "./BacktestResults";

interface Props {
  runId: number | null;
  onClose: () => void;
}

export default function BacktestDetailModal({ runId, onClose }: Props) {
  const chartRef = useRef<BacktestChartHandle>(null);
  const [resultsMap, setResultsMap] = useState<Record<number, RunResultItem[]>>({});

  const chartQuery = useQuery({
    queryKey: ["backtest-chart", runId],
    queryFn: () => getJson<ChartResponse>(`/backtests/${runId}/chart`),
    enabled: runId !== null,
  });

  const resultsQuery = useQuery({
    queryKey: ["backtest-results", runId],
    queryFn: () => getJson<RunResultItem[]>(`/backtests/${runId}/results`),
    enabled: runId !== null,
    refetchInterval: 4000,
  });

  useEffect(() => {
    if (runId && resultsQuery.data) {
      setResultsMap((prev) => ({ ...prev, [runId]: resultsQuery.data }));
    }
  }, [resultsQuery.data, runId]);

  return (
    <Modal
      opened={runId !== null}
      onClose={onClose}
      title={`Backtest Results - Run #${runId}`}
      size="95%"
      styles={{ body: { height: "85vh", display: "flex", flexDirection: "column", gap: "20px" } }}
    >
      {chartQuery.isLoading && <Text c="dimmed">Loading chart...</Text>}
      {chartQuery.isError && <Text c="red">Failed to load chart</Text>}
      {chartQuery.data && (
        <>
          <div style={{ flex: "0 0 50%", minHeight: 0 }}>
            <BacktestChart ref={chartRef} data={chartQuery.data} />
          </div>
          <div style={{ flex: "0 0 auto", overflow: "auto" }}>
            {runId && resultsMap[runId] && (
              <BacktestResults results={resultsMap[runId]} runId={runId} chartRef={chartRef} />
            )}
          </div>
        </>
      )}
    </Modal>
  );
}
