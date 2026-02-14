-- Create optimization_results table
CREATE TABLE IF NOT EXISTS optimization_results (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES run_headers(id) ON DELETE CASCADE,
    variant_params JSONB NOT NULL,
    final_value NUMERIC(30, 8),
    sharpe NUMERIC(18, 8),
    maxdd NUMERIC(18, 8),
    winrate NUMERIC(18, 8),
    profit_factor NUMERIC(18, 8),
    sqn NUMERIC(18, 8),
    total_trades INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Index for faster queries
CREATE INDEX IF NOT EXISTS idx_optimization_results_run_id ON optimization_results(run_id);
CREATE INDEX IF NOT EXISTS idx_optimization_results_final_value ON optimization_results(run_id, final_value DESC);
