# Weaver Production Test Plan

> **Goal**: End-to-end validation of the entire system in paper trading before going live.
>
> **Prerequisites**: Alpaca Paper credentials configured in `docker/.env`, all three containers running.

---

## Phase 0: Environment Verification

Confirm all infrastructure is reachable.

### 0.1 Container Status

```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep docker-
```

Expect: `backend_dev`, `frontend_dev`, `db_dev` all **Up**.

### 0.2 Database Connection

```bash
python -c "
import asyncio
from src.walle.database import Database
from src.config import get_config

async def check():
    config = get_config()
    db = Database(config.database.url)
    await db.connect()
    print('DB connected OK')
    await db.disconnect()

asyncio.run(check())
"
```

### 0.3 Alpaca Paper Credentials

```bash
# Load credentials (if container was created before .env was populated)
export $(grep -E '^ALPACA_' docker/.env | xargs)

python -c "
from alpaca.trading.client import TradingClient
from src.config import AlpacaConfig

config = AlpacaConfig()
creds = config.get_credentials('paper')
client = TradingClient(creds.api_key, creds.api_secret, paper=True)
account = client.get_account()
print(f'Account: {account.status}')
print(f'Cash: \${float(account.cash):,.2f}')
print(f'Buying Power: \${float(account.buying_power):,.2f}')
"
```

Expect: Account **ACTIVE** with available funds.

### 0.4 API Health Check

```bash
curl -s http://localhost:8000/healthz | python -m json.tool
```

If 404, try:
```bash
curl -s http://localhost:8000/api/v1/healthz
```

---

## Phase 1: Backtest Smoke Test

> **Purpose**: Validate the internal event chain without touching any external API.

### 1.1 Create a Backtest Run

```bash
curl -s -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "sma-crossover",
    "mode": "backtest",
    "symbols": ["AAPL"],
    "timeframe": "1d",
    "start_time": "2025-01-02T00:00:00Z",
    "end_time": "2025-03-01T00:00:00Z",
    "config": {
      "fast_period": 5,
      "slow_period": 20,
      "qty": "1.0"
    }
  }' | python -m json.tool
```

Note the returned `id` (referred to as `$RUN_ID` below).

**Checkpoints:**
- [ ] HTTP 201, status = `pending`
- [ ] Valid UUID id

### 1.2 Start the Backtest

```bash
curl -s -X POST http://localhost:8000/api/v1/runs/$RUN_ID/start | python -m json.tool
```

**Checkpoints:**
- [ ] HTTP 200, status = `completed` (backtests run synchronously)
- [ ] Both `started_at` and `stopped_at` are populated
- [ ] If status = `error`, inspect logs: `docker logs docker-backend_dev-1 --tail 50`

### 1.3 Verify the Event Chain

```bash
# Run details
curl -s http://localhost:8000/api/v1/runs/$RUN_ID | python -m json.tool

# Check for generated orders
curl -s "http://localhost:8000/api/v1/orders?run_id=$RUN_ID" | python -m json.tool
```

**Checkpoints:**
- [ ] Run status is `completed`
- [ ] Orders exist (SMA should trigger crossovers over 2 months of daily data)
- [ ] Zero orders is not necessarily a bug — depends on whether AAPL had SMA crossovers in that range

### 1.4 Troubleshooting

If backtest fails:

```bash
# Full backend logs
docker logs docker-backend_dev-1 2>&1 | tail -100

# Common issues:
# 1. BarRepository has no data → bars need to be preloaded
# 2. Strategy load failure → wrong strategy_id
# 3. DB not migrated → check alembic migrations
```

---

## Phase 2: Paper Trading — Single Order

> **Purpose**: Verify actual Alpaca Paper API communication.
>
> ⚠️ US market hours: 9:30–16:00 ET (21:30–04:00 / 22:30–05:00 Beijing Time).
> Market orders placed outside hours queue until next market open.

### 2.1 Create a Paper Run

```bash
curl -s -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "sma-crossover",
    "mode": "paper",
    "symbols": ["AAPL"],
    "timeframe": "1m"
  }' | python -m json.tool
```

Note `$RUN_ID`.

**Checkpoint:**
- [ ] HTTP 201, status = `pending`

### 2.2 Start the Paper Run

```bash
curl -s -X POST http://localhost:8000/api/v1/runs/$RUN_ID/start | python -m json.tool
```

**Checkpoints:**
- [ ] HTTP 200, status = `running` (async, non-blocking)
- [ ] Backend logs show RealtimeClock ticking

### 2.3 Manual Order Test

Submit a manual order to verify the order pipeline before waiting for strategy signals:

```bash
curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "'$RUN_ID'",
    "symbol": "AAPL",
    "side": "buy",
    "qty": "1",
    "order_type": "market",
    "time_in_force": "day"
  }' | python -m json.tool
```

