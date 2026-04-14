"""Shared pytest fixtures."""
from __future__ import annotations

import pytest

from src.accounts import CheckingAccount, SavingsAccount
from src.bank import Bank


@pytest.fixture
def tmp_storage(tmp_path):
    """Return a fresh storage path under a pytest tmp_path."""
    return str(tmp_path / "accounts.json")


@pytest.fixture
def bank(tmp_storage) -> Bank:
    return Bank(storage_path=tmp_storage)


@pytest.fixture
def savings() -> SavingsAccount:
    return SavingsAccount("Jane Doe", 1_000.0)


@pytest.fixture
def checking() -> CheckingAccount:
    return CheckingAccount("John Doe", 200.0)
