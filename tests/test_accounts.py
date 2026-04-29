"""Unit tests for the BankAccount / SavingsAccount / CheckingAccount domain."""

from __future__ import annotations

import pytest

from src.accounts import BankAccount, CheckingAccount, SavingsAccount


# ---------- BankAccount ----------
class TestBankAccount:
    def test_opens_with_history_entry(self):
        acc = BankAccount("Alice", 100)
        assert acc.balance == 100.0
        assert len(acc.history) == 1
        assert acc.history[0].type == "open"

    def test_requires_holder(self):
        with pytest.raises(ValueError):
            BankAccount("")

    def test_rejects_negative_initial_balance(self):
        with pytest.raises(ValueError):
            BankAccount("Alice", -1)

    def test_deposit_increments_balance_and_history(self):
        acc = BankAccount("Bob", 0)
        acc.deposit(50)
        assert acc.balance == 50.0
        assert acc.history[-1].type == "deposit"
        assert acc.history[-1].amount == 50.0

    def test_deposit_rejects_non_positive(self):
        acc = BankAccount("Bob", 0)
        with pytest.raises(ValueError):
            acc.deposit(0)
        with pytest.raises(ValueError):
            acc.deposit(-5)

    def test_withdraw_rejects_non_positive(self):
        acc = BankAccount("Bob", 100)
        with pytest.raises(ValueError):
            acc.withdraw(-1)

    def test_withdraw_rejects_overdraw_on_base(self):
        acc = BankAccount("Bob", 50)
        with pytest.raises(ValueError, match="Insufficient funds"):
            acc.withdraw(100)


# ---------- SavingsAccount: tiered interest ----------
class TestSavingsAccount:
    @pytest.mark.parametrize(
        "bal,expected",
        [
            (500, 515.0),  # 3% tier
            (1_000, 1_030.0),  # 3% tier boundary
            (2_000, 2_100.0),  # 5% tier
            (5_000, 5_250.0),  # 5% tier boundary
            (10_000, 10_700.0),  # 7% tier
        ],
    )
    def test_apply_interest_tiered(self, bal, expected):
        s = SavingsAccount("Tester", bal)
        s.apply_interest()
        assert s.get_balance() == pytest.approx(expected, rel=1e-3)

    def test_interest_logged_to_history(self):
        s = SavingsAccount("Tester", 1000)
        s.apply_interest()
        assert s.history[-1].type == "interest"
        assert "3.0%" in s.history[-1].note

    def test_preview_rate(self):
        assert SavingsAccount("X", 500).preview_rate() == 0.03
        assert SavingsAccount("X", 2000).preview_rate() == 0.05
        assert SavingsAccount("X", 10000).preview_rate() == 0.07


# ---------- CheckingAccount: overdraft ----------
class TestCheckingAccount:
    def test_withdraw_within_balance(self):
        c = CheckingAccount("Alex", 500)
        c.withdraw(200)
        assert c.balance == 300.0

    def test_overdraft_applies_fee(self):
        c = CheckingAccount("Alex", 200)
        c.withdraw(300)
        # 200 - 300 = -100, then -25 fee = -125
        assert c.balance == pytest.approx(-125.0)
        assert any(tx.type == "overdraft_fee" for tx in c.history)

    def test_overdraft_limit_enforced(self):
        c = CheckingAccount("Alex", 0)
        with pytest.raises(ValueError, match="overdraft limit"):
            c.withdraw(1_000)

    def test_no_fee_when_balance_stays_nonnegative(self):
        c = CheckingAccount("Alex", 500)
        c.withdraw(500)
        assert c.balance == 0.0
        assert not any(tx.type == "overdraft_fee" for tx in c.history)

    def test_serialization_roundtrip(self):
        c = CheckingAccount("Alex", 100)
        d = c.to_dict()
        assert d["account_type"] == "checking"
        assert d["overdraft_limit"] == -500.0
        assert d["overdraft_fee"] == 25.0


# ---------- Decimal precision (no float drift) ----------
class TestDecimalPrecision:
    def test_repeated_dime_deposits_do_not_drift(self):
        """Naive float arithmetic produces 0.30000000000000004 here."""
        from decimal import Decimal

        acc = BankAccount("Drifter", 0)
        for _ in range(3):
            acc.deposit(0.1)
        assert acc.balance == Decimal("0.30")

    def test_thousand_penny_deposits_sum_exactly(self):
        from decimal import Decimal

        acc = BankAccount("Penny", 0)
        for _ in range(1000):
            acc.deposit(0.01)
        assert acc.balance == Decimal("10.00")