**Checkpoints:**
- [ ] Response has `exchange_order_id` (Alpaca received the order)
- [ ] Status is `accepted` / `new` (market hours) or `pending_new` (after hours)
- [ ] 503 → VedaService not initialized (credential issue)
- [ ] `rejected` → Check `error_message` (insufficient funds, bad symbol, etc.)

### 2.4 Verify Order Status

```bash
# Via our API
curl -s "http://localhost:8000/api/v1/orders?run_id=$RUN_ID" | python -m json.tool

# Direct Alpaca confirmation
python -c "
from alpaca.trading.client import TradingClient
from src.config import AlpacaConfig
config = AlpacaConfig()
creds = config.get_credentials('paper')
client = TradingClient(creds.api_key, creds.api_secret, paper=True)
orders = client.get_orders()
for o in orders[:5]:
    print(f'{o.symbol} {o.side} {o.qty} @ {o.filled_avg_price} status={o.status}')
"
```

**Checkpoints:**
- [ ] Our API orders match Alpaca orders
- [ ] During market hours: order should quickly become `filled`
- [ ] After hours: status should be `accepted`, waiting for open

### 2.5 Sell to Close

```bash
curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "'$RUN_ID'",
    "symbol": "AAPL",
    "side": "sell",
    "qty": "1",
    "order_type": "market",
    "time_in_force": "day"
  }' | python -m json.tool
```

### 2.6 SSE Real-Time Push Verification

Open the SSE stream in a separate terminal:

```bash
curl -N "http://localhost:8000/api/v1/events/stream?run_id=$RUN_ID"
```

Then place another order from the first terminal. Watch for events on the SSE stream.

**Checkpoints:**
- [ ] SSE connection stays open
- [ ] Event received within seconds of order placement
- [ ] Event format: `event: orders.Created\ndata: {...}\n\n`

### 2.7 Stop the Run

```bash
curl -s -X POST http://localhost:8000/api/v1/runs/$RUN_ID/stop | python -m json.tool
```

**Checkpoints:**
- [ ] Status becomes `stopped`
- [ ] RealtimeClock stops ticking (no new ticks in logs)
- [ ] SSE receives `run.Stopped` event

---

## Phase 3: Strategy Auto-Trading Observation

> **Purpose**: Let the SMA strategy run autonomously and observe the full automated trading loop.
>
> ⚠️ Only meaningful during US market hours (no real-time quotes after hours).

### 3.1 Create and Start a Paper Run (5-min bars)

```bash
# Create
RUN_ID=$(curl -s -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "sma-crossover",
    "mode": "paper",
    "symbols": ["AAPL"],
    "timeframe": "5m",
    "config": {
      "fast_period": 3,
      "slow_period": 8,
      "qty": "1.0"
    }
  }' | python -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Run ID: $RUN_ID"

# Start
curl -s -X POST http://localhost:8000/api/v1/runs/$RUN_ID/start | python -m json.tool
```

> Shorter SMA periods (3/8) increase crossover frequency for easier observation.

### 3.2 Open Monitoring

```bash
# Terminal 1: SSE event stream
curl -N "http://localhost:8000/api/v1/events/stream?run_id=$RUN_ID"

# Terminal 2: Backend logs
docker logs -f docker-backend_dev-1 2>&1 | grep -E "tick|order|strategy|error" --color

# Terminal 3: Frontend UI
# Open http://localhost:13579 in browser
```

### 3.3 What to Watch For

| Timing | Expected Behavior |
|--------|-------------------|
| Every 5 min | RealtimeClock emits `clock.Tick` |
| After tick | Strategy emits `strategy.FetchWindow` |
| Data returned | `data.WindowReady` event with bar data |
| SMA crossover | `strategy.PlaceRequest` → `live.PlaceOrder` → Alpaca order |
| Order execution | `orders.Created` → `orders.Filled` (seconds during market hours) |
| SSE push | Frontend displays order status in real-time |

### 3.4 Check After 30 Minutes

```bash
# List all orders
curl -s "http://localhost:8000/api/v1/orders?run_id=$RUN_ID" | python -m json.tool

# Run status
curl -s "http://localhost:8000/api/v1/runs/$RUN_ID" | python -m json.tool

# Alpaca account balance
python -c "
from alpaca.trading.client import TradingClient
from src.config import AlpacaConfig
config = AlpacaConfig()
creds = config.get_credentials('paper')
client = TradingClient(creds.api_key, creds.api_secret, paper=True)
account = client.get_account()
print(f'Cash: \${float(account.cash):,.2f}')
print(f'Portfolio: \${float(account.portfolio_value):,.2f}')
positions = client.get_all_positions()
for p in positions:
    print(f'  {p.symbol}: {p.qty} shares @ \${float(p.avg_entry_price):,.2f}')
"
```

