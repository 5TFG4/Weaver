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
- Task scheduling and event-driven architecture powered by Celery combined with Redis.

---

### Module Overview

#### **1. GLaDOS (Main Control System)**

- **Responsibilities:**
  - Coordinate communication between modules, acting as the system’s central scheduler.
  - Expose RESTful API endpoints for frontend interaction.
  - Call Veda to fetch market data and trigger Marvin to execute strategies.
  - Log actions and monitor system status.
- **Design Features:**
  - Tasks are distributed to other modules asynchronously via Celery.

#### **2. Veda (API Interaction Module)**

- **Responsibilities:**
  - Handle all interactions with exchanges, including:
    - Fetching market data.
    - Retrieving account information.
    - Executing buy/sell orders.
  - Support historical data fetching and save it to a local database.
  - Provide standardized interfaces to facilitate the addition of new exchanges.
- **Design Features:**
  - Execute high-concurrency tasks using Celery.
  - Dynamically load implementations for different exchanges.

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

#### **6. Haro (Web UI Interaction Module)**

- **Responsibilities:**
  - Provide a React.js-based frontend interface to display:
    - Account information.
    - Current strategy status.
    - Historical trading records.
    - Backtesting results.
  - Enable users to manage strategies and monitor the system through the interface.
- **Design Features:**
  - Use Axios to communicate with the backend via REST APIs.
  - Support real-time data updates through WebSocket.

---

### Communication and Data Flow Design

**Inter-Module Communication:**

- **Core Architecture:**
  - GLaDOS serves as the core of the system, coordinating communication between modules.
  - GLaDOS interacts with the frontend through RESTful APIs provided by FastAPI.
  - Inter-module communication is facilitated by Celery and Redis for asynchronous task distribution and result processing.

**Example Data Flow:**

1. GLaDOS periodically calls Veda to fetch market data, which is distributed to Marvin via Celery.
2. Marvin processes the data and generates trading instructions, sending them back to GLaDOS.
3. GLaDOS forwards the trading instructions to Veda, which interacts with the exchange API to execute trades.
4. Execution results are passed back to GLaDOS via Celery. GLaDOS logs the results and notifies the frontend.

---

### Tech Stack

- **Backend:** FastAPI (RESTful API)
- **Frontend:** React.js
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Task Scheduling:** Celery + Redis
- **Containerization:** Docker + Docker Compose
- **CI/CD:** GitHub Actions
- **Monitoring and Logging:** Prometheus/Grafana + Python logging

---

### Directory Structure

```plaintext
weaver/
├── src/                           
│   ├── api/                      # API layer: FastAPI routes and application startup
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI application entry point
│   │   └── routes.py             # Route definitions
│   │
│   ├── modules/                  # Core modules of the project
│   │   ├── glados/               # Main control system: schedules tasks and coordinates modules
│   │   │   ├── __init__.py
│   │   │   ├── controller.py     # Core business logic
│   │   │   └── tasks.py          # Celery tasks for GLaDOS
│   │   │
│   │   ├── veda/                 # API interaction module: handles exchange integration (e.g., Alpaca)
│   │   │   ├── __init__.py
│   │   │   ├── alpaca.py         # Alpaca exchange integration
│   │   │   └── tasks.py          # Asynchronous tasks for Veda
│   │   │
│   │   ├── walle/                # Data storage module, manages database operations
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # Data model definitions
│   │   │   └── database.py       # Database connection and operations
│   │   │
│   │   ├── marvin/               # Strategy execution module: loads and executes trading strategies
│   │   │   ├── __init__.py
│   │   │   ├── base_strategy.py  # Base strategy class
│   │   │   └── strategies/       # Specific strategy implementations
│   │   │
│   │   ├── greta/                # Backtesting module: simulates trades using historical data
│   │   │   ├── __init__.py
│   │   │   └── backtest.py       # Backtesting logic
│   │   │
│   │   └── haro/                 # Frontend integration module: provides API support for the React UI
│   │       ├── __init__.py
│   │       └── api.py            # API encapsulation
│   │
│   ├── lib/                      # Common utilities and helper functions
│   │   ├── __init__.py
│   │   └── utils.py
│   │
│   ├── config/                   # Configuration files (e.g., logging, database, Celery settings)
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── celery_config.py
│   │
│   ├── tasks.py                  # Global tasks entry point (if needed)
│   └── main.py                   # Project entry point (can be used to start FastAPI, etc.)
│
├── tests/                        # Unit tests for each module
│   ├── glados/
│   ├── veda/
│   ├── walle/
│   ├── marvin/
│   ├── greta/
│   └── haro/
│
├── docker/                       # Docker configuration directory
│   ├── backend/                  # Backend Docker configuration
│   │   ├── Dockerfile
│   │   ├── Dockerfile.dev
│   │   └── requirements.txt
│   ├── frontend/                 # Frontend Docker configuration
│   │   ├── Dockerfile
│   │   ├── Dockerfile.dev
│   │   └── package.json
│   ├── .dockerignore
│   ├── .env
│   ├── .env.dev
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── example.env
│   └── example.env.dev
│
├── docs/                         # Project documentation
│   ├── Notes_en.md
│   └── Notes_cn.md               # Chinese documentation
│
├── weaver.py                     # Entry Point
│
└── .github/                      # GitHub Actions workflows and CI/CD configurations
    └── workflows/
```

