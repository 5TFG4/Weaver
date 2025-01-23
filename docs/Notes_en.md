### Project Background and Goals

**Goals**:
Develop a Python-based automated trading bot that operates 24/7 on a local server. The bot will be containerized using Docker and will include the following core functionalities:

- Interact with multiple exchange APIs (initially supporting Alpaca).
- Dynamically load and execute complex trading strategies.
- Record trading history and support backtesting strategies using local data.
- Provide a React.js-based web interface to monitor trading information and logs.

**Features**:

- Modular design with extensibility in mind.
- Backend architecture based on RESTful APIs.
- Secure sensitive information using GitHub Secrets and enable CI/CD with GitHub Actions.
- Task scheduling and event-driven design using Celery integrated with RabbitMQ.

---

### Module Breakdown

#### **1. GLaDOS (Core Control System)**

- **Responsibilities**:
  - Coordinate communication between modules, acting as the system’s central dispatcher.
  - Expose RESTful API endpoints for frontend interactions.
  - Retrieve market data from Veda and trigger strategy execution in Marvin.
  - Log system activities and monitor system health.
- **Design Characteristics**:
  - Use Celery for asynchronous task distribution to other modules.

#### **2. Veda (API Data Processing Module)**

- **Responsibilities**:
  - Interact with exchange APIs to:
    - Fetch market data.
    - Retrieve account information.
    - Execute buy/sell orders.
  - Support historical data fetching and save it to the local database.
  - Provide standardized interfaces to simplify extending support for additional exchanges.
- **Design Characteristics**:
  - Use Celery for handling high-concurrency tasks.
  - Dynamically load exchange-specific implementations.

#### **3. WallE (Data Storage Module)**

- **Responsibilities**:
  - Manage the PostgreSQL database for storing trading records and market data.
  - Provide efficient data read/write interfaces for other modules.
  - Store strategy configurations and backtesting results.
- **Design Characteristics**:
  - Utilize SQLAlchemy as an ORM layer to support complex queries and transactions.

#### **4. Marvin (Strategy Execution Module)**

- **Responsibilities**:
  - Dynamically load strategy modules and generate trading signals based on market data.
  - Provide a unified interface to standardize strategy module interactions.
  - Support multi-strategy combinations and complex decision logic.
  - Directly request additional data from Veda when required for high-frequency scenarios.
- **Design Characteristics**:
  - Each strategy is implemented as an independent Python module for flexibility and maintainability.
  - Return standardized results for seamless integration with GLaDOS.

#### **5. Greta (Backtesting Module)**

- **Responsibilities**:
  - Simulate trading strategies using historical data.
  - Return backtesting results, including key performance metrics like profitability and risk.
  - Store backtesting results in the database for future analysis.
- **Design Characteristics**:
  - Support flexible configurations to enable batch backtesting for multiple strategies.

#### **6. Haro (Web UI Interaction Module)**

- **Responsibilities**:
  - Provide a React.js-based frontend interface to display:
    - Account information.
    - Current strategy status.
    - Historical trading logs.
    - Backtesting results.
  - Allow users to manage strategies and monitor system activity via the interface.
- **Design Characteristics**:
  - Use Axios for REST API communication.
  - Support real-time data updates via WebSocket.

---

### Communication and Data Flow Design

**Inter-Module Communication**:

- **Core Architecture**:
  - GLaDOS serves as the system’s central controller, managing communication between modules.
  - GLaDOS communicates with the frontend via FastAPI, providing RESTful API endpoints.
  - Celery and RabbitMQ facilitate asynchronous task scheduling and message passing between modules.

**Data Flow Example**:

1. GLaDOS periodically triggers Veda to fetch market data, broadcasting the results via Celery to Marvin.
2. Marvin processes the market data, generates trading signals, and sends instructions back to GLaDOS.
3. GLaDOS forwards these instructions to Veda, which executes the trades using exchange APIs.
4. Execution results are sent back to GLaDOS via Celery, logged, and optionally displayed on the frontend.

---

### Tech Stack

- **Backend**: FastAPI (RESTful API)
- **Frontend**: React.js
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Task Scheduling**: Celery + RabbitMQ
- **Containerization**: Docker + Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring and Logging**: Prometheus/Grafana + Python logging

---

### Directory Structure

```plaintext
project/
├── backend/
│   ├── glados/        # Core Control System
│   │   ├── __init__.py
│   │   ├── controller.py  # Core logic
│   │   ├── routes.py      # FastAPI route definitions
│   │   ├── tasks.py       # Celery tasks
│   │   └── tests/         # Test files
│   ├── veda/          # API Data Processing Module
│   │   ├── __init__.py
│   │   ├── alpaca.py       # Alpaca exchange implementation
│   │   ├── tasks.py        # Celery tasks
│   │   └── tests/          # Test files
│   ├── walle/         # Data Storage Module
│   │   ├── __init__.py
│   │   ├── models.py       # Database models
│   │   ├── database.py     # Database connection logic
│   │   └── tests/          # Test files
│   ├── marvin/        # Strategy Execution Module
│   │   ├── __init__.py
│   │   ├── base_strategy.py  # Strategy base class
│   │   ├── strategies/       # Strategy implementations
│   │   └── tests/            # Test files
│   ├── greta/         # Backtesting Module
│   │   ├── __init__.py
│   │   ├── backtest.py       # Backtesting logic
│   │   └── tests/            # Test files
│   ├── tasks.py       # Global Celery task definitions
│   ├── main.py        # FastAPI entry point
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── App.js     # React entry point
│   │   └── api.js     # API request wrapper
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   ├── celery.Dockerfile
│   └── docker-compose.yml
├── .github/
│   ├── workflows/     # GitHub Actions configurations
├── .env.example       # Environment variable template
├── README.md          # Project documentation
└── requirements.txt   # Python dependencies
```

