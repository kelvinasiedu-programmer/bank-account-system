"""Tests for the Bank service — persistence & orchestration."""
from __future__ import annotations

import pytest

from src.bank import AccountNotFoundError, Bank


class TestBank:
    def test_create_and_get(self, bank: Bank):
        acc = bank.create_account("savings", "Alice", 100)
        fetched = bank.get(acc.account_id)
        assert fetched.account_holder == "Alice"
        assert fetched.balance == 100.0

    def test_create_checking(self, bank: Bank):
        acc = bank.create_account("checking", "Bob", 50)
        assert acc.account_type == "checking"

    def test_invalid_account_type(self, bank: Bank):
        with pytest.raises(ValueError):
            bank.create_account("crypto", "Zoe", 0)

    def test_get_missing_raises(self, bank: Bank):
        with pytest.raises(AccountNotFoundError):
            bank.get("nope")

    def test_deposit_and_withdraw(self, bank: Bank):
        acc = bank.create_account("savings", "Alice", 100)
        bank.deposit(acc.account_id, 50)
        bank.withdraw(acc.account_id, 30)
        assert bank.get(acc.account_id).balance == 120.0

    def test_apply_interest_only_savings(self, bank: Bank):
        s = bank.create_account("savings", "Alice", 500)
        c = bank.create_account("checking", "Bob", 500)
        bank.apply_interest(s.account_id)
        with pytest.raises(ValueError):
            bank.apply_interest(c.account_id)

    def test_stats(self, bank: Bank):
        bank.create_account("savings", "Alice", 1_000)
        bank.create_account("checking", "Bob", 500)
        stats = bank.stats()
        assert stats["total_accounts"] == 2
        assert stats["savings_accounts"] == 1
        assert stats["checking_accounts"] == 1
        assert stats["total_assets"] == 1_500.0

    def test_persistence_roundtrip(self, tmp_storage):
        b1 = Bank(storage_path=tmp_storage)
        a = b1.create_account("savings", "Persist", 777)

        b2 = Bank(storage_path=tmp_storage)
        assert b2.get(a.account_id).balance == 777.0

    def test_delete(self, bank: Bank):
        acc = bank.create_account("checking", "Alice", 10)
        bank.delete(acc.account_id)
        with pytest.raises(AccountNotFoundError):
            bank.get(acc.account_id)

    def test_clear(self, bank: Bank):
        bank.create_account("savings", "A", 10)
        bank.create_account("checking", "B", 10)
        bank.clear()
        assert bank.stats()["total_accounts"] == 0
