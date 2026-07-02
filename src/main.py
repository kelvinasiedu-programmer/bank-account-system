"""FastAPI application entrypoint for the Bank Account System."""

from __future__ import annotations

import secrets
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src import __version__
from src.bank import AccountNotFoundError, Bank
from src.config import settings
from src.schemas import (
    AccountOut,
    AccountSummary,
    AmountRequest,
    CreateAccountRequest,
    HealthOut,
    MessageOut,
    StatsOut,
)

# ---------- app ----------
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=settings.api_description,
)

# Reflecting an arbitrary origin *with* credentials defeats the same-origin
# policy, so credentials are only enabled when the origins are explicit.
_allow_credentials = "*" not in settings.cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# ---------- auth ----------
def require_admin(x_api_key: str | None = Header(default=None)) -> None:
    """Guard destructive endpoints with a constant-time API-key check."""
    expected = settings.admin_api_key
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin endpoints are not configured.",
        )
    if not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


# ---------- rate limiting ----------
_request_log: dict[str, deque[float]] = defaultdict(deque)
# Above this many tracked clients, sweep out IPs whose window has fully expired
# so a stream of unique source IPs cannot grow the map without bound.
_RATE_LOG_SWEEP_AT = 10_000


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Sliding-window rate limiter keyed on client IP."""
    client = request.client.host if request.client else "anon"
    now = time.time()
    window = settings.rate_limit_window_seconds
    cutoff = now - window

    if len(_request_log) > _RATE_LOG_SWEEP_AT:
        for ip in [k for k, v in _request_log.items() if not v or v[-1] <= cutoff]:
            del _request_log[ip]

    log = _request_log[client]
    while log and log[0] <= cutoff:
        log.popleft()
    if len(log) >= settings.rate_limit_requests:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Too many requests. Please slow down."},
        )
    log.append(now)
    return await call_next(request)


# ---------- bank dependency ----------
_bank = Bank(
    storage_path=settings.storage_path,
    seed_if_empty=settings.seed_demo_data,
)


def get_bank() -> Bank:
    return _bank


# ---------- routes ----------
API = "/api/v1"


@app.get(f"{API}/health", response_model=HealthOut, tags=["system"])
def health() -> HealthOut:
    return HealthOut(status="ok", version=__version__)


@app.post(
    f"{API}/accounts",
    response_model=AccountOut,
    status_code=status.HTTP_201_CREATED,
    tags=["accounts"],
)
def create_account(payload: CreateAccountRequest, bank: Bank = Depends(get_bank)) -> AccountOut:
    try:
        acc = bank.create_account(
            account_type=payload.account_type,
            account_holder=payload.account_holder,
            initial_balance=payload.initial_balance,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return AccountOut(**acc.to_dict())


@app.get(f"{API}/accounts", response_model=list[AccountSummary], tags=["accounts"])
def list_accounts(bank: Bank = Depends(get_bank)) -> list[AccountSummary]:
    return [
        AccountSummary(
            account_id=a.account_id,
            account_type=a.account_type,
            account_holder=a.account_holder,
            balance=round(a.balance, 2),
        )
        for a in bank.list_accounts()
    ]


@app.get(f"{API}/accounts/{{account_id}}", response_model=AccountOut, tags=["accounts"])
def get_account(account_id: str, bank: Bank = Depends(get_bank)) -> AccountOut:
    try:
        acc = bank.get(account_id)
    except AccountNotFoundError as e:
        raise HTTPException(status_code=404, detail="Account not found.") from e
    return AccountOut(**acc.to_dict())


@app.delete(
    f"{API}/accounts/{{account_id}}",
    response_model=MessageOut,
    tags=["accounts"],
    dependencies=[Depends(require_admin)],
)
def delete_account(account_id: str, bank: Bank = Depends(get_bank)) -> MessageOut:
    try:
        bank.delete(account_id)
    except AccountNotFoundError as e:
        raise HTTPException(status_code=404, detail="Account not found.") from e
    return MessageOut(message=f"Account {account_id} closed.")


@app.post(
    f"{API}/accounts/{{account_id}}/deposit",
    response_model=AccountOut,
    tags=["transactions"],
)
def deposit(account_id: str, body: AmountRequest, bank: Bank = Depends(get_bank)) -> AccountOut:
    try:
        acc = bank.deposit(account_id, body.amount)
    except AccountNotFoundError as e:
        raise HTTPException(status_code=404, detail="Account not found.") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return AccountOut(**acc.to_dict())


@app.post(
    f"{API}/accounts/{{account_id}}/withdraw",
    response_model=AccountOut,
    tags=["transactions"],
)
def withdraw(account_id: str, body: AmountRequest, bank: Bank = Depends(get_bank)) -> AccountOut:
    try:
        acc = bank.withdraw(account_id, body.amount)
    except AccountNotFoundError as e:
        raise HTTPException(status_code=404, detail="Account not found.") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return AccountOut(**acc.to_dict())


@app.post(
    f"{API}/accounts/{{account_id}}/apply-interest",
    response_model=AccountOut,
    tags=["transactions"],
)
def apply_interest(account_id: str, bank: Bank = Depends(get_bank)) -> AccountOut:
    try:
        acc = bank.apply_interest(account_id)
    except AccountNotFoundError as e:
        raise HTTPException(status_code=404, detail="Account not found.") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return AccountOut(**acc.to_dict())


@app.get(f"{API}/stats", response_model=StatsOut, tags=["system"])
def stats(bank: Bank = Depends(get_bank)) -> StatsOut:
    return StatsOut(**bank.stats())


@app.delete(
    f"{API}/accounts",
    response_model=MessageOut,
    tags=["accounts"],
    dependencies=[Depends(require_admin)],
)
def clear_all(bank: Bank = Depends(get_bank)) -> MessageOut:
    bank.clear()
    return MessageOut(message="All accounts cleared.")


# ---------- static UI ----------
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(str(STATIC_DIR / "index.html"))
