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
- Task scheduling and event-driven architecture powered by Celery combined with RabbitMQ.

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
  - Inter-module communication is facilitated by Celery and RabbitMQ for asynchronous task distribution and result processing.

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
- **Task Scheduling:** Celery + RabbitMQ
- **Containerization:** Docker + Docker Compose
- **CI/CD:** GitHub Actions
- **Monitoring and Logging:** Prometheus/Grafana + Python logging

---

### Directory Structure

```plaintext
weaver/
├── src/               # Main code directory
│   ├── glados/        # Main Control System
│   │   ├── __init__.py
│   │   ├── controller.py  # Core logic
│   │   ├── routes.py      # FastAPI routes
│   │   ├── tasks.py       # Celery tasks
│   ├── veda/          # API Interaction Module
│   │   ├── __init__.py
│   │   ├── alpaca.py       # Alpaca exchange integration
│   │   ├── tasks.py        # Celery tasks
│   ├── walle/         # Data Storage Module
│   │   ├── __init__.py
│   │   ├── models.py       # Data models
│   │   ├── database.py     # Database connection logic
│   ├── marvin/        # Strategy Execution Module
│   │   ├── __init__.py
│   │   ├── base_strategy.py  # Strategy base class
│   │   ├── strategies/       # Strategy implementations
│   ├── greta/         # Backtesting Module
│   │   ├── __init__.py
│   │   ├── backtest.py       # Backtesting logic
│   ├── haro/          # Frontend Module
│   │   ├── components/
│   │   ├── pages/
│   │   ├── App.js          # React entry point
│   │   └── api.js          # Frontend API abstraction
│   ├── tasks.py       # Celery global tasks
│   ├── main.py        # FastAPI entry point
├── tests/             # Test directory
│   ├── glados/        # GLaDOS tests
│   ├── veda/          # Veda tests
│   ├── walle/         # WallE tests
│   ├── marvin/        # Marvin tests
│   ├── greta/         # Greta tests
│   ├── haro/          # Haro tests
├── docker/            # Docker configuration directory
│   ├── backend/       # Backend Docker configuration
│   │   ├── Dockerfile
│   │   ├── Dockerfile.dev
│   │   ├── requirements.txt
│   ├── frontend/      # Frontend Docker configuration
│   │   ├── Dockerfile
│   │   ├── Dockerfile.dev
│   ├── .dockerignore
│   ├── .env
│   ├── .env.dev
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── example.env
│   └── example.env.dev
├── .github/
│   ├── workflows/     # GitHub Actions workflows
└── README.md          # Project documentation
```

