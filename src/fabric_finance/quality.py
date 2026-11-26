"""Row-level checks for bronze finance transactions.

These checks sit in front of ``cleanse_transactions``. They report problems
and leave the rows unchanged. Categories carry the accounting meaning
(Revenue, COGS, and the rest), so amounts are expected to be positive.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from fabric_finance.transforms import (
    ALLOWED_CATEGORIES,
    ALLOWED_CURRENCIES,
    ALLOWED_DEPARTMENTS,
    REQUIRED_FIELDS,
    normalize_currency,
    parse_transaction_date,
)


@dataclass(frozen=True)
class QualityIssue:
    row_index: int
    field: str | None
    message: str


def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def check_transactions(rows: Sequence[Mapping]) -> list[QualityIssue]:
    """Return one issue per problem. An empty list means the batch is clean."""
    issues: list[QualityIssue] = []
    seen_ids: dict = {}

    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            issues.append(QualityIssue(index, None, "row must be an object"))
            continue

        for field in REQUIRED_FIELDS:
            if _blank(row.get(field)):
                issues.append(QualityIssue(index, field, f"{field} is required"))

        txn_id = row.get("transaction_id")
        if not _blank(txn_id):
            if txn_id in seen_ids:
                issues.append(
                    QualityIssue(
                        index,
                        "transaction_id",
                        f"duplicate of row {seen_ids[txn_id]}",
                    )
                )
            else:
                seen_ids[txn_id] = index

        raw_date = row.get("transaction_date")
        if not _blank(raw_date):
            try:
                parse_transaction_date(raw_date)
            except ValueError as exc:
                issues.append(QualityIssue(index, "transaction_date", str(exc)))

        category = row.get("category")
        if not _blank(category) and category not in ALLOWED_CATEGORIES:
            issues.append(
                QualityIssue(index, "category", f"unknown category: {category}")
            )

        department = row.get("department")
        if not _blank(department) and department not in ALLOWED_DEPARTMENTS:
            issues.append(
                QualityIssue(
                    index,
                    "department",
                    f"unknown department: {department}",
                )
            )

        amount = row.get("amount")
        if not _blank(amount):
            try:
                value = float(amount)
            except (TypeError, ValueError):
                issues.append(QualityIssue(index, "amount", "amount must be numeric"))
            else:
                if value <= 0:
                    issues.append(
                        QualityIssue(
                            index,
                            "amount",
                            "amount must be greater than zero",
                        )
                    )

        currency = row.get("currency")
        if not _blank(currency):
            try:
                code = normalize_currency(currency)
            except ValueError as exc:
                issues.append(QualityIssue(index, "currency", str(exc)))
            else:
                if code not in ALLOWED_CURRENCIES:
                    issues.append(
                        QualityIssue(
                            index,
                            "currency",
                            f"unsupported currency: {code}",
                        )
                    )

    return issues
