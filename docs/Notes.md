### 项目背景和目标

**目标**：
构建一个 Python 自动交易机器人，部署在本地服务器上，能够 24/7 运行，通过 Docker 容器化部署，支持以下功能：

- 与多个交易所 API 交互（当前优先支持 Alpaca）。
- 执行复杂策略（通过 Python 模块动态加载）。
- 记录交易历史，并支持基于本地数据的策略回测。
- 提供一个基于 React.js 的 Web 界面，用于查看交易信息和记录。

**特点**：

- 模块化设计，支持扩展。
- 基于 RESTful API 的后端架构。
- 通过 GitHub Secrets 管理敏感信息，使用 GitHub Actions 实现 CI/CD。
- 以 Celery 为核心，支持任务调度与事件驱动的结合。

---

### 模块划分

#### **1. GLaDOS (主控系统)**

- **职责**：
  - 协调模块间的通信。
  - 调度 Veda 从交易所获取市场数据。
  - 调用 Marvin 的策略模块，接收其返回的操作指令。
  - 将操作指令传递给 Veda 执行。
  - 记录操作日志，监控系统状态。
- **设计原则**：
  - 职责单一，不直接与交易所或策略交互。

#### **2. Veda (API接口数据处理模块)**

- **职责**：
  - 负责与交易所的所有交互，包括：
    - 获取账户信息。
    - 拉取市场数据。
    - 执行买卖订单。
  - 支持历史数据抓取，并保存到本地数据库。
  - 提供标准化接口，使扩展到其他交易所更加容易。
- **设计特点**：
  - 模块化交易所支持：通过定义统一接口，动态加载不同交易所实现。
  - 以 Celery 为基础，支持高并发任务的异步处理。

#### **3. WallE (数据存储模块)**

- **职责**：
  - 管理 PostgreSQL 数据库。
  - 存储交易记录、市场数据、策略配置及回测结果。
  - 提供数据读写接口给 GLaDOS、Veda 和 Marvin。
- **设计特点**：
  - 使用 SQLAlchemy 提供 ORM 层。

#### **4. Marvin (策略存储与执行模块)**

- **职责**：
  - 动态加载策略模块，根据市场数据生成操作指令。
  - 提供统一接口，确保所有策略都能被标准化调用。
  - 支持多策略组合和复杂判断逻辑。
  - 可直接请求 Veda 进行额外的数据抓取（少数高频策略场景）。
- **设计特点**：
  - 每个策略以独立的 Python 模块形式实现。
  - 通过标准化返回结构与 GLaDOS 和 Veda 交互。

#### **5. Greta (回测模块)**

- **职责**：
  - 读取本地历史数据，运行策略模拟交易。
  - 返回回测结果，包括收益、风险等关键指标。
  - 保存回测结果到数据库。

#### **6. Haro (Web UI 交互模块)**

- **职责**：
  - 提供基于 React.js 的前端界面，展示：
    - 账户信息。
    - 当前策略状态。
    - 历史交易记录。
    - 回测结果。
  - 与后端交互，支持用户通过界面管理策略和查看日志。
- **设计特点**：
  - 使用 Axios 调用 REST API。
  - 通过 WebSocket 支持实时更新数据。

---

### 通信与数据流设计

**模块间通信**：

- **主控式架构**：
  - GLaDOS 是系统的调度中心，负责模块间的协调。
  - GLaDOS 与各模块通过 RESTful API 通信，或通过直接调用模块提供的接口。

**示例数据流**：

1. GLaDOS 定时调用 Veda 抓取市场数据，并将其广播给 Marvin。
2. Marvin 接收到市场数据后，根据策略需求进行判断。
3. Marvin 返回明确的交易指令（如买入某资产）。
4. GLaDOS 将指令传递给 Veda，Veda 使用交易所模块执行具体操作。
5. Veda 将操作结果返回给 GLaDOS，GLaDOS 记录日志。

