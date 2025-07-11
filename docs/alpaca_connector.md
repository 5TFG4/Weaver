# Alpaca Connector Documentation

## Overview

The Alpaca connector provides real-time trading capabilities with Alpaca Markets, supporting both paper trading and live trading modes. It implements the `BaseTradingConnector` interface and integrates seamlessly with the Weaver trading system.

## Features

- ✅ **Paper Trading**: Safe testing environment
- ✅ **Live Trading**: Real market trading
- ✅ **Order Management**: Market, limit, stop orders
- ✅ **Position Tracking**: Real-time position updates
- ✅ **Account Information**: Balance, buying power, etc.
- ✅ **Historical Data**: OHLCV data retrieval
- ✅ **Market Data Streaming**: Real-time price updates
- ✅ **Error Handling**: Comprehensive error management
- ✅ **Type Safety**: Full TypeScript-style type annotations

## Installation

The Alpaca connector is already included in the Weaver system. Required dependencies:

```bash
pip install aiohttp
```

## Configuration

### Basic Configuration

```python
from connectors.alpaca_connector import AlpacaConnectorConfig

config = AlpacaConnectorConfig(
    name="alpaca_trading",
    enabled=True,
    paper_trading=True,  # Set to False for live trading
    api_key="your_api_key_here",
    secret_key="your_secret_key_here",
    supported_symbols=["AAPL", "GOOGL", "MSFT"],
    commission_rate=Decimal("0.0"),  # Alpaca has no commission
    timeout=30.0,
    retry_attempts=3
)
```

### Using Environment Variables

```python
import os

config = AlpacaConnectorConfig(
    name="alpaca_trading",
    enabled=True,
    paper_trading=True,
    api_key=os.getenv("ALPACA_API_KEY"),
    secret_key=os.getenv("ALPACA_SECRET_KEY"),
    supported_symbols=["AAPL", "GOOGL", "MSFT"]
)
```

### Environment Variables

```bash
export ALPACA_API_KEY="your_api_key_here"
export ALPACA_SECRET_KEY="your_secret_key_here"
```

## Usage

### Basic Usage

```python
import asyncio
from connectors.connector_factory import ConnectorFactory, ConnectorType
from connectors.alpaca_connector import AlpacaConnectorConfig

async def main():
    # Create factory
    factory = ConnectorFactory()
    
    # Create configuration
    config = AlpacaConnectorConfig(
        name="alpaca_trading",
        enabled=True,
        paper_trading=True,
        api_key="your_api_key",
        secret_key="your_secret_key",
        supported_symbols=["AAPL", "GOOGL", "MSFT"]
    )
    
    # Create connector
    connector = factory.create_trading_connector(ConnectorType.ALPACA, config)
    
    # Connect to Alpaca
    await connector.connect()
    
    # Submit a market order
    order = Order(
        symbol="AAPL",
        quantity=Decimal("10"),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET
    )
    
    order_id = await connector.submit_order(order)
    print(f"Order submitted: {order_id}")
    
    # Check order status
    order_status = await connector.get_order_status(order_id)
    print(f"Order status: {order_status.status}")
    
    # Get account information
    account = await connector.get_account_info()
    print(f"Buying power: {account.buying_power}")
    
    # Get current positions
    positions = await connector.get_positions()
    for position in positions:
        print(f"Position: {position.symbol} - {position.quantity}")
    
    # Disconnect
    await connector.disconnect()

asyncio.run(main())
```

### Order Types

```python
# Market order
market_order = Order(
    symbol="AAPL",
    quantity=Decimal("10"),
    side=OrderSide.BUY,
    order_type=OrderType.MARKET
)

# Limit order
limit_order = Order(
    symbol="GOOGL",
    quantity=Decimal("5"),
    side=OrderSide.SELL,
    order_type=OrderType.LIMIT,
    price=Decimal("150.00")
)

# Stop order
stop_order = Order(
    symbol="MSFT",
    quantity=Decimal("20"),
    side=OrderSide.SELL,
    order_type=OrderType.STOP,
    stop_price=Decimal("280.00")
)
```

### Historical Data

```python
# Get historical data
historical_data = await connector.get_historical_data(
    symbol="AAPL",
    timeframe="1d",
    start_date="2023-01-01",
    end_date="2023-12-31"
)

for bar in historical_data:
    print(f"{bar['timestamp']}: {bar['close']}")
```

## API Reference

### AlpacaConnectorConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | - | Connector name |
| `enabled` | bool | True | Enable/disable connector |
| `paper_trading` | bool | True | Use paper trading mode |
| `api_key` | str | "" | Alpaca API key |
| `secret_key` | str | "" | Alpaca secret key |
| `supported_symbols` | List[str] | [] | List of tradeable symbols |
| `commission_rate` | Decimal | 0.0 | Commission rate (Alpaca is commission-free) |
| `timeout` | float | 30.0 | Request timeout in seconds |
| `retry_attempts` | int | 3 | Number of retry attempts |
| `retry_delay` | float | 1.0 | Delay between retries |

### Methods

#### Connection Management
- `connect()`: Connect to Alpaca API
- `disconnect()`: Disconnect from Alpaca API
- `health_check()`: Check connection health

#### Order Management
- `submit_order(order)`: Submit an order
- `cancel_order(order_id)`: Cancel an order
- `get_order_status(order_id)`: Get order status
- `validate_order(order)`: Validate order before submission

#### Account & Positions
- `get_account_info()`: Get account information
- `get_positions()`: Get current positions

#### Market Data
- `get_historical_data(symbol, timeframe, start_date, end_date)`: Get historical data

## Error Handling

The connector handles various error scenarios:

```python
try:
    await connector.connect()
except ConnectionError as e:
    print(f"Connection failed: {e}")
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Paper Trading vs Live Trading

### Paper Trading (Default)
- Safe testing environment
- No real money involved
- Uses `https://paper-api.alpaca.markets`
- Perfect for development and testing

### Live Trading
- Real money trading
- Requires production API credentials
- Uses `https://api.alpaca.markets`
- Set `paper_trading=False` in configuration

## Best Practices

1. **Always start with paper trading** when developing
2. **Use environment variables** for API credentials
3. **Implement proper error handling**
4. **Validate orders** before submission
5. **Monitor positions** and account balance
6. **Use appropriate timeouts** for network requests
7. **Test thoroughly** before live trading

## Integration with Weaver

The Alpaca connector integrates with the Weaver event system:

```python
from core.event_bus import EventBus

# Create event bus
event_bus = EventBus()

# Create connector with event bus
connector = AlpacaConnector(config, event_bus)

# Listen for events
@event_bus.subscribe("order_update")
async def handle_order_update(event):
    print(f"Order update: {event}")

@event_bus.subscribe("position_update")
async def handle_position_update(event):
    print(f"Position update: {event}")
```

## Testing

Run the test script to verify the connector:

```bash
python test_alpaca_connector.py
```

Run the example usage:

```bash
python example_alpaca_usage.py
```

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure `aiohttp` is installed
2. **Authentication Error**: Check API key and secret
3. **Symbol Not Supported**: Verify symbol is in `supported_symbols`
4. **Connection Timeout**: Increase timeout value
5. **Rate Limiting**: Implement exponential backoff

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

1. **Never commit API keys** to version control
2. **Use environment variables** for credentials
3. **Rotate API keys** regularly
4. **Monitor account activity**
5. **Use paper trading** for development

## Contributing

When contributing to the Alpaca connector:

1. Follow the existing code style
2. Add tests for new features
3. Update documentation
4. Ensure type safety
5. Test with both paper and live trading

## License

This connector is part of the Weaver trading system and follows the same license terms.
