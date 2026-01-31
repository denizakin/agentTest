import { Button, Checkbox, Group, Modal, NumberInput, Select, Stack } from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { useState } from "react";
import type { Strategy, CoinSummary } from "../api/types";

type Props = {
  opened: boolean;
  onClose: () => void;
  onSubmit: (params: BacktestParams) => void;
  strategies: Strategy[];
  coins: CoinSummary[];
  isLoading?: boolean;
};

export type BacktestParams = {
  strategy_id: number;
  instrument_id: string;
  bar: string;
  start_ts?: string;
  end_ts?: string;
  cash?: number;
  commission?: number;
  stake?: number;
  use_sizer: boolean;
  coc: boolean;
  baseline: boolean;
  parallel_baseline: boolean;
  slip_perc: number;
  slip_fixed: number;
  slip_open: boolean;
  refresh: boolean;
  plot: boolean;
};

export default function CreateBacktestModal({ opened, onClose, onSubmit, strategies, coins, isLoading }: Props) {
  const barOptions = ["1m", "5m", "15m", "1h", "4h", "1d", "1w", "1mo"];

  const [instrumentId, setInstrumentId] = useState("");
  const [bar, setBar] = useState("1h");
  const [strategyId, setStrategyId] = useState<string | null>(null);
  const [startDt, setStartDt] = useState<Date | null>(null);
  const [endDt, setEndDt] = useState<Date | null>(null);
  const [cash, setCash] = useState<number | undefined>(10000);
  const [commission, setCommission] = useState<number | undefined>(0.001);
  const [stake, setStake] = useState<number | undefined>(1);
  const [useSizer, setUseSizer] = useState(false);
  const [coc, setCoc] = useState(false);
  const [baseline, setBaseline] = useState(true);
  const [parallelBaseline, setParallelBaseline] = useState(false);
  const [slipPerc, setSlipPerc] = useState<number | undefined>(0);
  const [slipFixed, setSlipFixed] = useState<number | undefined>(0);
  const [slipOpen, setSlipOpen] = useState(true);
  const [refresh, setRefresh] = useState(false);
  const [plot, setPlot] = useState(true);

  const handleSubmit = () => {
    if (!strategyId || !instrumentId || !bar) return;

    onSubmit({
      strategy_id: Number(strategyId),
      instrument_id: instrumentId,
      bar,
      start_ts: startDt?.toISOString(),
      end_ts: endDt?.toISOString(),
      cash,
      commission,
      stake,
      use_sizer: useSizer,
      coc,
      baseline,
      parallel_baseline: parallelBaseline,
      slip_perc: slipPerc ?? 0,
      slip_fixed: slipFixed ?? 0,
      slip_open: slipOpen,
      refresh,
      plot,
    });
    onClose();
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Create New Backtest" size="lg">
      <Stack gap="md">
        <Group grow>
          <Select
            label="Strategy"
            placeholder="Select strategy"
            data={strategies.map((s) => ({ value: String(s.id), label: `${s.name} (${s.status})` }))}
            value={strategyId}
            onChange={setStrategyId}
            searchable
            nothingFoundMessage="No strategies"
            required
          />
          <Select
            label="Instrument"
            placeholder="Select instrument"
            data={coins.map((c) => ({ value: c.instrument_id, label: c.instrument_id }))}
            value={instrumentId}
            onChange={(v) => setInstrumentId(v || "")}
            searchable
            nothingFoundMessage="No instruments"
            required
          />
        </Group>
        <Group grow>
          <Select
            label="Bar"
            placeholder="Select bar"
            data={barOptions.map((b) => ({ value: b, label: b }))}
            value={bar}
            onChange={(v) => setBar(v || "1h")}
            required
          />
          <NumberInput label="Cash" value={cash} onChange={(v) => setCash(v === "" ? undefined : Number(v))} min={0} step={1000} />
        </Group>
        <Group grow>
          <DateTimePicker
            label="Start"
            placeholder="Pick start"
            value={startDt}
            onChange={setStartDt}
            valueFormat="YYYY-MM-DD HH:mm"
          />
          <DateTimePicker
            label="End"
            placeholder="Pick end"
            value={endDt}
            onChange={setEndDt}
            valueFormat="YYYY-MM-DD HH:mm"
          />
        </Group>
        <Group grow>
          <NumberInput label="Commission" value={commission} onChange={(v) => setCommission(v === "" ? undefined : Number(v))} min={0} step={0.0001} decimalScale={6} />
          <NumberInput label="Stake" value={stake} onChange={(v) => setStake(v === "" ? undefined : Number(v))} min={0} step={1} />
        </Group>
        <Group grow>
          <NumberInput label="Slip % (fraction)" value={slipPerc} onChange={(v) => setSlipPerc(v === "" ? undefined : Number(v))} min={0} step={0.0001} decimalScale={6} />
          <NumberInput label="Slip fixed" value={slipFixed} onChange={(v) => setSlipFixed(v === "" ? undefined : Number(v))} min={0} step={0.01} />
        </Group>
        <Group>
          <Checkbox label="Use sizer" checked={useSizer} onChange={(e) => setUseSizer(e.currentTarget.checked)} />
          <Checkbox label="COC" checked={coc} onChange={(e) => setCoc(e.currentTarget.checked)} />
          <Checkbox label="Baseline" checked={baseline} onChange={(e) => setBaseline(e.currentTarget.checked)} />
          <Checkbox label="Parallel baseline" checked={parallelBaseline} onChange={(e) => setParallelBaseline(e.currentTarget.checked)} />
          <Checkbox label="Slip on open" checked={slipOpen} onChange={(e) => setSlipOpen(e.currentTarget.checked)} />
          <Checkbox label="Refresh MV" checked={refresh} onChange={(e) => setRefresh(e.currentTarget.checked)} />
          <Checkbox label="Plot" checked={plot} onChange={(e) => setPlot(e.currentTarget.checked)} />
        </Group>
        <Group justify="flex-end">
          <Button variant="light" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!strategyId || !instrumentId || !bar} loading={isLoading}>
            Start Backtest
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
