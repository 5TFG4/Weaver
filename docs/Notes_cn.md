### 项目背景和目标

**目标**：
构建一个 Python 自动交易机器人，部署在本地服务器上，支持 24/7 无间断运行，通过 Docker 容器化部署，具备以下核心功能：

- 与多个交易所 API 交互（当前优先支持 Alpaca）。
- 动态加载并执行策略模块。
- 记录交易历史，并支持基于本地数据的策略回测。
- 提供基于 React.js 的 Web 界面查看交易信息和记录。

**特点**：

- **事件驱动架构**：通过内部事件总线实现模块间自主通信。
- 模块化设计，支持扩展。
- 基于 RESTful API 的后端架构。
- 敏感信息通过 GitHub Secrets 管理，使用 GitHub Actions 实现 CI/CD。

---

### 事件驱动架构设计

**核心原则**：模块通过事件进行自主通信，最小化中央协调。

**GLaDOS 角色**：最小化编排器，仅处理系统初始化、健康监控和关闭协调。

**模块自主性**：每个模块管理自己的生命周期，直接通过事件与其他模块通信。

**通信流程示例**：
1. GLaDOS 发布 `system_init` → 所有模块开始初始化
2. 模块完成启动并发布 `module_ready` → GLaDOS 收集就绪状态
3. GLaDOS 在所有模块就绪时发布 `system_ready` → 开始操作
4. Marvin 发布 `strategy_load_request` → 策略初始化
5. 策略发布 `trading_platform_request` → Veda 响应
6. Veda 发布 `platform_available` → 策略接收
7. 策略发布 `market_data_request` → WallE/Veda 响应
8. 持续自主通信...
9. GLaDOS 发布 `system_terminate` → 有序关闭序列开始

---

### 模块概述

#### **1. GLaDOS (主应用程序类)**

- **职责**：
  - **系统初始化**：发布 `system_init` 事件并协调模块启动
  - **健康监控**：收集模块健康状态并协调系统就绪状态
  - **模块协调**：等待所有模块报告就绪后开始操作
  - **关闭协调**：编排有序关闭序列以防止问题
  - **应急响应**：处理系统错误和紧急关闭
- **设计特点**：
  - 操作前模块健康检查协调
  - 有序关闭序列（策略 → 数据 → APIs → 核心）
  - 紧急干预能力
- **事件通信**：
  - 发布：`system_init`, `system_ready`, `system_terminate`, `emergency_shutdown`
  - 监听：`module_ready`, `module_health`, `system_error`, `module_shutdown_request`

#### **2. Veda (交易所API管理器)**

- **职责**：
  - **API集成**：处理与交易平台/交易所的所有交互
  - **市场数据**：提供实时和历史市场数据
  - **订单执行**：通过交易所API执行买卖订单
  - **账户管理**：获取账户信息和投资组合状态
  - **平台发现**：响应平台可用性请求
- **事件通信**：
  - 监听：`trading_platform_request`, `market_data_request`, `order_request`
  - 发布：`platform_available`, `market_data_update`, `order_filled`
- **设计特点**：
  - 通过插件架构管理多个交易所连接器
  - 基于事件请求的自主操作

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

### 系统协调模式

#### **模块健康检查系统**

**启动协调**：
1. GLaDOS 发布 `system_init`
2. 每个模块初始化并发布带状态的 `module_ready`
3. GLaDOS 等待所有模块报告就绪
4. GLaDOS 发布 `system_ready` → 交易操作开始
5. 通过 `module_health` 事件进行定期健康检查

**健康检查事件**：
- `module_ready`: 模块初始化完成并准备操作
- `module_health`: 定期健康状态（健康/降级/错误）
- `system_ready`: 所有模块就绪，可以开始交易操作
- `system_status_check`: 请求所有模块报告当前健康状态

#### **有序关闭序列**

**关闭优先级顺序**：
1. **策略** (Marvin) - 停止生成新信号，完成待处理操作
2. **UI后端** (Haro) - 关闭WebSocket连接，停止API端点
3. **交易所API** (Veda) - 取消待处理订单，关闭API连接
4. **数据库** (WallE) - 刷新待写入数据，关闭数据库连接
5. **核心系统** - 事件总线、日志、应用程序关闭

**关闭事件**：
- `system_terminate`: 开始有序关闭序列
- `module_shutdown_complete`: 模块已完成关闭
- `emergency_shutdown`: 需要立即关闭
- `shutdown_timeout`: 模块关闭超时

---

### 事件总线通信模式

#### **系统事件（GLaDOS管理）**：
- `system_init`: 系统启动通知
- `system_ready`: 所有模块就绪，可以开始操作
- `system_terminate`: 开始有序关闭序列
- `system_status_check`: 请求系统范围健康检查
- `emergency_shutdown`: 需要立即关闭
- `module_ready`: 模块初始化完成
- `module_health`: 模块健康状态报告
- `module_shutdown_complete`: 模块关闭确认
- `system_error`: 需要GLaDOS干预的关键错误

#### **模块间事件**：

**策略与交易**：
- `strategy_load_request`: 请求加载策略
- `trading_platform_request`: 请求可用交易平台
- `platform_available`: 响应平台信息
- `market_data_request`: 请求市场数据
- `market_data_update`: 市场数据广播
- `trade_signal`: 生成交易信号
- `order_request`: 请求执行订单
- `order_filled`: 订单执行确认

**数据管理**：
- `data_store_request`: 请求存储数据
- `data_query_request`: 从数据库请求数据
- `data_stored`: 数据存储确认
- `data_response`: 数据查询响应
- `historical_data_request`: 请求历史数据
- `historical_data_response`: 历史数据交付

**回测**：
- `backtest_request`: 请求回测
- `backtest_complete`: 回测完成
- `backtest_results`: 回测结果

**UI通信**：
- `ui_data_request`: UI请求数据
- `ui_update`: 用新数据更新UI
- `user_action`: 来自前端的用户操作

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

