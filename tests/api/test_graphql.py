"""Tests for GraphQL queries, mutations, and DataLoader batching."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from httpx import AsyncClient


async def _gql(
    client: AsyncClient, query: str, variables: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Helper: execute a GraphQL query and return the JSON body."""
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = await client.post("/graphql", json=payload)
    assert resp.status_code == 200
    return resp.json()


# --- Query tests ---


@pytest.mark.asyncio
async def test_account_balance_found(client: AsyncClient) -> None:
    query = """
        query {
            accountBalance(phoneNumber: "+2348012345678") {
                id
                phoneNumber
                name
                balance
                currency
                plan
                status
                region
            }
        }
    """
    body = await _gql(client, query)
    assert body.get("errors") is None
    account = body["data"]["accountBalance"]
    assert account["phoneNumber"] == "+2348012345678"
    assert account["name"] == "Amina Bello"
    assert float(account["balance"]) == 15000.50
    assert account["region"] == "kano"


@pytest.mark.asyncio
async def test_account_balance_not_found(client: AsyncClient) -> None:
    query = """
        query {
            accountBalance(phoneNumber: "+2340000000000") {
                id
                name
            }
        }
    """
    body = await _gql(client, query)
    assert body.get("errors") is None
    assert body["data"]["accountBalance"] is None


@pytest.mark.asyncio
async def test_transaction_history(client: AsyncClient) -> None:
    query = """
        query {
            transactionHistory(accountId: "11111111-1111-1111-1111-111111111111") {
                id
                amount
                merchant
                status
                type
            }
        }
    """
    body = await _gql(client, query)
    assert body.get("errors") is None
    txns = body["data"]["transactionHistory"]
    assert len(txns) == 2
    assert txns[0]["merchant"] == "MTN Airtime"


@pytest.mark.asyncio
async def test_transaction_history_with_last(client: AsyncClient) -> None:
    query = """
        query {
            transactionHistory(accountId: "11111111-1111-1111-1111-111111111111", last: 1) {
                id
                merchant
            }
        }
    """
    body = await _gql(client, query)
    assert body.get("errors") is None
    txns = body["data"]["transactionHistory"]
    assert len(txns) == 1


@pytest.mark.asyncio
async def test_transaction_history_empty(client: AsyncClient) -> None:
    query = """
        query {
            transactionHistory(accountId: "99999999-9999-9999-9999-999999999999") {
                id
            }
        }
    """
    body = await _gql(client, query)
    assert body.get("errors") is None
    assert body["data"]["transactionHistory"] == []


@pytest.mark.asyncio
async def test_network_status(client: AsyncClient) -> None:
    query = """
        query {
            networkStatus(region: "kano") {
                region
                status
                latencyMs
                lastChecked
            }
        }
    """
    body = await _gql(client, query)
    assert body.get("errors") is None
    ns = body["data"]["networkStatus"]
    assert ns["region"] == "kano"
    assert ns["status"] == "healthy"
    assert ns["latencyMs"] == 45.2


@pytest.mark.asyncio
async def test_network_status_not_found(client: AsyncClient) -> None:
    query = """
        query {
            networkStatus(region: "unknown") {
                region
            }
        }
    """
    body = await _gql(client, query)
    assert body.get("errors") is None
    assert body["data"]["networkStatus"] is None


# --- Mutation tests ---


@pytest.mark.asyncio
async def test_process_payment_requires_confirmation(client: AsyncClient) -> None:
    query = """
        mutation {
            processPayment(phoneNumber: "+2348012345678", amount: 1000.0, merchant: "MTN") {
                success
                message
                referenceId
                requiresConfirmation
            }
        }
    """
    body = await _gql(client, query)
    assert body.get("errors") is None
    result = body["data"]["processPayment"]
    assert result["success"] is True
    assert result["requiresConfirmation"] is True
    assert result["referenceId"] is not None


@pytest.mark.asyncio
async def test_reset_pin_requires_confirmation(client: AsyncClient) -> None:
    query = """
        mutation {
            resetPin(phoneNumber: "+2348012345678") {
                success
                requiresConfirmation
            }
        }
    """
    body = await _gql(client, query)
    assert body.get("errors") is None
    assert body["data"]["resetPin"]["requiresConfirmation"] is True


@pytest.mark.asyncio
async def test_change_plan_requires_confirmation(client: AsyncClient) -> None:
    query = """
        mutation {
            changePlan(phoneNumber: "+2348012345678", newPlan: "premium") {
                success
                requiresConfirmation
                message
            }
        }
    """
    body = await _gql(client, query)
    assert body.get("errors") is None
    result = body["data"]["changePlan"]
    assert result["requiresConfirmation"] is True
    assert "premium" in result["message"]


@pytest.mark.asyncio
async def test_create_escalation_ticket_requires_confirmation(client: AsyncClient) -> None:
    query = """
        mutation {
            createEscalationTicket(phoneNumber: "+2348012345678", issue: "Cannot send money") {
                success
                requiresConfirmation
                message
            }
        }
    """
    body = await _gql(client, query)
    assert body.get("errors") is None
    result = body["data"]["createEscalationTicket"]
    assert result["requiresConfirmation"] is True


# --- DataLoader batching test ---


@pytest.mark.asyncio
async def test_dataloader_batches_account_lookups(client: AsyncClient) -> None:
    """Verify that multiple account lookups within one query use the DataLoader batch."""
    # We use aliases to request two accounts in a single query
    query = """
        query {
            a1: accountBalance(phoneNumber: "+2348012345678") { name }
            a2: accountBalance(phoneNumber: "+2348087654321") { name }
        }
    """
    with patch(
        "src.api.mock_resolvers.get_customers_batch",
        wraps=_real_batch,
    ) as mock_batch:
        body = await _gql(client, query)

    assert body.get("errors") is None
    assert body["data"]["a1"]["name"] == "Amina Bello"
    assert body["data"]["a2"]["name"] == "Musa Ibrahim"
    # DataLoader should batch both into a single call
    mock_batch.assert_called_once()


async def _real_batch(phone_numbers: list[str]):
    """Delegate to real implementation so the test gets real data."""
    from src.api.mock_resolvers import MOCK_CUSTOMERS

    return [MOCK_CUSTOMERS.get(phone) for phone in phone_numbers]
