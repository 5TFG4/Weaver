weaver/
│
├── src/                    # Source code directory
│   ├── WallE/              # Data storage module
│   │   ├── __init__.py
│   │   ├── data_storage.py     # Data storage functions
│   │   └── data_retrieval.py   # Data retrieval functions
│   │
│   ├── Veda/               # API interface data processing module
│   │   ├── __init__.py
│   │   ├── api_handler.py      # API handling functions
│   │   └── data_uploader.py    # Data uploading functions
│   │
│   ├── GLaDOS/             # Main control system
│   │   ├── __init__.py
│   │   ├── control_system.py   # Control system functions
│   │   └── integration_manager.py  # Integration management
│   │
│   ├── Marvin/             # Strategy storage and execution module
│   │   ├── __init__.py
│   │   ├── strategy_manager.py # Strategy management
│   │   └── strategies/         # Folder for specific strategies
│   │       ├── __init__.py
│   │       ├── strategy1.py    # Strategy 1
│   │       └── strategy2.py    # Strategy 2
│   │
│   ├── Greta/              # Backtesting module
│   │   ├── __init__.py
│   │   ├── backtesting.py      # Backtesting functions
│   │   └── test_suite.py       # Test suite
│   │
│   └── Haro/               # Web UI interaction module
│       ├── __init__.py
│       ├── web_interface.py    # Web interface functions
│       └── templates/          # Folder for HTML templates
│           ├── index.html
│           └── dashboard.html
│
├── tests/                  # Unit tests directory
│   ├── test_WallE.py
│   ├── test_Veda.py
│   ├── test_GLaDOS.py
│   ├── test_Marvin.py
│   ├── test_Greta.py
│   └── test_Haro.py
│
├── .github/                # GitHub configuration directory
│   └── workflows/          # GitHub Actions workflows directory
│       └── ci_cd.yml       # CI/CD workflow configuration file
│
├── .devcontainer/
│   └── devcontainer.json
│
├── Dockerfile              # Docker configuration file
├── docker-compose.dev.yml  # Docker Compose configuration file for dev env
├── docker-compose.pord.yml # Docker Compose configuration file for prod env
├── .env                    # Environment configuration file (not to be version controlled)
├── .dockerignore           # Docker ignore file
├── .gitignore              # Git ignore file
├── README.md               # Project documentation
├── LICENSE                 # MIT License file
└── requirements.txt        # List of Python dependencies

