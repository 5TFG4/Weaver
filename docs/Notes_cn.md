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
- 基于内部事件总线的模块间通信系统。

---

### 模块划分

#### **1. GLaDOS (主应用程序类)**

- **职责**：
  - **主要角色**：管理整个交易系统生命周期的主应用程序类。
  - **系统编排**：协调启动、关闭和模块初始化。
  - **模块协调**：通过事件总线管理所有交易模块之间的通信。
  - **应用管理**：处理系统健康监控、错误恢复和优雅关闭。
  - **事件协调**：处理关键系统事件（市场数据、交易信号、订单成交）。
  - **进程管理**：维护主应用程序循环并确保系统稳定性。
- **设计特点**：
  - 包含主应用程序实例并管理核心系统基础设施。
  - 实现适当的信号处理以实现优雅关闭。
  - 协调模块启动顺序和依赖管理。
  - 提供集中的系统监控和健康检查。

#### **2. Veda (API接口数据处理模块)**

- **职责**：
  - 负责与交易所的所有交互，包括：
    - 拉取市场数据。
    - 获取账户信息。
    - 执行买卖订单。
  - 支持历史数据抓取，并保存到本地数据库。
  - 提供标准化接口，使扩展到其他交易所更容易。
- **设计特点**：
  - 通过插件架构管理多个交易所连接器。
  - 直接 API 调用，支持异步操作以实现高性能数据处理。

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

#### **6. Haro (UI后端模块)**

- **职责**：
  - 为前端通信提供专门的FastAPI路由。
  - 处理WebSocket连接，向UI提供实时数据更新。
  - 将其他模块的数据格式化供前端使用。
  - 管理UI特定关注点（用户会话、UI状态、图表数据格式化）。
- **设计特点**：
  - 专用UI后端 - GLaDOS处理核心业务逻辑，Haro专注于UI需求。
  - WebSocket支持无需轮询的实时更新。
  - 清晰分离：frontend/ 目录包含React应用，Haro提供其后端API。

---

### 通信与数据流设计

**模块间通信**：

- **核心架构**：
  - GLaDOS 作为主应用程序类，管理系统生命周期和模块协调。
  - GLaDOS 使用 core.Application 类提供系统基础设施（事件总线、启动/关闭）。
  - Haro 为前端通信提供 RESTful API 和 WebSocket 连接。
  - 模块间通过内部事件总线实现实时数据流和命令执行。

**数据流示例**：

1. GLaDOS 在系统启动期间初始化所有模块并启动事件总线。
2. Veda 定期获取市场数据并向事件总线发布 'market_data' 事件。
3. Marvin 订阅 'market_data' 事件，处理数据并发布 'trade_signal' 事件。
4. GLaDOS 接收 'trade_signal' 事件并与 Veda 协调执行订单。
5. 订单执行结果作为 'order_filled' 事件发布，由 WallE 记录，并通过 Haro 的 WebSocket 发送到前端。
3. GLaDOS 接收交易信号并将指令转发给 Veda 执行。
4. 执行结果发布到事件总线，由 GLaDOS 记录日志并通过 WebSocket 发送给前端。

---

### 技术栈

- **后端**：FastAPI（RESTful API）
- **前端**：React.js
- **数据库**：PostgreSQL
- **ORM**：SQLAlchemy
- **模块通信**：内部事件总线
- **实时更新**：WebSockets
- **容器化**：Docker + Docker Compose
- **CI/CD**：GitHub Actions
- **监控与日志**：Prometheus/Grafana + Python logging

---

### 目录结构

