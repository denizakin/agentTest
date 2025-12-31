from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])


@router.get("/", response_class=HTMLResponse)
def ui_root() -> str:
    """
    Minimal HTML page to view stub responses without Swagger.
    """
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Stub Viewer</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background: #0b1220; color: #e7ecf5; }
    h1 { margin-bottom: 8px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; }
    .card { background: #111a2c; border: 1px solid #1f2c45; border-radius: 10px; padding: 16px; box-shadow: 0 8px 24px rgba(0,0,0,0.2); }
    button { background: #2c7be5; border: none; color: #fff; padding: 8px 12px; border-radius: 6px; cursor: pointer; }
    button:hover { background: #2567c1; }
    pre { background: #0e1627; padding: 12px; border-radius: 8px; max-height: 260px; overflow: auto; }
    .row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  </style>
</head>
<body>
  <h1>Stub API Viewer</h1>
  <p>Use the buttons to fetch current stub responses.</p>
  <div class="grid">
    <div class="card">
      <div class="row">
        <h3>Coins</h3>
        <button onclick="loadCoins()">Reload</button>
      </div>
      <pre id="coins">pending...</pre>
    </div>
    <div class="card">
      <div class="row">
        <h3>Strategies</h3>
        <button onclick="loadStrategies()">Reload</button>
      </div>
      <pre id="strategies">pending...</pre>
    </div>
    <div class="card">
      <div class="row">
        <h3>Backtests</h3>
        <button onclick="loadBacktests()">Reload</button>
      </div>
      <pre id="backtests">pending...</pre>
    </div>
  </div>

  <script>
    async function fetchJson(url) {
      const res = await fetch(url);
      if (!res.ok) throw new Error(res.status + " " + res.statusText);
      return res.json();
    }

    async function loadCoins() {
      const el = document.getElementById("coins");
      el.textContent = "loading...";
      try {
        const data = await fetchJson("/coins/top");
        el.textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        el.textContent = "Error: " + err;
      }
    }

    async function loadStrategies() {
      const el = document.getElementById("strategies");
      el.textContent = "loading...";
      try {
        const data = await fetchJson("/strategies");
        el.textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        el.textContent = "Error: " + err;
      }
    }

    async function loadBacktests() {
      const el = document.getElementById("backtests");
      el.textContent = "loading...";
      try {
        const data = await fetchJson("/backtests");
        el.textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        el.textContent = "Error: " + err;
      }
    }

    // initial load
    loadCoins();
    loadStrategies();
    loadBacktests();
  </script>
</body>
</html>
"""

