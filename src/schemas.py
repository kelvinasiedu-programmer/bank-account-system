"""Pydantic request/response schemas for the Bank API."""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class CreateAccountRequest(BaseModel):
    account_type: Literal["savings", "checking"] = Field(
        ..., description="Type of account to open."
    )
    account_holder: str = Field(..., min_length=1, max_length=80)
    initial_balance: float = Field(0.0, ge=0)


class AmountRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in dollars (must be positive).")


class TransactionOut(BaseModel):
    type: str
    amount: float
    balance_after: float
    timestamp: str
    note: str = ""


class AccountOut(BaseModel):
    account_id: str
    account_type: str
    account_holder: str
    balance: float
    history: List[TransactionOut] = []
    overdraft_limit: Optional[float] = None
    overdraft_fee: Optional[float] = None


class AccountSummary(BaseModel):
    account_id: str
    account_type: str
    account_holder: str
    balance: float


class StatsOut(BaseModel):
    total_accounts: int
    savings_accounts: int
    checking_accounts: int
    total_assets: float


class MessageOut(BaseModel):
    message: str


class HealthOut(BaseModel):
    status: str
    version: str
