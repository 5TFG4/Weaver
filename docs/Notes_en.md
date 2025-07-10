### Project Background and Objectives

**Objectives:**
Build a Python-based automated trading bot, deployable on a local server, capable of 24/7 operation. The bot will be containerized using Docker and support the following core functionalities:

- Integration with multiple exchange APIs (with priority support for Alpaca).
- Dynamic loading and execution of trading strategies.
- Logging of trade history with support for strategy backtesting using local data.
- A React.js-based web interface for viewing trading data and records.

**Key Features:**

- Modular design to facilitate scalability and extensibility.
- Backend architecture based on RESTful APIs.
- Sensitive data managed using GitHub Secrets, with CI/CD workflows implemented via GitHub Actions.
- Event-driven architecture with internal message bus for module communication.

---

### Module Overview

#### **1. GLaDOS (Main Control System)**

- **Responsibilities:**
  - Coordinate communication between modules, acting as the system’s central scheduler.
  - Expose RESTful API endpoints for frontend interaction.
  - Call Veda to fetch market data and trigger Marvin to execute strategies.
  - Log actions and monitor system status.
- **Design Features:**
  - Module coordination through internal event bus system.

#### **2. Veda (API Interaction Module)**

- **Responsibilities:**
  - Handle all interactions with exchanges, including:
    - Fetching market data.
    - Retrieving account information.
    - Executing buy/sell orders.
  - Support historical data fetching and save it to a local database.
  - Provide standardized interfaces to facilitate the addition of new exchanges.
- **Design Features:**
  - Manages multiple exchange connectors through plugin architecture.
  - Direct API calls with async support for high-performance data operations.

#### **3. WallE (Data Storage Module)**

- **Responsibilities:**
  - Manage the PostgreSQL database to store trading records and market data.
  - Provide efficient data read/write interfaces for other modules.
  - Save strategy configurations and backtesting results.
- **Design Features:**
  - Utilize SQLAlchemy to implement an ORM layer, supporting complex queries and transaction handling.

#### **4. Marvin (Strategy Execution Module)**

- **Responsibilities:**
  - Dynamically load strategy modules and generate trade signals based on market data.
  - Provide a unified interface to standardize the execution of all strategy modules.
  - Support multi-strategy combinations and complex decision-making logic.
  - Directly call Veda for additional data required for strategy logic.
- **Design Features:**
  - Each strategy is implemented as a standalone Python module for easy maintenance and extension.
  - Returns standardized results for GLaDOS to process.

#### **5. Greta (Backtesting Module)**

- **Responsibilities:**
  - Use local historical data to simulate trades.
  - Return backtesting results, including profitability and risk metrics.
  - Save backtesting results to the database for future analysis.
- **Design Features:**
  - Support flexible backtesting configurations, enabling batch tests for multiple strategies.

#### **6. Haro (UI Backend Module)**

- **Responsibilities:**
  - Provide FastAPI routes specifically for frontend communication.
  - Handle WebSocket connections for real-time data updates to the UI.
  - Format data from other modules for frontend consumption.
  - Manage UI-specific concerns (user sessions, UI state, chart data formatting).
- **Design Features:**
  - Dedicated UI backend - while GLaDOS handles core business logic, Haro focuses on UI needs.
  - WebSocket support for real-time updates without polling.
  - Clean separation: frontend/ directory contains React app, Haro provides its backend API.

---

### Communication and Data Flow Design

**Inter-Module Communication:**

- **Core Architecture:**
  - GLaDOS serves as the core of the system, coordinating communication between modules.
  - GLaDOS interacts with the frontend through RESTful APIs provided by FastAPI.
  - Inter-module communication is facilitated by an internal event bus for real-time data flow and command execution.

**Example Data Flow:**

1. GLaDOS periodically calls Veda to fetch market data, which is published to the event bus.
2. Marvin subscribes to market data events, processes the data and generates trading instructions.
3. GLaDOS receives trading signals and forwards instructions to Veda for execution.
4. Execution results are published to the event bus, logged by GLaDOS, and sent to the frontend via WebSocket.

---

### Tech Stack

- **Backend:** FastAPI (RESTful API)
- **Frontend:** React.js
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Module Communication:** Internal Event Bus
- **Real-time Updates:** WebSockets
- **Containerization:** Docker + Docker Compose
- **CI/CD:** GitHub Actions
- **Monitoring and Logging:** Prometheus/Grafana + Python logging

---

### Directory Structure

