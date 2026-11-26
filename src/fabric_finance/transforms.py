"""Bronze to silver cleanse, and the three gold finance aggregates.

Stub USD rates are EUR 1.08, GBP 1.27, and USD 1. Gold totals are rounded
to cents after the sum. The year-to-date figure is the running sum of those
already rounded monthly totals, and it resets each year.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Mapping, Sequence

ALLOWED_CATEGORIES = ("Revenue", "COGS", "OPEX", "Payroll", "Capex", "Tax")
ALLOWED_DEPARTMENTS = (
    "Sales",
    "Marketing",
    "Engineering",
    "Finance",
    "HR",
    "Operations",
)
ALLOWED_CURRENCIES = ("USD", "EUR", "GBP")

# Stub rates until a live FX table is wired in.
FX_TO_USD = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
}

REQUIRED_FIELDS = (
    "transaction_id",
    "transaction_date",
    "category",
    "department",
    "amount",
    "currency",
)


def normalize_currency(currency: str) -> str:
    if currency is None or not str(currency).strip():
        raise ValueError("currency is required")
    return str(currency).strip().upper()


def to_amount_usd(
    amount: float,
    currency: str,
    rates: Mapping[str, float] | None = None,
) -> float:
    """Convert ``amount`` into USD. Unknown currencies are rejected."""
    code = normalize_currency(currency)
    table = FX_TO_USD if rates is None else rates
    if code not in table:
        raise ValueError(f"unsupported currency: {code}")
    return float(amount) * float(table[code])


def parse_transaction_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError("transaction_date is required")
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"transaction_date must be YYYY-MM-DD: {value}") from exc


def quarter_of(month: int) -> int:
    if month < 1 or month > 12:
        raise ValueError(f"month out of range: {month}")
    return (month - 1) // 3 + 1


def _require(row: Mapping, field: str):
    value = row.get(field)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{field} is required")
    return value


def _cents(value: float) -> float:
    return round(float(value), 2)


def cleanse_transactions(rows: Sequence[Mapping]) -> list[dict]:
    """Silver layer.

    Parses the date, derives year, month, and quarter, upper-cases the
    currency, converts the amount to USD, and keeps the first row for each
    ``transaction_id``. Run ``check_transactions`` first when invalid rows
    should be reported instead of raising.
    """
    seen: set = set()
    silver: list[dict] = []
    for row in rows:
        txn_id = _require(row, "transaction_id")
        if txn_id in seen:
            continue
        seen.add(txn_id)
        txn_date = parse_transaction_date(_require(row, "transaction_date"))
        currency = normalize_currency(_require(row, "currency"))
        amount = float(_require(row, "amount"))
        silver.append(
            {
                "transaction_id": txn_id,
                "transaction_date": txn_date.isoformat(),
                "year": txn_date.year,
                "month": txn_date.month,
                "quarter": quarter_of(txn_date.month),
                "category": _require(row, "category"),
                "department": _require(row, "department"),
                "amount": float(amount),
                "currency": currency,
                "amount_usd": to_amount_usd(amount, currency),
            }
        )
    return silver


def monthly_pl(silver_rows: Sequence[Mapping]) -> list[dict]:
    """Monthly P&L by year, quarter, month, and category."""
    totals: dict[tuple, float] = defaultdict(float)
    counts: dict[tuple, int] = defaultdict(int)
    for row in silver_rows:
        key = (row["year"], row["quarter"], row["month"], row["category"])
        totals[key] += float(row["amount_usd"])
        counts[key] += 1

    result = []
    for key in sorted(totals):
        year, quarter, month, category = key
        count = counts[key]
        total = _cents(totals[key])
        result.append(
            {
                "year": year,
                "quarter": quarter,
                "month": month,
                "category": category,
                "total_amount_usd": total,
                "transaction_count": count,
                "avg_amount_usd": _cents(totals[key] / count),
            }
        )
    return result


def department_spend(silver_rows: Sequence[Mapping]) -> list[dict]:
    """Annual spend by department, highest total first within each year."""
    totals: dict[tuple, float] = defaultdict(float)
    counts: dict[tuple, int] = defaultdict(int)
    for row in silver_rows:
        key = (row["year"], row["department"])
        totals[key] += float(row["amount_usd"])
        counts[key] += 1

    result = [
        {
            "year": year,
            "department": department,
            "total_spend_usd": _cents(totals[(year, department)]),
            "transaction_count": counts[(year, department)],
        }
        for year, department in totals
    ]
    result.sort(key=lambda row: (row["year"], -row["total_spend_usd"], row["department"]))
    return result


def ytd_totals(silver_rows: Sequence[Mapping]) -> list[dict]:
    """Running total of rounded monthly sums, reset at each year boundary."""
    monthly: dict[tuple, float] = defaultdict(float)
    for row in silver_rows:
        monthly[(row["year"], row["month"])] += float(row["amount_usd"])

    by_year: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for (year, month), total in monthly.items():
        by_year[year].append((month, _cents(total)))

    result = []
    for year in sorted(by_year):
        running = 0.0
        for month, total in sorted(by_year[year]):
            running = _cents(running + total)
            result.append(
                {
                    "year": year,
                    "month": month,
                    "monthly_total_usd": total,
                    "ytd_total_usd": running,
                }
            )
    return result
