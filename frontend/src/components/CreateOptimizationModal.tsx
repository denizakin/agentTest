import { Button, Group, Modal, NumberInput, Select, Stack, TextInput, Textarea } from "@mantine/core";
import { DateTimePicker } from "@mantine/dates";
import { useState } from "react";
import type { Strategy, CoinSummary, CreateOptimizationRequest, ParamRange } from "../api/types";

type Props = {
  opened: boolean;
  onClose: () => void;
  onSubmit: (params: CreateOptimizationRequest) => void;
  strategies: Strategy[];
  coins: CoinSummary[];
  isLoading?: boolean;
};

type ParamRangeInput = {
  name: string;
  start: number;
  stop: number;
  step: number;
};

export default function CreateOptimizationModal({ opened, onClose, onSubmit, strategies, coins, isLoading }: Props) {
  const barOptions = ["1m", "5m", "15m", "1h", "4h", "1d", "1w", "1mo"];

  const [instrumentId, setInstrumentId] = useState<string | null>(null);
  const [bar, setBar] = useState("1h");
  const [strategyId, setStrategyId] = useState<string | null>(null);
  const [startDt, setStartDt] = useState<Date | null>(null);
  const [endDt, setEndDt] = useState<Date | null>(null);
  const [cash, setCash] = useState<number | undefined>(10000);
  const [commission, setCommission] = useState<number | undefined>(0.001);
  const [slipPerc, setSlipPerc] = useState<number | undefined>(0);
  const [slipFixed, setSlipFixed] = useState<number | undefined>(0);
  const [slipOpen, setSlipOpen] = useState(true);
  const [maxcpus, setMaxcpus] = useState<number | undefined>(1);
  const [constraint, setConstraint] = useState("");

  // Parameter ranges - start with one empty parameter
  const [paramRanges, setParamRanges] = useState<ParamRangeInput[]>([
    { name: "", start: 1, stop: 10, step: 1 },
  ]);

  const handleSubmit = () => {
    if (!strategyId || !instrumentId || !bar || isLoading) return;

    // Filter out empty parameter names
    const validParams = paramRanges.filter((p) => p.name.trim() !== "");
    if (validParams.length === 0) {
      alert("Please add at least one parameter range");
      return;
    }

    // Build param_ranges object
    const param_ranges: Record<string, ParamRange> = {};
    for (const p of validParams) {
      param_ranges[p.name] = {
        start: p.start,
        stop: p.stop,
        step: p.step,
      };
    }

    onSubmit({
      strategy_id: Number(strategyId),
      instrument_id: instrumentId,
      bar,
      param_ranges,
      constraint: constraint.trim() || undefined,
      start_ts: startDt?.toISOString(),
      end_ts: endDt?.toISOString(),
      cash,
      commission,
      slip_perc: slipPerc,
      slip_fixed: slipFixed,
      slip_open: slipOpen,
      maxcpus,
    });
  };

  const addParamRange = () => {
    setParamRanges([...paramRanges, { name: "", start: 1, stop: 10, step: 1 }]);
  };

  const removeParamRange = (index: number) => {
    setParamRanges(paramRanges.filter((_, i) => i !== index));
  };

  const updateParamRange = (index: number, field: keyof ParamRangeInput, value: string | number) => {
    const updated = [...paramRanges];
    updated[index] = { ...updated[index], [field]: value };
    setParamRanges(updated);
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Create New Optimization" size="lg">
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
            onChange={setInstrumentId}
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
          <div style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px", color: "#495057" }}>
            Parameter Ranges (start:stop:step)
          </div>
          {paramRanges.map((param, idx) => (
            <Group key={idx} grow style={{ marginBottom: "8px" }}>
              <TextInput
                placeholder="Parameter name (e.g., fast)"
                value={param.name}
                onChange={(e) => updateParamRange(idx, "name", e.currentTarget.value)}
                style={{ flex: 2 }}
              />
              <NumberInput
                placeholder="Start"
                value={param.start}
                onChange={(v) => updateParamRange(idx, "start", v === "" ? 1 : Number(v))}
                step={1}
                style={{ flex: 1 }}
              />
              <NumberInput
                placeholder="Stop"
                value={param.stop}
                onChange={(v) => updateParamRange(idx, "stop", v === "" ? 10 : Number(v))}
                step={1}
                style={{ flex: 1 }}
              />
              <NumberInput
                placeholder="Step"
                value={param.step}
                onChange={(v) => updateParamRange(idx, "step", v === "" ? 1 : Number(v))}
                min={1}
                step={1}
                style={{ flex: 1 }}
              />
              <Button
                variant="light"
                color="red"
                size="xs"
                onClick={() => removeParamRange(idx)}
                disabled={paramRanges.length === 1}
              >
                Remove
              </Button>
            </Group>
          ))}
          <Button variant="light" size="xs" onClick={addParamRange} style={{ marginTop: "8px" }}>
            + Add Parameter
          </Button>
        </div>

        {/* Constraint */}
        <Textarea
          label="Constraint (optional)"
          placeholder="e.g., fast < slow"
          value={constraint}
          onChange={(e) => setConstraint(e.currentTarget.value)}
          minRows={2}
        />

        <Group justify="flex-end">
          <Button variant="light" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!strategyId || !instrumentId || !bar || isLoading} loading={isLoading}>
            Start Optimization
          </Button>
        </Group>
      </Stack>
    </Modal>
  );
}
