# Configuration System

> Part of [Architecture Documentation](../ARCHITECTURE.md)

**Implementation**: `src/config.py` using `pydantic-settings`

## 1. Design Principles

* **Dual Credentials**: Support running Live and Paper trading in parallel (not time-based switching).
* **Environment Isolation**: Each config class reads from specific env var prefixes.
* **Type Safety**: All settings are validated via Pydantic.
* **Test Isolation**: `get_test_config()` provides safe defaults for testing.

## 2. Alpaca Credentials

The system supports **simultaneous Live and Paper API access**:

```
┌─────────────────────────────────────────────────────────────────────┐
│  Environment Variables                                              │
│  ├── ALPACA_LIVE_API_KEY / ALPACA_LIVE_API_SECRET                  │
│  ├── ALPACA_LIVE_BASE_URL (default: https://api.alpaca.markets)    │
│  ├── ALPACA_PAPER_API_KEY / ALPACA_PAPER_API_SECRET                │
│  └── ALPACA_PAPER_BASE_URL (default: https://paper-api.alpaca.markets)
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  AlpacaConfig.get_credentials(mode: "live" | "paper")              │
│  → Returns AlpacaCredentials(api_key, api_secret, base_url, is_paper)
└─────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│  Live Run (run_id: A)    │    │  Paper Run (run_id: B)   │
│  Uses Live credentials   │    │  Uses Paper credentials  │
│  Real money, real fills  │    │  Simulated trading       │
└──────────────────────────┘    └──────────────────────────┘
```

### Why Dual Credentials (Not Time-Based Switching)?

**Original consideration**: Switch between Paper (during market hours) and Live (off-hours testing).

**Actual need**: Run Live and Paper **simultaneously** as separate trading runs:
- Run A: Live trading with strategy X
- Run B: Paper testing with experimental strategy Y
- Both active at the same time, isolated by `run_id`

This design also supports:
- A/B testing strategies (Live vs Paper with same parameters)
- Validating Paper results before promoting to Live
- Running backtests while Live trading continues

## 3. Configuration Classes

```python
@dataclass(frozen=True)
class AlpacaCredentials:
    """Immutable credentials for a single Alpaca environment."""
    api_key: str
    api_secret: str
    base_url: str
    is_paper: bool

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret)


class AlpacaConfig(BaseSettings):
    """Alpaca API configuration with dual credential support."""
    live_api_key: str = ""
    live_api_secret: str = ""
    live_base_url: str = "https://api.alpaca.markets"
    paper_api_key: str = ""
    paper_api_secret: str = ""
    paper_base_url: str = "https://paper-api.alpaca.markets"

    def get_credentials(self, mode: Literal["live", "paper"]) -> AlpacaCredentials:
        """Get credentials for the specified trading mode."""
        ...

    @property
    def has_live_credentials(self) -> bool: ...
    @property
    def has_paper_credentials(self) -> bool: ...
```

## 4. Security Best Practices

| Practice | Implementation |
|----------|----------------|
| Never commit secrets | `.gitignore` excludes `.env*` files |
| Template files only | `docker/example.env` contains placeholders only |
| Test isolation | Tests use `monkeypatch` to prevent real credential leakage |
| CI/CD secrets | Use GitHub Secrets (`${{ secrets.XXX }}`) in workflows |
| Key rotation | Rotate keys immediately if exposed in logs/errors |

### Codespace Security Note

GitHub Codespaces are **private to each user**. When someone forks or clones the repository:
- They get the code but NOT your `.env` file
- They must configure their own API keys
- Your secrets remain isolated in your Codespace

### Test Output Leakage Prevention

pydantic-settings automatically loads environment variables. Without isolation, test assertions can expose real credentials:

```python
# BAD: Real API key appears in error message!
# AssertionError: assert 'PKRL2TT6...' == ''

# GOOD: Use fixture to isolate environment
@pytest.fixture
def clean_alpaca_env(monkeypatch):
    """Clear all Alpaca env vars to prevent credential leakage."""
    for var in ["ALPACA_LIVE_API_KEY", "ALPACA_PAPER_API_KEY", ...]:
        monkeypatch.delenv(var, raising=False)

def test_default_values(clean_alpaca_env):
    config = AlpacaConfig()
    assert config.paper_api_key == ""  # Safe: env vars cleared
```

## 5. Testing with Live vs Paper Credentials

| Test Type | Credentials Used | Real API Calls? | Purpose |
|-----------|------------------|-----------------|---------|
| **Unit Tests** | None (mocked) | ❌ No | Test logic in isolation |
| **Integration Tests** | Paper only | ✅ Yes (sandbox) | Test real API interactions safely |
| **E2E Tests** | Paper only | ✅ Yes (sandbox) | Full system verification |
| **Production** | Live | ✅ Yes (real money) | Actual trading |

**Rule**: Never use Live credentials in automated tests. Paper API provides identical behavior without financial risk.

```python
# In conftest.py or test setup
def get_test_credentials() -> AlpacaCredentials:
    """Always return Paper credentials for testing."""
    return AlpacaCredentials(
        api_key="test-paper-key",
        api_secret="test-paper-secret",
        base_url="https://paper-api.alpaca.markets",
        is_paper=True,
    )
```
