export type CoinSummary = {
  instrument_id: string;
  name?: string | null;
  market_cap_usd?: number | null;
  volume_24h_usd?: number | null;
};

export type Strategy = {
  id: number;
  name: string;
  status: "draft" | "prod" | "archived";
  notes?: string | null;
  code?: string | null;
};

export type CreateStrategyRequest = {
  name: string;
  status: "draft" | "prod" | "archived";
  notes?: string;
  code?: string;
};

export type BacktestSummary = {
  run_id: number;
  job_id: string;
  strategy_id: number;
  strategy_name?: string | null;
  instrument_id: string;
  bar: string;
  status: string;
  submitted_at: string;
  progress: number;
  error?: string | null;
};

export type CreateBacktestJobRequest = {
  strategy_id: number;
  instrument_id: string;
  bar: string;
  params?: Record<string, unknown>;
  start_ts?: string;
  end_ts?: string;
};

export type RunLogItem = {
  ts: string;
  level: string;
  message: string;
};
