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
  tag?: string | null;
  notes?: string | null;
  code?: string | null;
};

export type CreateStrategyRequest = {
  name: string;
  status: "draft" | "prod" | "archived";
  tag?: string;
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
  start_ts?: string | null;
  end_ts?: string | null;
  strategy_params?: Record<string, unknown> | null;
};

export type CreateBacktestJobRequest = {
  strategy_id: number;
  instrument_id: string;
  bar: string;
  params?: Record<string, unknown>;
  start_ts?: string;
  end_ts?: string;
  cash?: number;
  commission?: number;
  stake?: number;
  use_sizer?: boolean;
  coc?: boolean;
  baseline?: boolean;
  parallel_baseline?: boolean;
  slip_perc?: number;
  slip_fixed?: number;
  slip_open?: boolean;
  refresh?: boolean;
  plot?: boolean;
};

export type RunLogItem = {
  ts: string;
  level: string;
  message: string;
};

export type RunResultItem = {
  label: string;
  params?: Record<string, unknown> | null;
  metrics?: Record<string, unknown> | null;
  plot_path?: string | null;
};

export type ChartCandle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type ChartSignal = {
  time: string;
  side: string;
  price?: number | null;
  message?: string | null;
};

export type ChartResponse = {
  candles: ChartCandle[];
  signals: ChartSignal[];
};

export type TradeItem = {
  entry_ts: string;
  exit_ts: string;
  side: string;
  entry_price: number;
  exit_price: number;
  size: number;
  pnl: number;
  pnl_pct?: number | null;
  mae?: number | null;
  mfe?: number | null;
  commission?: number | null;
};

export type ParamRange = {
  start: number;
  stop: number;
  step: number;
};

export type OptimizationSummary = {
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
  total_variants?: number | null;
  best_final_value?: number | null;
  best_params?: Record<string, unknown> | null;
};

export type OptimizationVariant = {
  id: number;
  variant_params: Record<string, unknown>;
  final_value?: number | null;
  sharpe?: number | null;
  maxdd?: number | null;
  winrate?: number | null;
  profit_factor?: number | null;
  sqn?: number | null;
  total_trades?: number | null;
  long_count?: number | null;
  short_count?: number | null;
  won_count?: number | null;
  lost_count?: number | null;
  best_pnl?: number | null;
  worst_pnl?: number | null;
  avg_pnl?: number | null;
};

export type OptimizationDetail = {
  run_id: number;
  strategy_id: number;
  strategy_name: string;
  instrument_id: string;
  bar: string;
  status: string;
  submitted_at: string;
  ended_at?: string | null;
  progress: number;
  error?: string | null;
  param_ranges: Record<string, ParamRange>;
  constraint?: string | null;
  total_variants: number;
  variants: OptimizationVariant[];
  cash?: number | null;
  commission?: number | null;
  slip_perc?: number | null;
  slip_fixed?: number | null;
  start_ts?: string | null;
  end_ts?: string | null;
  maxcpus?: number | null;
};

export type CreateOptimizationRequest = {
  strategy_id: number;
  instrument_id: string;
  bar: string;
  param_ranges: Record<string, ParamRange>;
  constraint?: string;
  start_ts?: string;
  end_ts?: string;
  cash?: number;
  commission?: number;
  slip_perc?: number;
  slip_fixed?: number;
  slip_open?: boolean;
  maxcpus?: number;
};

// ── Walk-Forward Analysis ──────────────────────────────────────────────

export type WfoSummary = {
  run_id: number;
  strategy_id: number;
  strategy_name?: string | null;
  instrument_id: string;
  bar: string;
  status: string;
  submitted_at: string;
  progress: number;
  error?: string | null;
  total_folds: number;
  objective?: string | null;
  train_months?: number | null;
  test_months?: number | null;
  step_months?: number | null;
};

export type WfoFoldItem = {
  id: number;
  fold_index: number;
  train_start: string;
  train_end: string;
  test_start: string;
  test_end: string;
  params?: Record<string, unknown> | null;
  train_objective?: number | null;
  metrics?: Record<string, unknown> | null;
};

export type WfoDetail = {
  run_id: number;
  strategy_id: number;
  strategy_name: string;
  instrument_id: string;
  bar: string;
  status: string;
  submitted_at: string;
  ended_at?: string | null;
  progress: number;
  error?: string | null;
  param_ranges: Record<string, ParamRange>;
  constraint?: string | null;
  objective?: string | null;
  train_months?: number | null;
  test_months?: number | null;
  step_months?: number | null;
  total_folds: number;
  folds: WfoFoldItem[];
  cash?: number | null;
  commission?: number | null;
  slip_perc?: number | null;
  slip_fixed?: number | null;
  start_ts?: string | null;
  end_ts?: string | null;
  maxcpus?: number | null;
};

export type CreateWfoRequest = {
  strategy_id: number;
  instrument_id: string;
  bar: string;
  param_ranges: Record<string, ParamRange>;
  constraint?: string;
  objective?: string;
  train_months?: number;
  test_months?: number;
  step_months?: number;
  start_ts?: string;
  end_ts?: string;
  cash?: number;
  commission?: number;
  slip_perc?: number;
  slip_fixed?: number;
  slip_open?: boolean;
  maxcpus?: number;
};
