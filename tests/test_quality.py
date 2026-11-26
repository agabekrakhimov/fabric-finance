"""Unit tests for bronze transaction quality checks."""

from fabric_finance.quality import QualityIssue, check_transactions
from fabric_finance.transforms import cleanse_transactions


def bronze(**overrides):
    row = {
        "transaction_id": "TXN-1",
        "transaction_date": "2024-03-01",
        "category": "Payroll",
        "department": "HR",
        "amount": 1200.5,
        "currency": "GBP",
    }
    row.update(overrides)
    return row


def test_a_valid_batch_has_no_issues():
    rows = [
        bronze(),
        bronze(transaction_id="TXN-2", category="Tax", department="Finance", currency="eur"),
    ]
    assert check_transactions(rows) == []
    assert len(cleanse_transactions(rows)) == 2


def test_reports_missing_fields_duplicates_and_bad_values():
    rows = [
        bronze(transaction_id=" ", transaction_date="", amount=None, category=""),
        bronze(transaction_id="TXN-2", transaction_date="2024/01/02", category="revenue", department="Legal", amount=0, currency="jpy"),
        bronze(transaction_id="TXN-2", amount=-15, currency="USD"),
        "not-a-row",
    ]

    issues = check_transactions(rows)

    assert QualityIssue(0, "transaction_id", "transaction_id is required") in issues
    assert QualityIssue(0, "transaction_date", "transaction_date is required") in issues
    assert QualityIssue(0, "category", "category is required") in issues
    assert QualityIssue(0, "amount", "amount is required") in issues
    assert QualityIssue(1, "transaction_date", "transaction_date must be YYYY-MM-DD: 2024/01/02") in issues
    assert QualityIssue(1, "category", "unknown category: revenue") in issues
    assert QualityIssue(1, "department", "unknown department: Legal") in issues
    assert QualityIssue(1, "amount", "amount must be greater than zero") in issues
    assert QualityIssue(1, "currency", "unsupported currency: JPY") in issues
    assert QualityIssue(2, "transaction_id", "duplicate of row 1") in issues
    assert QualityIssue(2, "amount", "amount must be greater than zero") in issues
    assert QualityIssue(3, None, "row must be an object") in issues


def test_non_numeric_amount_is_flagged():
    issues = check_transactions([bronze(amount="twelve")])
    assert issues == [QualityIssue(0, "amount", "amount must be numeric")]


def test_checks_do_not_change_the_input_rows():
    rows = [bronze(amount=-1)]
    snapshot = [dict(rows[0])]
    check_transactions(rows)
    assert rows == snapshot
