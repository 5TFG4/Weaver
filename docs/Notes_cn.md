### 项目背景和目标

**目标**：
构建一个 Python 自动交易机器人，部署在本地服务器上，支持 24/7 无间断运行，通过 Docker 容器化部署，具备以下核心功能：

- 与多个交易所 API 交互（当前优先支持 Alpaca）。
- 动态加载并执行策略模块。
- 记录交易历史，并支持基于本地数据的策略回测。
- 提供基于 React.js 的 Web 界面查看交易信息和记录。

**特点**：

- 模块化设计，支持扩展。
- 基于 RESTful API 的后端架构。
- 敏感信息通过 GitHub Secrets 管理，使用 GitHub Actions 实现 CI/CD。
- 以 Celery 为核心，结合 Redis，实现任务调度与事件驱动的结合。

---

### 模块划分

#### **1. GLaDOS (主控系统)**

- **职责**：
  - 协调模块间的通信，充当系统核心调度器。
  - 提供 RESTful API 接口供前端调用。
  - 调用 Veda 获取市场数据，触发 Marvin 执行策略。
  - 记录操作日志，监控系统运行状态。
- **设计特点**：
  - 通过 Celery 将任务分发给其他模块，实现异步处理。

#### **2. Veda (API接口数据处理模块)**

- **职责**：
  - 负责与交易所的所有交互，包括：
    - 拉取市场数据。
    - 获取账户信息。
    - 执行买卖订单。
  - 支持历史数据抓取，并保存到本地数据库。
  - 提供标准化接口，使扩展到其他交易所更容易。
- **设计特点**：
  - 使用 Celery 执行高并发任务。
  - 动态加载不同交易所实现模块。

#### **3. WallE (数据存储模块)**

- **职责**：
  - 管理 PostgreSQL 数据库，存储交易记录和市场数据。
  - 提供高效的数据读写接口供其他模块调用。
  - 保存策略配置和回测结果。
- **设计特点**：
  - 使用 SQLAlchemy 实现 ORM 层，支持复杂查询和事务处理。

#### **4. Marvin (策略执行模块)**

- **职责**：
  - 动态加载策略模块，根据市场数据生成交易指令。
  - 提供统一接口，确保所有策略模块的标准化调用。
  - 支持多策略组合和复杂判断逻辑。
  - 可直接调用 Veda 获取额外数据支持策略判断。
- **设计特点**：
  - 每个策略独立实现为 Python 模块，便于扩展和维护。
  - 返回标准化结果供 GLaDOS 调度使用。

#### **5. Greta (回测模块)**

- **职责**：
  - 使用本地历史数据运行策略模拟交易。
  - 返回回测结果，包括收益率、风险指标等关键数据。
  - 保存回测结果到数据库供后续分析。
- **设计特点**：
  - 支持灵活的回测配置，可对多种策略进行批量回测。

#### **6. Haro (Web UI 交互模块)**

- **职责**：
  - 提供基于 React.js 的前端界面，展示：
    - 账户信息。
    - 当前策略状态。
    - 历史交易记录。
    - 回测结果。
  - 支持用户通过界面管理策略和查看系统状态。
- **设计特点**：
  - 使用 Axios 调用 REST API 实现前后端通信。
  - 通过 WebSocket 支持实时数据更新。

---

### 通信与数据流设计

**模块间通信**：

- **核心架构**：
  - GLaDOS 作为系统核心，负责模块间的协调通信。
  - GLaDOS 与前端通过 FastAPI 提供 RESTful API 交互。
  - 模块间通过 Celery 和 Redis 实现异步任务分发和结果处理。

**数据流示例**：

1. GLaDOS 定时调用 Veda 拉取市场数据，结果通过 Celery 广播给 Marvin。
2. Marvin 根据策略逻辑生成交易指令，将指令返回给 GLaDOS。
3. GLaDOS 将交易指令传递给 Veda，Veda 调用交易所 API 执行交易。
4. 交易执行结果通过 Celery 回传给 GLaDOS，GLaDOS 记录日志并通知前端。

---

### 技术栈

- **后端**：FastAPI（RESTful API）
- **前端**：React.js
- **数据库**：PostgreSQL
- **ORM**：SQLAlchemy
- **任务调度**：Celery + Redis
- **容器化**：Docker + Docker Compose
- **CI/CD**：GitHub Actions
- **监控与日志**：Prometheus/Grafana + Python logging

---

### 目录结构

```plaintext
weaver/
├── src/                           
│   ├── api/                      # API 层（例如 FastAPI 路由和入口）
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI 应用入口
│   │   └── routes.py             # 路由定义
│   │
│   ├── modules/                  # 各个核心模块
│   │   ├── glados/               # 主控系统：调度任务、协调各模块
│   │   │   ├── __init__.py
│   │   │   ├── controller.py     # 核心业务逻辑
│   │   │   └── tasks.py          # Celery 相关任务
│   │   │
│   │   ├── veda/                 # API 交互模块：与交易所交互（如 Alpaca）
│   │   │   ├── __init__.py
│   │   │   ├── alpaca.py         # Alpaca 交易所集成
│   │   │   └── tasks.py          # 交易所异步任务
│   │   │
│   │   ├── walle/                # 数据存储模块
│   │   │   ├── __init__.py
│   │   │   ├── models.py         # 数据模型定义
│   │   │   └── database.py       # 数据库连接及操作
│   │   │
│   │   ├── marvin/               # 策略执行模块：加载并执行交易策略
│   │   │   ├── __init__.py
│   │   │   ├── base_strategy.py  # 策略基类
│   │   │   └── strategies/       # 具体策略实现
│   │   │
│   │   ├── greta/                # 回测模块
│   │   │   ├── __init__.py
│   │   │   └── backtest.py       # 回测逻辑
│   │   │
│   │   └── haro/                 # 前端交互模块（后端部分），为 React 提供 API 支持
│   │       ├── __init__.py
│   │       └── api.py            # API 封装
│   │
│   ├── lib/                      # 公共工具库、辅助函数等
│   │   ├── __init__.py
│   │   └── utils.py
│   │
│   ├── config/                   # 配置文件（如日志、数据库、Celery 的配置等）
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   └── celery_config.py
│   │
│   ├── tasks.py                  # 全局任务入口（如果需要统一管理部分任务）
│   └── main.py                   # 整体项目的入口（可用于启动 FastAPI 等）
│
├── tests/                        # 单元测试目录，对应各模块的测试
│   ├── glados/
│   ├── veda/
│   ├── walle/
│   ├── marvin/
│   ├── greta/
│   └── haro/
│
├── docker/                       # Docker 配置目录
│   ├── backend/                  # 后端 Docker 配置
│   │   ├── Dockerfile
│   │   ├── Dockerfile.dev
│   │   └── requirements.txt
│   ├── frontend/                 # 前端 Docker 配置
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
├── docs/                         # 项目文档
│   ├── Notes_en.md
│   └── Notes_cn.md               # 中文说明文档
│
└── .github/                      # GitHub Actions 工作流和 CI/CD 配置
    └── workflows/
```

