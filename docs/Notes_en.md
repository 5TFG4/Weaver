### Project Background and Objectives

*#### **1. GLaDOS (Main Application Class)**

- **Responsibilities:**
  - **System Initialization:** Publishes `system_init` event and coordinates module startup
  - **Health Monitoring:** Collect module health status and coordinate system readiness
  - **Module Coordination:** Wait for all modules to report ready before starting operations
  - **Shutdown Coordination:** Orchestrate ordered shutdown sequence to prevent issues
  - **Emergency Response:** Handle system errors and emergency shutdowns
- **Design Features:**
  - Module health check coordination before system operations
  - Ordered shutdown sequence (strategies → data → APIs → core)
  - Emergency intervention capabilities
- **Event Communication:**
  - Publishes: `system_init`, `system_ready`, `system_terminate`, `emergency_shutdown`
  - Listens: `module_ready`, `module_health`, `system_error`, `module_shutdown_request`es:**
Build a Python-based automated trading bot, deployable on a local server, capable of 24/7 operation. The bot will be containerized using Docker and support the following core functionalities:

- Integration with multiple exchange APIs (with priority support for Alpaca).
- Dynamic loading and execution of trading strategies.
- Logging of trade history with support for strategy backtesting using local data.
- A React.js-based web interface for viewing trading data and records.

**Key Features:**

- **Event-Driven Architecture:** Autonomous module communication through internal event bus.
- **Modular design** to facilitate scalability and extensibility.
- Backend architecture based on RESTful APIs.
- Sensitive data managed using GitHub Secrets, with CI/CD workflows implemented via GitHub Actions.

---

### Event-Driven Architecture Design

**Core Principle:** Modules communicate autonomously through events, with minimal central coordination.

**GLaDOS Role:** Minimal orchestrator handling only system initialization, health monitoring, and shutdown coordination.

**Module Autonomy:** Each module manages its own lifecycle and communicates directly with other modules via events.

**Communication Flow Example:**
1. GLaDOS publishes `system_init` → all modules start initialization
2. Modules complete startup and publish `module_ready` → GLaDOS collects readiness
3. GLaDOS publishes `system_ready` when all modules are ready → operations begin
4. Marvin publishes `strategy_load_request` → strategies initialize  
5. Strategy publishes `trading_platform_request` → Veda responds
6. Veda publishes `platform_available` → strategies receive
7. Strategy publishes `market_data_request` → WallE/Veda respond
8. Continuous autonomous communication...
9. GLaDOS publishes `system_terminate` → ordered shutdown sequence begins

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

### System Coordination Patterns

#### **Module Health Check System**

**Startup Coordination:**
1. GLaDOS publishes `system_init` 
2. Each module initializes and publishes `module_ready` with status
3. GLaDOS waits for all modules to report ready
4. GLaDOS publishes `system_ready` → trading operations begin
5. Periodic health checks via `module_health` events

**Health Check Events:**
- `module_ready`: Module initialization complete and ready for operations
- `module_health`: Periodic health status (healthy/degraded/error)
- `system_ready`: All modules ready, trading operations can begin
- `system_status_check`: Request all modules to report current health

#### **Ordered Shutdown Sequence**

**Shutdown Priority Order:**
1. **Strategies** (Marvin) - Stop generating new signals, complete pending operations
2. **UI Backend** (Haro) - Close WebSocket connections, stop API endpoints  
3. **Exchange APIs** (Veda) - Cancel pending orders, close API connections
4. **Database** (WallE) - Flush pending writes, close database connections
5. **Core Systems** - Event bus, logging, application shutdown

**Shutdown Events:**
- `system_terminate`: Begin ordered shutdown sequence
- `module_shutdown_complete`: Module has completed shutdown
- `emergency_shutdown`: Immediate shutdown required
- `shutdown_timeout`: Module taking too long to shutdown

---

### Event Bus Communication Patterns

#### **System Events (GLaDOS Managed):**
- `system_init`: System startup notification
- `system_ready`: All modules ready, operations can begin
- `system_terminate`: Begin ordered shutdown sequence
- `system_status_check`: Request system-wide health check
- `emergency_shutdown`: Immediate shutdown required
- `module_ready`: Module initialization complete
- `module_health`: Module health status report
- `module_shutdown_complete`: Module shutdown confirmation
- `system_error`: Critical error requiring GLaDOS intervention

#### **Module-to-Module Events:**

**Inter-Module Communication:**

- **Core Architecture:**
  - GLaDOS serves as the main application class, managing system lifecycle and module coordination.
  - GLaDOS uses the core.Application class for system infrastructure (event bus, startup/shutdown).
  - Haro provides RESTful APIs and WebSocket connections for frontend communication.
  - Inter-module communication is facilitated by an internal event bus for real-time data flow and command execution.

**Example Data Flow:**

1. GLaDOS initializes all modules and starts the event bus during system startup.
2. Veda periodically fetches market data and publishes 'market_data' events to the event bus.
3. Marvin subscribes to 'market_data' events, processes data, and publishes 'trade_signal' events.
4. GLaDOS receives 'trade_signal' events and coordinates with Veda to execute orders.
5. Order execution results are published as 'order_filled' events, logged by WallE, and sent to frontend via Haro's WebSocket.

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
│   │   │   ├── application.py    # Core application class used by GLaDOS for system management
│   │   │   ├── logger.py         # Logging configuration and utilities
│   │   │   └── constants.py      # Application-wide constants (ALPACA, etc.)
│   │   │
│   │   ├── modules/              # All main business modules (uniform treatment)
│   │   │   ├── glados.py         # Main Application Class (system orchestrator, module coordinator)
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

