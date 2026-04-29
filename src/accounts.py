"""
Core banking domain model.

Defines an OOP hierarchy for bank accounts with tiered interest savings,
and overdraft-enabled checking, plus a transaction audit log.

Money is stored internally as `Decimal` quantized to two decimals to avoid
floating-point drift on accumulating transactions. The API and JSON
persistence layers serialize back to `float` for compatibility.

Classes:
    Transaction      immutable record of a single account event
    BankAccount      base class with deposit/withdraw/balance
    SavingsAccount   applies tiered interest (3%, 5%, 7%)
    CheckingAccount  allows overdraft up to a configurable limit with a fee
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from src.config import settings

TransactionType = Literal["deposit", "withdrawal", "interest", "overdraft_fee", "open"]

_CENTS = Decimal("0.01")


def _money(amount) -> Decimal:
    """Coerce any numeric input to a 2-decimal Decimal for monetary math."""
    d = amount if isinstance(amount, Decimal) else Decimal(str(amount))
    return d.quantize(_CENTS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Transaction:
    """Immutable ledger entry for a single account event."""

    type: TransactionType
    amount: Decimal
    balance_after: Decimal
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    note: str = ""


class BankAccount:
    """
    Base class representing a generic bank account.

    Attributes:
        account_id (str):       Unique identifier (UUID4).
        account_holder (str):   Name of the account holder.
        balance (Decimal):      Current balance, quantized to 2 dp.
        history (list):         Ordered list of Transaction entries.
    """

    account_type: str = "bank"

    def __init__(
        self,
        account_holder: str,
        initial_balance=0.0,
        account_id: str | None = None,
    ) -> None:
        if not account_holder or not account_holder.strip():
            raise ValueError("Account holder name is required.")
        opening = _money(initial_balance)
        if opening < 0:
            raise ValueError("Initial balance cannot be negative.")

        self.account_id: str = account_id or str(uuid.uuid4())
        self.account_holder: str = account_holder.strip()
        self.balance: Decimal = opening
        self.history: list[Transaction] = [
            Transaction(
                type="open",
                amount=opening,
                balance_after=opening,
                note=f"Account opened ({self.account_type})",
            )
        ]

    # ---------- core operations ----------
    def deposit(self, amount) -> Transaction:
        """Deposit a positive amount into the account."""
        if amount is None:
            raise ValueError("Deposit amount must be positive.")
        amt = _money(amount)
        if amt <= 0:
            raise ValueError("Deposit amount must be positive.")
        self.balance = _money(self.balance + amt)
        tx = Transaction(type="deposit", amount=amt, balance_after=self.balance)
        self.history.append(tx)
        return tx

    def withdraw(self, amount) -> Transaction:
        """Withdraw an amount if sufficient funds exist."""
        if amount is None:
            raise ValueError("Withdrawal amount must be positive.")
        amt = _money(amount)
        if amt <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        if self.balance < amt:
            raise ValueError("Insufficient funds.")
        self.balance = _money(self.balance - amt)
        tx = Transaction(type="withdrawal", amount=amt, balance_after=self.balance)
        self.history.append(tx)
        return tx

    def get_balance(self) -> Decimal:
        """Return the current balance."""
        return self.balance

    # ---------- serialization ----------
    def to_dict(self) -> dict:
        """Serialize to a JSON-safe dict (Decimals coerced to floats)."""
        return {
            "account_id": self.account_id,
            "account_type": self.account_type,
            "account_holder": self.account_holder,
            "balance": float(self.balance),
            "history": [
                {
                    "type": tx.type,
                    "amount": float(tx.amount),
                    "balance_after": float(tx.balance_after),
                    "timestamp": tx.timestamp,
                    "note": tx.note,
                }
                for tx in self.history
            ],
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.account_holder}): Balance = ${self.balance:.2f}"

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} id={self.account_id[:8]} "
            f"holder={self.account_holder!r} balance={self.balance:.2f}>"
        )


class SavingsAccount(BankAccount):
    """
    Savings account with tiered interest rates.

    Tiers (configurable via settings):
        balance <= 1000   -> 3%
        balance <= 5000   -> 5%
        balance >  5000   -> 7%
    """

    account_type: str = "savings"

    def _current_rate(self) -> Decimal:
        bal = self.balance
        if bal <= _money(settings.tier_1_limit):
            return Decimal(str(settings.tier_1_rate))
        if bal <= _money(settings.tier_2_limit):
            return Decimal(str(settings.tier_2_rate))
        return Decimal(str(settings.tier_3_rate))

    def apply_interest(self) -> Transaction:
        """Compute tiered interest and credit it to the account."""
        rate = self._current_rate()
        interest = _money(self.balance * rate)
        self.balance = _money(self.balance + interest)
        tx = Transaction(
            type="interest",
            amount=interest,
            balance_after=self.balance,
            note=f"Tiered interest applied @ {float(rate) * 100:.1f}%",
        )
        self.history.append(tx)
        return tx

    def preview_rate(self) -> float:
        """Non-mutating lookup of the current tiered rate."""
        return float(self._current_rate())


class CheckingAccount(BankAccount):
    """
    Checking account that permits overdraft up to a configurable limit.

    When a withdrawal drives the balance negative, a one-time overdraft
    fee is assessed in addition to the withdrawal.
    """

    account_type: str = "checking"

    def __init__(
        self,
        account_holder: str,
        initial_balance=0.0,
        account_id: str | None = None,
    ) -> None:
        super().__init__(account_holder, initial_balance, account_id)
        self.overdraft_limit: Decimal = _money(settings.overdraft_limit)
        self.overdraft_fee: Decimal = _money(settings.overdraft_fee)

    def withdraw(self, amount) -> Transaction:
        """Withdraw, allowing overdraft up to ``overdraft_limit`` with a fee."""
        if amount is None:
            raise ValueError("Withdrawal amount must be positive.")
        amt = _money(amount)
        if amt <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        new_balance = _money(self.balance - amt)
        if new_balance < self.overdraft_limit:
            raise ValueError(
                f"Withdrawal would exceed overdraft limit of ${float(self.overdraft_limit):.2f}."
            )
        self.balance = new_balance
        tx = Transaction(type="withdrawal", amount=amt, balance_after=self.balance)
        self.history.append(tx)

        # Apply fee if this withdrawal pushed balance negative
        if self.balance < 0:
            self.balance = _money(self.balance - self.overdraft_fee)
            fee_tx = Transaction(
                type="overdraft_fee",
                amount=self.overdraft_fee,
                balance_after=self.balance,
                note="Overdraft fee assessed",
            )
            self.history.append(fee_tx)
        return tx

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["overdraft_limit"] = float(self.overdraft_limit)
        d["overdraft_fee"] = float(self.overdraft_fee)
        return d


def account_from_dict(data: dict) -> BankAccount:
    """Reconstruct an account instance (Savings/Checking/Bank) from a dict."""
    atype = data.get("account_type", "bank")
    cls: type[BankAccount]
    if atype == "savings":
        cls = SavingsAccount
    elif atype == "checking":
        cls = CheckingAccount
    else:
        cls = BankAccount

    acc = cls(
        account_holder=data["account_holder"],
        initial_balance=0,
        account_id=data["account_id"],
    )
    acc.balance = _money(data.get("balance", 0))
    acc.history = [
        Transaction(
            type=tx["type"],
            amount=_money(tx["amount"]),
            balance_after=_money(tx["balance_after"]),
            timestamp=tx["timestamp"],
            note=tx.get("note", ""),
        )
        for tx in data.get("history", [])
    ]
    return acc
