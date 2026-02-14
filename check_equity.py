import sys
sys.path.insert(0, 'src')

from db.database import Database
from db.run_results_repo import RunResultsRepo

db = Database()
repo = RunResultsRepo()

with db.session_scope() as s:
    results = repo.list_by_run(s, 78)
    for r in results:
        has_equity = "equity" in (r.metrics or {})
        equity_count = len(r.metrics.get("equity", [])) if has_equity else 0
        print(f"Run {r.run_id}, label={r.label}, has_equity={has_equity}, equity_points={equity_count}")
        if has_equity:
            print(f"  First equity point: {r.metrics['equity'][0]}")