```plaintext
weaver/
├── backend/                      # Backend Python code
│   ├── src/                      # Main application code
│   │   ├── core/                 # Core system infrastructure
│   │   │   ├── __init__.py
│   │   │   ├── event_bus.py      # Publishes: 'market_data', 'trade_signal', 'order_filled'
│   │   │   ├── application.py    # Starts all modules, coordinates everything
│   │   │   ├── logging.py        # Logging configuration and utilities
│   │   │   └── constants.py      # Application-wide constants (ALPACA, etc.)
│   │   │
│   │   ├── modules/              # All main business modules (uniform treatment)
│   │   │   ├── glados.py         # Main orchestrator (starts strategies, handles signals)
│   │   │   ├── veda.py           # Exchange manager (routes orders to correct platform)
│   │   │   ├── walle.py          # Database operations (saves trades, market data)
│   │   │   ├── marvin.py         # Strategy executor (loads and runs strategies)
│   │   │   ├── greta.py          # Backtesting engine (simulates historical trades)
│   │   │   └── haro.py           # UI Backend (FastAPI routes for frontend, WebSocket for real-time updates)
│   │   │
│   │   ├── lib/                  # Shared utilities and helpers
│   │   │   ├── __init__.py
│   │   │   └── utils.py          # General utility functions (date parsing, validation, etc.)
│   │   │
│   │   ├── connectors/           # Exchange implementations (when you have multiple)
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Common interface: get_data(), place_order()
│   │   │   ├── alpaca.py         # Alpaca API implementation
│   │   │   ├── binance.py        # Binance API implementation (future)
│   │   │   └── coinbase.py       # Coinbase Pro API implementation (future)
│   │   │
│   │   ├── strategies/           # Trading strategies (when you have multiple)
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Base strategy class with common methods
│   │   │   ├── simple_ma.py      # Moving average strategy (includes MA calculation)
│   │   │   ├── rsi_strategy.py   # RSI strategy (includes RSI calculation)
│   │   │   ├── bollinger_bands.py # Bollinger strategy (includes Bollinger calculation)
│   │   │   ├── portfolio_risk.py # Portfolio-level risk management
│   │   │   └── buy_and_hold.py   # Simple buy and hold strategy
│   │   │
│   │   ├── models/               # Database models (when you have multiple)
│   │   │   ├── __init__.py
│   │   │   ├── trade.py          # Trade table: symbol, qty, price, timestamp
│   │   │   ├── market_data.py    # Market data: symbol, ohlcv, timestamp
│   │   │   ├── strategy_run.py   # Strategy execution records
│   │   │   └── portfolio.py      # Portfolio positions and balances
│   │   │
│   │   └── weaver.py             # Entry point: python -m src.weaver
│
├── frontend/                     # React.js web interface
│   ├── src/
│   │   ├── components/           # React components (charts, tables, forms)
│   │   ├── pages/                # React pages (dashboard, strategies, trades)
│   │   ├── hooks/                # Custom React hooks
│   │   ├── services/             # API calls to backend
│   │   └── App.js                # Main React app component
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   ├── package.json              # NPM dependencies and scripts (required by React)
│   └── package-lock.json         # Exact dependency versions (required by NPM)
│
├── tests/                        # Unit tests mirroring backend/src structure
│   ├── test_modules/             # Tests for modules/
│   ├── test_strategies/          # Tests for strategies/
│   ├── test_connectors/          # Tests for connectors/
│   ├── test_models/              # Tests for models/
│   └── conftest.py               # Pytest configuration
│
├── docker/                       # Container configurations and deployment
│   ├── backend/                  # Backend container setup
│   │   ├── Dockerfile            # Production backend container
│   │   └── Dockerfile.dev        # Development backend container
│   │
│   ├── frontend/                 # Frontend container setup
│   │   ├── Dockerfile            # Production frontend container (nginx)
│   │   └── Dockerfile.dev        # Development frontend container
│   │
│   ├── docker-compose.yml        # Production deployment
│   ├── docker-compose.dev.yml    # Development environment
│   ├── example.env               # Example production environment variables
│   ├── example.env.dev           # Example development environment variables
│   ├── .env                      # Actual production environment variables (gitignored)
│   ├── .env.dev                  # Actual development environment variables (gitignored)
│   └── .dockerignore             # Files to exclude from docker build
│
├── docs/                         # Documentation
│   ├── Notes_en.md               # English architecture documentation
│   ├── Notes_cn.md               # Chinese architecture documentation
│   └── API.md                    # API endpoint documentation
│
├── logs/                         # Application logs (created at runtime)
│   ├── app.log                   # General application logs
│   └── main.log                  # Main process logs
│
├── .github/                      # CI/CD workflows and issue templates
│   ├── workflows/                # GitHub Actions workflows
│   │   ├── ci.yml                # Continuous integration
│   │   └── deploy.yml            # Deployment pipeline
│   ├── ISSUE_TEMPLATE/           # Issue templates
│   │   ├── BUG-REPORT.yml
│   │   └── FEATURE-REQUEST.yml
│   └── PULL_REQUEST_TEMPLATE.md
│
├── .devcontainer/                # VS Code development container
│   └── devcontainer.json         # Container configuration for development
│
├── weaver.py                     # Alternative entry point (backward compatibility)
├── README.md                     # Project overview and setup instructions
└── .gitignore                    # Git ignore patterns
```