```plaintext
weaver/
├── backend/                      # 后端Python代码
│   ├── src/                      # 主应用代码
│   │   ├── core/                 # 核心系统基础设施
│   │   │   ├── __init__.py
│   │   │   ├── event_bus.py      # 发布: 'market_data', 'trade_signal', 'order_filled'
│   │   │   ├── application.py    # GLaDOS用于系统管理的核心应用程序类
│   │   │   ├── logger.py         # 日志配置和工具
│   │   │   └── constants.py      # 应用程序范围常量（ALPACA等）
│   │   │
│   │   ├── modules/              # 所有主要业务模块（统一处理）
│   │   │   ├── glados.py         # 主应用程序类（系统编排器，模块协调器）
│   │   │   ├── veda.py           # 交易所管理器（将订单路由到正确平台）
│   │   │   ├── walle.py          # 数据库操作（保存交易，市场数据）
│   │   │   ├── marvin.py         # 策略执行器（加载和运行策略）
│   │   │   ├── greta.py          # 回测引擎（模拟历史交易）
│   │   │   └── haro.py           # UI后端（前端的FastAPI路由，WebSocket实时更新）
│   │   │
│   │   ├── lib/                  # 共享工具和助手
│   │   │   ├── __init__.py
│   │   │   └── utils.py          # 通用工具函数（日期解析，验证等）
│   │   │
│   │   ├── connectors/           # 交易所实现（当有多个时）
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # 通用接口: get_data(), place_order()
│   │   │   ├── alpaca.py         # Alpaca API 实现
│   │   │   ├── binance.py        # Binance API 实现（未来）
│   │   │   └── coinbase.py       # Coinbase Pro API 实现（未来）
│   │   │
│   │   ├── strategies/           # 交易策略（当有多个时）
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # 包含通用方法的基础策略类
│   │   │   ├── simple_ma.py      # 移动平均策略（包含MA计算）
│   │   │   ├── rsi_strategy.py   # RSI策略（包含RSI计算）
│   │   │   ├── bollinger_bands.py # 布林带策略（包含布林带计算）
│   │   │   ├── portfolio_risk.py # 投资组合级别风险管理
│   │   │   └── buy_and_hold.py   # 简单买入持有策略
│   │   │
│   │   ├── models/               # 数据库模型（当有多个时）
│   │   │   ├── __init__.py
│   │   │   ├── trade.py          # 交易表: symbol, qty, price, timestamp
│   │   │   ├── market_data.py    # 市场数据: symbol, ohlcv, timestamp
│   │   │   ├── strategy_run.py   # 策略执行记录
│   │   │   └── portfolio.py      # 投资组合持仓和余额
│   │   │
│   │   └── weaver.py             # 入口点: python -m src.weaver
│
├── frontend/                     # React.js网络界面
│   ├── src/
│   │   ├── components/           # React组件（图表，表格，表单）
│   │   ├── pages/                # React页面（仪表板，策略，交易）
│   │   ├── hooks/                # 自定义React钩子
│   │   ├── services/             # 对后端的API调用
│   │   └── App.js                # 主React应用组件
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   ├── package.json              # NPM依赖和脚本（React必需）
│   └── package-lock.json         # 确切的依赖版本（NPM必需）
│
├── tests/                        # 单元测试，镜像backend/src结构
│   ├── test_modules/             # modules/的测试
│   ├── test_strategies/          # strategies/的测试
│   ├── test_connectors/          # connectors/的测试
│   ├── test_models/              # models/的测试
│   └── conftest.py               # Pytest配置
│
├── docker/                       # 容器配置和部署
│   ├── backend/                  # 后端容器设置
│   │   ├── Dockerfile            # 生产后端容器
│   │   └── Dockerfile.dev        # 开发后端容器
│   │
│   ├── frontend/                 # 前端容器设置
│   │   ├── Dockerfile            # 生产前端容器（nginx）
│   │   └── Dockerfile.dev        # 开发前端容器
│   │
│   ├── docker-compose.yml        # 生产部署
│   ├── docker-compose.dev.yml    # 开发环境
│   ├── example.env               # 示例生产环境变量
│   ├── example.env.dev           # 示例开发环境变量
│   ├── .env                      # 实际生产环境变量（gitignored）
│   ├── .env.dev                  # 实际开发环境变量（gitignored）
│   └── .dockerignore             # 从docker构建中排除的文件
│
├── docs/                         # 文档
│   ├── Notes_en.md               # 英文架构文档
│   ├── Notes_cn.md               # 中文架构文档
│   └── API.md                    # API端点文档
│
├── logs/                         # 应用日志（运行时创建）
│   ├── app.log                   # 通用应用日志
│   └── main.log                  # 主进程日志
│
├── .github/                      # CI/CD工作流和问题模板
│   ├── workflows/                # GitHub Actions工作流
│   │   ├── ci.yml                # 持续集成
│   │   └── deploy.yml            # 部署管道
│   ├── ISSUE_TEMPLATE/           # 问题模板
│   │   ├── BUG-REPORT.yml
│   │   └── FEATURE-REQUEST.yml
│   └── PULL_REQUEST_TEMPLATE.md
│
├── .devcontainer/                # VS Code开发容器
│   └── devcontainer.json         # 开发容器配置
│
├── weaver.py                     # 替代入口点（向后兼容）
├── README.md                     # 项目概述和设置说明
└── .gitignore                    # Git忽略模式
```

