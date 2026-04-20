"""
Bank — in-memory account registry with JSON persistence.

Provides a thin service layer over the account domain model so the
FastAPI routes stay lean and free of storage concerns.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from src.accounts import (
    BankAccount,
    CheckingAccount,
    SavingsAccount,
    account_from_dict,
)


class AccountNotFoundError(KeyError):
    """Raised when an account_id does not exist."""


class Bank:
    """Thread-safe in-memory bank with JSON-backed persistence."""

    def __init__(self, storage_path: str) -> None:
        self.storage_path = Path(storage_path)
        self._lock = threading.RLock()
        self._accounts: dict[str, BankAccount] = {}
        self._load()

    def _load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            with self.storage_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            for acc in data.get("accounts", []):
                account = account_from_dict(acc)
                self._accounts[account.account_id] = account
        except (json.JSONDecodeError, OSError, KeyError):
            # Corrupt or missing data — start fresh rather than crash.
            self._accounts = {}

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.storage_path.with_suffix(".tmp")
        payload = {"accounts": [a.to_dict() for a in self._accounts.values()]}
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp, self.storage_path)

    def create_account(
        self, account_type: str, account_holder: str, initial_balance: float = 0.0
    ) -> BankAccount:
        atype = account_type.lower().strip()
        with self._lock:
            if atype == "savings":
                acc: BankAccount = SavingsAccount(account_holder, initial_balance)
            elif atype == "checking":
                acc = CheckingAccount(account_holder, initial_balance)
            else:
                raise ValueError(
                    f"Unknown account type '{account_type}'. Use 'savings' or 'checking'."
                )
            self._accounts[acc.account_id] = acc
            self._save()
            return acc

    def get(self, account_id: str) -> BankAccount:
        with self._lock:
            acc = self._accounts.get(account_id)
            if acc is None:
                raise AccountNotFoundError(account_id)
            return acc

    def list_accounts(self) -> list[BankAccount]:
        with self._lock:
            return list(self._accounts.values())

    def delete(self, account_id: str) -> None:
        with self._lock:
            if account_id not in self._accounts:
                raise AccountNotFoundError(account_id)
            del self._accounts[account_id]
            self._save()

    def clear(self) -> None:
        with self._lock:
            self._accounts.clear()
            self._save()

    def deposit(self, account_id: str, amount: float) -> BankAccount:
        with self._lock:
            acc = self.get(account_id)
            acc.deposit(amount)
            self._save()
            return acc

    def withdraw(self, account_id: str, amount: float) -> BankAccount:
        with self._lock:
            acc = self.get(account_id)
            acc.withdraw(amount)
            self._save()
            return acc

    def apply_interest(self, account_id: str) -> BankAccount:
        with self._lock:
            acc = self.get(account_id)
            if not isinstance(acc, SavingsAccount):
                raise ValueError("Interest can only be applied to savings accounts.")
            acc.apply_interest()
            self._save()
            return acc

    def stats(self) -> dict:
        with self._lock:
            accounts = list(self._accounts.values())
            savings = [a for a in accounts if isinstance(a, SavingsAccount)]
            checking = [a for a in accounts if isinstance(a, CheckingAccount)]
            return {
                "total_accounts": len(accounts),
                "savings_accounts": len(savings),
                "checking_accounts": len(checking),
                "total_assets": round(sum(a.balance for a in accounts), 2),
            }