---

### 技术栈

- **后端**：FastAPI（RESTful API）
- **前端**：React.js
- **数据库**：PostgreSQL
- **ORM**：SQLAlchemy
- **容器化**：Docker + Docker Compose
- **CI/CD**：GitHub Actions
- **任务调度与事件驱动**：Celery + Redis
- **日志与监控**：Python logging 模块 + Prometheus/Grafana

---

### 目录结构

```plaintext
project/
├── backend/
│   ├── glados/        # 主控系统
│   │   ├── __init__.py
│   │   ├── controller.py  # 核心逻辑
│   │   ├── routes.py      # API 路由
│   │   └── tests/         # 测试文件
│   ├── veda/          # API接口数据处理模块
│   │   ├── __init__.py
│   │   ├── alpaca.py       # Alpaca 接口实现
│   │   ├── tasks.py        # Celery 任务
│   │   └── tests/          # 测试文件
│   ├── walle/         # 数据存储模块
│   │   ├── __init__.py
│   │   ├── models.py       # 数据模型
│   │   ├── database.py     # 数据库连接
│   │   └── tests/          # 测试文件
│   ├── marvin/        # 策略存储与执行模块
│   │   ├── __init__.py
│   │   ├── base_strategy.py  # 策略基类
│   │   ├── strategies/       # 策略实现
│   │   └── tests/            # 测试文件
│   ├── greta/         # 回测模块
│   │   ├── __init__.py
│   │   ├── backtest.py       # 回测逻辑
│   │   └── tests/            # 测试文件
│   ├── tasks.py       # Celery 任务定义
│   ├── main.py        # FastAPI 主入口
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── App.js     # React 主入口
│   │   └── api.js     # 前端 REST API 封装
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   ├── celery.Dockerfile
│   └── docker-compose.yml
├── .github/
│   ├── workflows/     # GitHub Actions 配置
├── .env.example       # 环境变量模板
├── README.md          # 项目说明文档
└── requirements.txt   # Python 依赖
```

---

### 开发计划

1. **初始化项目**：
   - 设置代码仓库和目录结构。
   - 初始化 Docker 环境。
   - 配置基础环境变量和 GitHub Secrets。

2. **GLaDOS 基础框架开发**：
   - 搭建 FastAPI 项目。
   - 定义模块间通信接口。
   - 实现基础日志记录和健康检查接口。

3. **Veda 模块开发**：
   - 集成 Alpaca API。
   - 实现市场数据抓取和下单功能。
   - 定义交易所模块接口，支持未来扩展。

4. **WallE 数据存储模块开发**：
   - 使用 SQLAlchemy 定义数据库模型。
   - 实现交易记录和市场数据的读写功能。

5. **Marvin 策略模块开发**：
   - 定义策略接口。
   - 实现基础策略（如移动均线）。
   - 测试策略模块与 Veda 的集成。

6. **Greta 回测模块开发**：
   - 读取本地历史数据，运行策略模拟交易。
   - 返回回测结果并存储。

7. **Haro 前端开发**：
   - 搭建 React 项目。
   - 实现账户信息、交易记录和策略管理界面。

8. **Celery 集成**：
   - 配置 Celery 和 Redis。
   - 将任务调度与事件驱动机制集成到系统中。
   - 实现任务路由和高并发支持。

9. **测试与优化**：
   - 编写单元测试和集成测试。
   - 优化性能和扩展性。

---

### 安全设计

1. **身份认证**：
   - 使用 JWT（JSON Web Token）保护 API。
   - 本地开发使用静态密钥，未来公开访问可引入 OAuth2。

2. **数据保护**：
   - 使用 GitHub Secrets 管理敏感信息。
   - 环境变量加载（通过 `python-dotenv`）。

3. **网络安全**：
   - 配置 HTTPS（通过 Let’s Encrypt 自动签发证书）。
   - 启用 IP 限制和 API 调用限速。

---
