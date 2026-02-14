import sys
sys.path.insert(0, 'src')

from config import load_env_file
from db.db_conn import DbConn
from db.run_trades_repo import RunTradesRepo
from db.backtests_repo import BacktestsRepo

load_env_file()
db = DbConn()
backtests_repo = BacktestsRepo()
trades_repo = RunTradesRepo()

with db.session_scope() as s:
    # Get most recent backtests
    recent = backtests_repo.list_recent(s, limit=5)
    for run in recent:
        print(f'Run {run.id}: {run.strategy} on {run.instrument_id} - Status: {run.status}')
        trades = trades_repo.list_trades(s, run.id)
        print(f'  Trades count: {len(trades)}')
        if trades:
            print(f'  First trade: {trades[0].side} entry={trades[0].entry_ts} pnl={trades[0].pnl}')
        print()
