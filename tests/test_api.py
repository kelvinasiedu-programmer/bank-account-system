"""Integration tests for the FastAPI endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src import main as main_module


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Fresh app instance with an isolated JSON store per test."""
    monkeypatch.setattr(
        main_module, "_bank", main_module.Bank(storage_path=str(tmp_path / "a.json"))
    )
    return TestClient(main_module.app)


class TestAPI:
    def test_health(self, client):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_create_list_delete(self, client):
        r = client.post(
            "/api/v1/accounts",
            json={"account_type": "savings", "account_holder": "Alice", "initial_balance": 100},
        )
        assert r.status_code == 201
        aid = r.json()["account_id"]

        r = client.get("/api/v1/accounts")
        assert r.status_code == 200
        assert len(r.json()) == 1

        r = client.delete(f"/api/v1/accounts/{aid}")
        assert r.status_code == 200
        assert client.get("/api/v1/accounts").json() == []

    def test_deposit_and_withdraw(self, client):
        r = client.post(
            "/api/v1/accounts",
            json={"account_type": "checking", "account_holder": "Bob", "initial_balance": 500},
        )
        aid = r.json()["account_id"]
        client.post(f"/api/v1/accounts/{aid}/deposit", json={"amount": 100})
        client.post(f"/api/v1/accounts/{aid}/withdraw", json={"amount": 50})
        bal = client.get(f"/api/v1/accounts/{aid}").json()["balance"]
        assert bal == 550.0

    def test_apply_interest(self, client):
        r = client.post(
            "/api/v1/accounts",
            json={"account_type": "savings", "account_holder": "Alice", "initial_balance": 1_000},
        )
        aid = r.json()["account_id"]
        r = client.post(f"/api/v1/accounts/{aid}/apply-interest")
        assert r.status_code == 200
        assert r.json()["balance"] == pytest.approx(1030.0)

    def test_apply_interest_on_checking_fails(self, client):
        r = client.post(
            "/api/v1/accounts",
            json={"account_type": "checking", "account_holder": "Bob", "initial_balance": 100},
        )
        aid = r.json()["account_id"]
        r = client.post(f"/api/v1/accounts/{aid}/apply-interest")
        assert r.status_code == 400

    def test_404_on_missing_account(self, client):
        r = client.get("/api/v1/accounts/does-not-exist")
        assert r.status_code == 404

    def test_invalid_payload_rejected(self, client):
        r = client.post(
            "/api/v1/accounts",
            json={"account_type": "bitcoin", "account_holder": "Z"},
        )
        assert r.status_code == 422  # Pydantic Literal validation

    def test_overdraft_endpoint(self, client):
        r = client.post(
            "/api/v1/accounts",
            json={"account_type": "checking", "account_holder": "Alex", "initial_balance": 200},
        )
        aid = r.json()["account_id"]
        r = client.post(f"/api/v1/accounts/{aid}/withdraw", json={"amount": 300})
        assert r.status_code == 200
        assert r.json()["balance"] == pytest.approx(-125.0)

    def test_stats(self, client):
        client.post(
            "/api/v1/accounts",
            json={"account_type": "savings", "account_holder": "A", "initial_balance": 100},
        )
        r = client.get("/api/v1/stats")
        assert r.status_code == 200
        body = r.json()
        assert body["total_accounts"] == 1
        assert body["total_assets"] == 100.0
