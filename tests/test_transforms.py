"""Unit tests for the silver cleanse and gold aggregates."""

import pytest

from fabric_finance.transforms import (
    cleanse_transactions,
    department_spend,
    monthly_pl,
    parse_transaction_date,
    quarter_of,
    to_amount_usd,
    ytd_totals,
)


def bronze(**overrides):
    row = {
        "transaction_id": "TXN-1",
        "transaction_date": "2024-01-15",
        "category": "Revenue",
        "department": "Sales",
        "amount": 100.0,
        "currency": "USD",
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        (100, "USD", 100.0),
        (100, "usd", 100.0),
        (250, "EUR", 270.0),
        (100, "gbp", 127.0),
        (10, " EUR ", 10.8),
    ],
)
def test_fx_stub_rates(amount, currency, expected):
    assert to_amount_usd(amount, currency) == expected


def test_unknown_currency_is_rejected():
    with pytest.raises(ValueError, match="unsupported currency: JPY"):
        to_amount_usd(10, "jpy")


@pytest.mark.parametrize(
    ("month", "quarter"),
    [(1, 1), (3, 1), (4, 2), (6, 2), (7, 3), (12, 4)],
)
def test_quarter_boundaries(month, quarter):
    assert quarter_of(month) == quarter


def test_date_must_be_iso():
    assert parse_transaction_date("2024-02-29").isoformat() == "2024-02-29"
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        parse_transaction_date("01/15/2024")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        parse_transaction_date("2024-13-01")


def test_cleanse_types_and_converts_a_row():
    silver = cleanse_transactions([bronze(amount=250, currency="eur")])
    assert silver == [
        {
            "transaction_id": "TXN-1",
            "transaction_date": "2024-01-15",
            "year": 2024,
            "month": 1,
            "quarter": 1,
            "category": "Revenue",
            "department": "Sales",
            "amount": 250.0,
            "currency": "EUR",
            "amount_usd": 270.0,
        }
    ]


def test_cleanse_keeps_the_first_row_for_a_duplicate_id():
    rows = [
        bronze(transaction_id="TXN-9", amount=40, currency="USD"),
        bronze(transaction_id="TXN-9", amount=999, currency="EUR", category="COGS"),
        bronze(transaction_id="TXN-10", amount=10, currency="USD"),
    ]
    silver = cleanse_transactions(rows)
    assert [row["transaction_id"] for row in silver] == ["TXN-9", "TXN-10"]
    assert silver[0]["amount_usd"] == 40.0
    assert silver[0]["category"] == "Revenue"


def test_cleanse_raises_when_a_required_value_is_missing():
    with pytest.raises(ValueError, match="transaction_date is required"):
        cleanse_transactions([bronze(transaction_date="")])


def test_gold_rollups_from_a_small_batch():
    silver = cleanse_transactions(
        [
            bronze(transaction_id="A", transaction_date="2024-01-15", amount=100, currency="EUR", category="Revenue", department="Sales"),
            bronze(transaction_id="B", transaction_date="2024-01-20", amount=50, currency="GBP", category="COGS", department="Engineering"),
            bronze(transaction_id="C", transaction_date="2024-02-02", amount=80, currency="USD", category="Revenue", department="Sales"),
            bronze(transaction_id="A", transaction_date="2024-01-15", amount=1, currency="USD", category="Revenue", department="Sales"),
            bronze(transaction_id="D", transaction_date="2024-01-18", amount=20, currency="USD", category="Revenue", department="Sales"),
            bronze(transaction_id="E", transaction_date="2023-12-01", amount=10, currency="USD", category="OPEX", department="Finance"),
        ]
    )

    assert monthly_pl(silver) == [
        {
            "year": 2023,
            "quarter": 4,
            "month": 12,
            "category": "OPEX",
            "total_amount_usd": 10.0,
            "transaction_count": 1,
            "avg_amount_usd": 10.0,
        },
        {
            "year": 2024,
            "quarter": 1,
            "month": 1,
            "category": "COGS",
            "total_amount_usd": 63.5,
            "transaction_count": 1,
            "avg_amount_usd": 63.5,
        },
        {
            "year": 2024,
            "quarter": 1,
            "month": 1,
            "category": "Revenue",
            "total_amount_usd": 128.0,
            "transaction_count": 2,
            "avg_amount_usd": 64.0,
        },
        {
            "year": 2024,
            "quarter": 1,
            "month": 2,
            "category": "Revenue",
            "total_amount_usd": 80.0,
            "transaction_count": 1,
            "avg_amount_usd": 80.0,
        },
    ]

    assert department_spend(silver) == [
        {
            "year": 2023,
            "department": "Finance",
            "total_spend_usd": 10.0,
            "transaction_count": 1,
        },
        {
            "year": 2024,
            "department": "Sales",
            "total_spend_usd": 208.0,
            "transaction_count": 3,
        },
        {
            "year": 2024,
            "department": "Engineering",
            "total_spend_usd": 63.5,
            "transaction_count": 1,
        },
    ]

    assert ytd_totals(silver) == [
        {
            "year": 2023,
            "month": 12,
            "monthly_total_usd": 10.0,
            "ytd_total_usd": 10.0,
        },
        {
            "year": 2024,
            "month": 1,
            "monthly_total_usd": 191.5,
            "ytd_total_usd": 191.5,
        },
        {
            "year": 2024,
            "month": 2,
            "monthly_total_usd": 80.0,
            "ytd_total_usd": 271.5,
        },
    ]


def test_ytd_skips_empty_months_and_resets_each_year():
    silver = cleanse_transactions(
        [
            bronze(transaction_id="Y1", transaction_date="2024-01-05", amount=10),
            bronze(transaction_id="Y2", transaction_date="2024-03-05", amount=5),
            bronze(transaction_id="Y3", transaction_date="2025-01-05", amount=7),
        ]
    )
    assert ytd_totals(silver) == [
        {"year": 2024, "month": 1, "monthly_total_usd": 10.0, "ytd_total_usd": 10.0},
        {"year": 2024, "month": 3, "monthly_total_usd": 5.0, "ytd_total_usd": 15.0},
        {"year": 2025, "month": 1, "monthly_total_usd": 7.0, "ytd_total_usd": 7.0},
    ]


def test_empty_inputs_stay_empty():
    assert cleanse_transactions([]) == []
    assert monthly_pl([]) == []
    assert department_spend([]) == []
    assert ytd_totals([]) == []
