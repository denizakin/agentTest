import { Button, Group, Modal, NumberInput, Select, Stack, Text, Textarea, Loader } from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import type { Strategy, CoinSummary, CreateWfoRequest, ParamRange } from "../api/types";

type Props = {
  opened: boolean;
  onClose: () => void;
  onSubmit: (params: CreateWfoRequest) => void;
  strategies: Strategy[];
  coins: CoinSummary[];
  isLoading?: boolean;
};

type ParamRangeRow = {
  name: string;
  defaultValue: number;
  start: number;
  stop: number;
  step: number;
};

export default function CreateWfoModal({ opened, onClose, onSubmit, strategies, coins, isLoading }: Props) {
  const barOptions = ["1m", "5m", "15m", "1h", "4h", "1d", "1w", "1mo"];
  const objectiveOptions = [
    { value: "final", label: "Final Value" },
    { value: "sharpe", label: "Sharpe Ratio" },
    { value: "pf", label: "Profit Factor" },
  ];

  const [instrumentId, setInstrumentId] = useState<string | null>(null);
  const [bar, setBar] = useState("1h");
  const [strategyId, setStrategyId] = useState<string | null>(null);
  const [startDt, setStartDt] = useState<Date | null>(null);
  const [endDt, setEndDt] = useState<Date | null>(null);
  const [cash, setCash] = useState<number | undefined>(10000);
  const [commission, setCommission] = useState<number | undefined>(0.001);
  const [slipPerc, setSlipPerc] = useState<number | undefined>(0);
  const [slipFixed, setSlipFixed] = useState<number | undefined>(0);
  const [maxcpus, setMaxcpus] = useState<number | undefined>(1);
  const [constraint, setConstraint] = useState("");
  const [objective, setObjective] = useState("final");
  const [trainMonths, setTrainMonths] = useState<number | undefined>(12);
  const [testMonths, setTestMonths] = useState<number | undefined>(3);
  const [stepMonths, setStepMonths] = useState<number | undefined>(3);
  const [paramRanges, setParamRanges] = useState<ParamRangeRow[]>([]);

  const { data: paramsData, isLoading: paramsLoading } = useQuery({
    queryKey: ["strategy-params", strategyId],
    queryFn: async () => {
      if (!strategyId) return null;
      const res = await fetch(`/api/backtests/strategies/${strategyId}/params`);
      if (!res.ok) return null;
      return res.json();
    },
    enabled: !!strategyId,
    retry: false,
  });

  useEffect(() => {
    if (paramsData?.params) {
      const rows: ParamRangeRow[] = [];
      for (const [key, value] of Object.entries(paramsData.params)) {
        if (typeof value === "number") {
          const defaultVal = value as number;
          const isInt = Number.isInteger(defaultVal);
          const absVal = Math.abs(defaultVal) || 1;
          const start = isInt ? Math.max(1, Math.floor(defaultVal * 0.5)) : defaultVal * 0.5;
          const stop = isInt ? Math.ceil(defaultVal * 2) : defaultVal * 2;
          const step = isInt ? 1 : Math.round(absVal * 0.1 * 100) / 100;
          rows.push({
            name: key,
            defaultValue: defaultVal,
            start: isInt ? start : Math.round(start * 100) / 100,
            stop: isInt ? Math.max(stop, start + 1) : Math.round(stop * 100) / 100,
            step: Math.max(step, isInt ? 1 : 0.01),
          });
        }
      }
      setParamRanges(rows);
    } else {
      setParamRanges([]);
    }
  }, [paramsData]);

  const handleSubmit = () => {
    if (!strategyId || !instrumentId || !bar || isLoading) return;

    const param_ranges: Record<string, ParamRange> = {};
    for (const p of paramRanges) {
      if (p.step > 0 && p.stop >= p.start) {
        param_ranges[p.name] = { start: p.start, stop: p.stop, step: p.step };
      }
    }

    if (Object.keys(param_ranges).length === 0) {
      alert("Please configure at least one parameter range");
      return;
    }

    onSubmit({
      strategy_id: Number(strategyId),
      instrument_id: instrumentId,
      bar,
      param_ranges,
      constraint: constraint.trim() || undefined,
      objective,
      train_months: trainMonths,
      test_months: testMonths,
      step_months: stepMonths,
      start_ts: startDt?.toISOString(),
      end_ts: endDt?.toISOString(),
      cash,
      commission,
      slip_perc: slipPerc,
      slip_fixed: slipFixed,
      maxcpus,
    });
  };

  const updateParamRange = (index: number, field: keyof ParamRangeRow, value: number) => {
    const updated = [...paramRanges];
    updated[index] = { ...updated[index], [field]: value };
    setParamRanges(updated);
  };

  const totalVariants = paramRanges.reduce((total, p) => {
    if (p.step <= 0 || p.stop < p.start) return total;
    const count = Math.floor((p.stop - p.start) / p.step) + 1;
    return total * Math.max(1, count);
  }, 1);

  return (
    <Modal opened={opened} onClose={onClose} title="Create Walk-Forward Analysis" size="lg">
      <Stack gap="md">
        <Group grow>
          <Select
            label="Strategy"
            placeholder="Select strategy"
            data={strategies.map((s) => ({ value: String(s.id), label: `${s.name} (${s.status})` }))}
            value={strategyId}
            onChange={setStrategyId}
            searchable
            required
          />
          <Select
            label="Instrument"
            placeholder="Select instrument"
            data={coins.map((c) => ({ value: c.instrument_id, label: c.instrument_id }))}
            value={instrumentId}
            onChange={setInstrumentId}
            searchable
            required
          />
        </Group>

        <Group grow>
          <Select
            label="Bar"
            data={barOptions.map((b) => ({ value: b, label: b }))}
            value={bar}
            onChange={(v) => setBar(v || "1h")}
            required
          />
          <Select
            label="Objective"
            data={objectiveOptions}
            value={objective}
            onChange={(v) => setObjective(v || "final")}
          />
        </Group>

        {/* WFO window settings */}
        <Group grow>
          <NumberInput
            label="Train (months)"
            value={trainMonths}
            onChange={(v) => setTrainMonths(v === "" ? undefined : Number(v))}
            min={1}
            step={1}
          />
          <NumberInput
            label="Test (months)"
            value={testMonths}
            onChange={(v) => setTestMonths(v === "" ? undefined : Number(v))}
            min={1}
            step={1}
          />
          <NumberInput
            label="Step (months)"
            value={stepMonths}
            onChange={(v) => setStepMonths(v === "" ? undefined : Number(v))}
            min={1}
            step={1}
          />
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
          <NumberInput label="Cash" value={cash} onChange={(v) => setCash(v === "" ? undefined : Number(v))} min={0} step={1000} />
          <NumberInput
            label="Commission"
            value={commission}
            onChange={(v) => setCommission(v === "" ? undefined : Number(v))}
            min={0}
            step={0.0001}
            decimalScale={6}
          />
          <NumberInput
            label="Max CPUs"
            value={maxcpus}
            onChange={(v) => setMaxcpus(v === "" ? undefined : Number(v))}
            min={1}
            step={1}
          />
        </Group>

        <Group grow>
          <NumberInput
            label="Slip % (fraction)"
            value={slipPerc}
            onChange={(v) => setSlipPerc(v === "" ? undefined : Number(v))}
            min={0}
            step={0.0001}
            decimalScale={6}
          />
          <NumberInput
            label="Slip fixed"
            value={slipFixed}
            onChange={(v) => setSlipFixed(v === "" ? undefined : Number(v))}
            min={0}
            step={0.01}
          />
        </Group>

        {/* Parameter Ranges */}
        <div style={{ borderTop: "1px solid #dee2e6", paddingTop: "12px", marginTop: "8px" }}>
          <Group justify="space-between" mb="sm">
            <Text size="sm" fw={600} c="dimmed">Parameter Ranges (Start / Stop / Step)</Text>
            {paramRanges.length > 0 && (
              <Text size="xs" c="blue">Variants per fold: {totalVariants.toLocaleString()}</Text>
            )}
          </Group>

          {!strategyId && (
            <Text size="sm" c="dimmed" ta="center" py="md">Select a strategy to see its parameters</Text>
          )}
          {strategyId && paramsLoading && (
            <div style={{ display: "flex", justifyContent: "center", padding: "16px" }}><Loader size="sm" /></div>
          )}
          {strategyId && !paramsLoading && paramRanges.length === 0 && (
            <Text size="sm" c="dimmed" ta="center" py="md">No configurable parameters found</Text>
          )}

          {paramRanges.map((param, idx) => (
            <div key={param.name} style={{ marginBottom: "8px" }}>
              <Text size="xs" fw={600} mb={4}>
                {param.name} <Text span size="xs" c="dimmed">(default: {param.defaultValue})</Text>
              </Text>
              <Group grow>
                <NumberInput label="Start" size="xs" value={param.start}
                  onChange={(v) => updateParamRange(idx, "start", v === "" ? 1 : Number(v))}
                  step={Number.isInteger(param.defaultValue) ? 1 : 0.01}
                  decimalScale={Number.isInteger(param.defaultValue) ? 0 : 2}
                />
                <NumberInput label="Stop" size="xs" value={param.stop}
                  onChange={(v) => updateParamRange(idx, "stop", v === "" ? 10 : Number(v))}
                  step={Number.isInteger(param.defaultValue) ? 1 : 0.01}
                  decimalScale={Number.isInteger(param.defaultValue) ? 0 : 2}
                />
                <NumberInput label="Step" size="xs" value={param.step}
                  onChange={(v) => updateParamRange(idx, "step", v === "" ? 1 : Number(v))}
                  min={Number.isInteger(param.defaultValue) ? 1 : 0.01}
                  step={Number.isInteger(param.defaultValue) ? 1 : 0.01}
                  decimalScale={Number.isInteger(param.defaultValue) ? 0 : 2}
                />
              </Group>
            </div>
          ))}
        </div>

        <Textarea
          label="Constraint (optional)"
          placeholder="e.g., fast < slow"
          value={constraint}
          onChange={(e) => setConstraint(e.currentTarget.value)}
          minRows={2}
        />

        <Group justify="flex-end">
          <Button variant="light" onClick={onClose}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            disabled={!strategyId || !instrumentId || !bar || paramRanges.length === 0 || isLoading}
            loading={isLoading}
          >
            Start WFO ({totalVariants.toLocaleString()} variants/fold)
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
