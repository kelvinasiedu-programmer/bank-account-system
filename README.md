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

A small FastAPI service modelling savings and checking accounts with tiered
interest and overdraft rules, plus a dashboard UI for inspecting balances and
transaction history.

[![CI](https://github.com/kelvinasiedu-programmer/bank-account-system/actions/workflows/ci.yml/badge.svg)](https://github.com/kelvinasiedu-programmer/bank-account-system/actions/workflows/ci.yml)

Built as a portfolio project to practise OOP design, REST API work, and
containerised deployment end-to-end. Data lives in a JSON file, not a real
database, so it is not intended for production use.

## Domain model

- `BankAccount` — base class with deposit, withdraw, and a read-only transaction list.
- `SavingsAccount` — applies tiered interest: 3% up to $1K, 5% up to $5K, 7% above.
- `CheckingAccount` — allows overdraft down to -$500 and charges a $25 fee when the balance goes negative.
- `Transaction` — a frozen dataclass; every mutation appends one entry (`open`, `deposit`, `withdrawal`, `interest`, `overdraft_fee`).

Tier limits, rates, overdraft limit, and fee are all configurable via `.env`.

## Run it

```bash
git clone https://github.com/kelvinasiedu-programmer/bank-account-system.git
cd bank-account-system

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

uvicorn src.main:app --reload
```

Dashboard at `http://localhost:8000`, Swagger at `/docs`.

With Docker: `docker compose up -d`.

## API

| Method   | Endpoint                                       |
| -------- | ---------------------------------------------- |
| `POST`   | `/api/v1/accounts`                             |
| `GET`    | `/api/v1/accounts`                             |
| `GET`    | `/api/v1/accounts/{id}`                        |
| `DELETE` | `/api/v1/accounts/{id}`                        |
| `POST`   | `/api/v1/accounts/{id}/deposit`                |
| `POST`   | `/api/v1/accounts/{id}/withdraw`               |
| `POST`   | `/api/v1/accounts/{id}/apply-interest`         |
| `GET`    | `/api/v1/stats`                                |
| `GET`    | `/api/v1/health`                               |

Example:

```bash
curl -X POST http://localhost:8000/api/v1/accounts \
  -H "Content-Type: application/json" \
  -d '{"account_type":"savings","account_holder":"Jane Doe","initial_balance":1500}'

curl -X POST http://localhost:8000/api/v1/accounts/{id}/apply-interest
# returns the account with a new interest transaction appended
```

## Config

Set via environment or `.env`:

| Variable            | Default              |
| ------------------- | -------------------- |
| `STORAGE_PATH`      | `data/accounts.json` |
| `TIER_1_LIMIT`      | `1000.0`             |
| `TIER_1_RATE`       | `0.03`               |
| `TIER_2_LIMIT`      | `5000.0`             |
| `TIER_2_RATE`       | `0.05`               |
| `TIER_3_RATE`       | `0.07`               |
| `OVERDRAFT_LIMIT`   | `-500.0`             |
| `OVERDRAFT_FEE`     | `25.0`               |

## Tests

```bash
pip install -r requirements-dev.txt
make test
```

Tests cover the tier boundary cases, overdraft edges, persistence round-trips,
and the FastAPI endpoints end-to-end.

## Stack

FastAPI, Pydantic v2 / Pydantic Settings, `threading.RLock` for concurrent
writes, atomic JSON persistence, Docker multi-stage build, pytest + coverage,
GitHub Actions for lint and test on Python 3.10–3.12.

## Known limitations

- JSON file persistence is not safe across processes; it is fine for a single
  container but you would swap it for Postgres before anything real.
- The sliding-window rate limiter is in-memory, so it resets on restart.
- No auth — the API is open by design, since this is a portfolio demo.

## License

MIT
