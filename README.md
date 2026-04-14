---
title: Bank Account System
emoji: 🏦
colorFrom: purple
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Bank Account System

Production-grade OOP banking API modeling savings and checking accounts with tiered interest rates and overdraft logic. Built around a clean class hierarchy (`BankAccount` → `SavingsAccount`, `CheckingAccount`) exposed via a FastAPI REST service with a transaction-ledger UI.

[![CI](https://github.com/kelvinasiedu-programmer/bank-account-system/actions/workflows/ci.yml/badge.svg)](https://github.com/kelvinasiedu-programmer/bank-account-system/actions/workflows/ci.yml)

## Architecture

```
Client ──▶ FastAPI REST API ──▶ Bank Service ──▶ Account Domain
                                     │                │
                                     ▼                ▼
                              JSON Persistence   BankAccount
                                (atomic write)        ├── SavingsAccount  (tiered interest)
                                                      └── CheckingAccount (overdraft + fee)
```

**Domain model:**

- `BankAccount` — base class: deposit, withdraw, immutable transaction history
- `SavingsAccount` — applies tiered interest (**3% ≤ $1K · 5% ≤ $5K · 7% > $5K**)
- `CheckingAccount` — overrides `withdraw()` to allow overdraft up to `-$500` and assess a `$25` fee when balance goes negative
- `Transaction` — frozen dataclass; every mutation appends an immutable ledger entry (`open`, `deposit`, `withdrawal`, `interest`, `overdraft_fee`)

## Features

- **Clean OOP hierarchy** — inheritance, encapsulation, polymorphism with a base `BankAccount` and two specialized subclasses
- **Tiered interest engine** — balance-aware rate selection (3 / 5 / 7%) configurable via environment
- **Overdraft logic** — configurable limit and fee with balance validation
- **Immutable transaction ledger** — every deposit, withdrawal, interest accrual, and fee is logged with a timestamp
- **REST API** — FastAPI with auto-generated OpenAPI/Swagger docs
- **Persistent storage** — atomic JSON writes survive container restarts
- **Thread-safe** — `RLock`-guarded operations for concurrent access
- **Rate limiting** — sliding-window middleware
- **Beautiful dark UI** — dashboard with account list, transaction history, and live stats
- **Docker** — multi-stage build with health checks
- **CI/CD** — GitHub Actions: lint, test (Python 3.10–3.12), Docker build
- **Type-safe config** — Pydantic Settings with `.env` support

## Quick Start

### Prerequisites

- Python 3.10+

### Install & Run

```bash
git clone https://github.com/kelvinasiedu-programmer/bank-account-system.git
cd bank-account-system

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env

uvicorn src.main:app --reload
```

Dashboard: `http://localhost:8000` · Swagger docs: `http://localhost:8000/docs`

### Docker

```bash
cp .env.example .env
docker compose up -d
```

## API Endpoints

| Method   | Endpoint                                       | Description                       |
| -------- | ---------------------------------------------- | --------------------------------- |
| `POST`   | `/api/v1/accounts`                             | Open a new account                |
| `GET`    | `/api/v1/accounts`                             | List all accounts                 |
| `GET`    | `/api/v1/accounts/{id}`                        | Get account details + history     |
| `DELETE` | `/api/v1/accounts/{id}`                        | Close an account                  |
| `POST`   | `/api/v1/accounts/{id}/deposit`                | Deposit funds                     |
| `POST`   | `/api/v1/accounts/{id}/withdraw`               | Withdraw funds                    |
| `POST`   | `/api/v1/accounts/{id}/apply-interest`         | Apply tiered interest (savings)   |
| `DELETE` | `/api/v1/accounts`                             | Clear all accounts                |
| `GET`    | `/api/v1/stats`                                | Aggregate bank stats              |
| `GET`    | `/api/v1/health`                               | Health check                      |

### Example

```bash
# Open a savings account
curl -X POST http://localhost:8000/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{"account_type":"savings","account_holder":"Jane Doe","initial_balance":1500}'

# Apply interest (will credit 5% → +$75)
curl -X POST http://localhost:8000/api/v1/accounts/{id}/apply-interest
```

### Response Format

```json
{
  "account_id": "f3c...",
  "account_type": "savings",
  "account_holder": "Jane Doe",
  "balance": 1575.00,
  "history": [
    { "type": "open",     "amount": 1500, "balance_after": 1500, "timestamp": "..." },
    { "type": "interest", "amount": 75,   "balance_after": 1575, "note": "Tiered interest applied @ 5.0%" }
  ]
}
```

## Configuration

All settings are configurable via environment variables or `.env`:

| Variable            | Default              | Description                         |
| ------------------- | -------------------- | ----------------------------------- |
| `STORAGE_PATH`      | `data/accounts.json` | JSON persistence path               |
| `TIER_1_LIMIT`      | `1000.0`             | Upper bound of 3% tier              |
| `TIER_1_RATE`       | `0.03`               | Interest rate for tier 1            |
| `TIER_2_LIMIT`      | `5000.0`             | Upper bound of 5% tier              |
| `TIER_2_RATE`       | `0.05`               | Interest rate for tier 2            |
| `TIER_3_RATE`       | `0.07`               | Interest rate for tier 3 (> $5K)    |
| `OVERDRAFT_LIMIT`   | `-500.0`             | Minimum allowed checking balance    |
| `OVERDRAFT_FEE`     | `25.0`               | Fee assessed on negative balance    |

## Testing

```bash
pip install -r requirements-dev.txt
make test
```

Covers domain invariants (tier boundaries, overdraft edge cases), persistence round-trips, and end-to-end API flows.

## Project Structure

```
bank-account-system/
├── src/
│   ├── main.py           # FastAPI app, routes, rate limiter, static UI mount
│   ├── config.py         # Pydantic Settings
│   ├── accounts.py       # BankAccount / SavingsAccount / CheckingAccount
│   ├── bank.py           # Registry, persistence, thread-safe service layer
│   ├── schemas.py        # Pydantic request/response models
│   └── static/index.html # Dark-theme dashboard
├── tests/
│   ├── conftest.py
│   ├── test_accounts.py  # Domain invariants + tier boundaries
│   ├── test_bank.py      # Persistence & service layer
│   └── test_api.py       # End-to-end FastAPI TestClient
├── .github/workflows/ci.yml
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
├── requirements.txt
└── requirements-dev.txt
```

## Tech Stack

| Component         | Technology                   |
| ----------------- | ---------------------------- |
| API Framework     | FastAPI                      |
| Validation        | Pydantic v2                  |
| Config            | Pydantic Settings            |
| Persistence       | Atomic JSON writes           |
| Concurrency       | threading.RLock              |
| Containerization  | Docker (multi-stage)         |
| CI/CD             | GitHub Actions               |
| Testing           | pytest + coverage + httpx    |

## License

MIT