### 3.5 Stop and Record

```bash
curl -s -X POST http://localhost:8000/api/v1/runs/$RUN_ID/stop | python -m json.tool
```

---

## Phase 4: Frontend UI Verification

> **Purpose**: Confirm that Haro correctly displays all trading data.

### 4.1 Access

Open `http://localhost:13579` in the browser.

### 4.2 Dashboard

- [ ] Page loads without blank screen
- [ ] Previously created runs are listed

### 4.3 Create a Run (via UI)

- [ ] Create a new paper run through the UI
- [ ] Click Start — status changes to Running
- [ ] Orders list loads properly

### 4.4 SSE Real-Time Updates

- [ ] Page auto-refreshes after run creation
- [ ] Orders page shows new orders in real-time after placement
- [ ] Stopping a run updates the status immediately

### 4.5 Stop a Run (via UI)

- [ ] Click Stop button
- [ ] Status changes to Stopped
- [ ] No error popups

---

## Phase 5: Edge Cases

> **Purpose**: Verify system behavior under abnormal conditions.

### 5.1 Invalid Symbol

```bash
curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "'$RUN_ID'",
    "symbol": "FAKESYMBOL",
    "side": "buy",
    "qty": "1",
    "order_type": "market",
    "time_in_force": "day"
  }' | python -m json.tool
```

- [ ] Returns `rejected` or error, **not** 500

### 5.2 Insufficient Funds

```bash
curl -s -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "'$RUN_ID'",
    "symbol": "BRK.A",
    "side": "buy",
    "qty": "100",
    "order_type": "market",
    "time_in_force": "day"
  }' | python -m json.tool
```

- [ ] Alpaca rejects (BRK.A ~$700k/share × 100 >> account balance)
- [ ] System returns `rejected`, does not crash

### 5.3 Duplicate Start

```bash
# Attempt to start an already running run
curl -s -X POST http://localhost:8000/api/v1/runs/$RUN_ID/start
```

- [ ] Returns 409 or error message, does not start a second instance

### 5.4 Restart After Stop

```bash
curl -s -X POST http://localhost:8000/api/v1/runs/$RUN_ID/stop
curl -s -X POST http://localhost:8000/api/v1/runs/$RUN_ID/start
```

- [ ] Should be rejected (stopped runs cannot be restarted; create a new run)

### 5.5 Backend Restart Recovery

```bash
# Restart the backend container
docker restart docker-backend_dev-1

# Wait, then check
sleep 30
curl -s http://localhost:8000/api/v1/runs | python -m json.tool
```

- [ ] Previously persisted runs are recovered and listed
- [ ] Runs that were `running` before restart are now marked `error` (unclean shutdown)

---

## Quick Reference: Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 503 Service Unavailable | VedaService not initialized | Check Alpaca credentials are loaded |
| Orders stuck in pending | Outside market hours | Wait for market open, or use crypto (24/7) |
| Backtest produces no orders | No SMA crossover in that range | Use a longer date range or shorter SMA periods |
| SSE disconnects | Timeout / network issue | Refresh page (Haro has auto-reconnect) |
| `strategy not found` | Wrong strategy_id | Use `sma-crossover` |
| DB connection failed | db_dev not running | `docker start docker-db_dev-1` |
| Credentials empty | Container created before .env was populated | `export $(grep -E '^ALPACA_' docker/.env \| xargs)` or rebuild container |

---

## Crypto Alternative (24/7 Testable)

If you don't want to wait for US market open, use crypto for paper trading (Alpaca supports it):

```bash
curl -s -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "sma-crossover",
    "mode": "paper",
    "symbols": ["BTC/USD"],
    "timeframe": "1m",
    "config": {
      "fast_period": 3,
      "slow_period": 8,
      "qty": "0.001"
    }
  }' | python -m json.tool
```

> ⚠️ Verify that your Alpaca paper account has crypto enabled.
> Also confirm the symbol format matches what Alpaca expects (`BTC/USD` vs `BTCUSD`).

---

## Execution Order Summary

```
Phase 0: Environment check     ← Confirm everything connects
  ↓
Phase 1: Backtest smoke test   ← Internal only, no external API
  ↓
Phase 2: Paper single order    ← Verify Alpaca communication
  ↓
Phase 3: Strategy auto-run     ← Full automated loop
  ↓
Phase 4: Frontend UI           ← Manual UI verification
  ↓
Phase 5: Edge cases            ← Boundary testing
```

Pass each phase before moving to the next. When in doubt, check backend logs: `docker logs -f docker-backend_dev-1`.
