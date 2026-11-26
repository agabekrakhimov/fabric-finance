# fabric-finance

Local, testable transforms for finance transactions: a quality gate on the raw rows, a silver cleanse, and the gold aggregates used for P&L, department spend, and year-to-date totals.

## Architecture

```
bronze rows
    │
    ▼
check_transactions          required fields, ISO dates, known categories
                            and departments, positive amounts, USD/EUR/GBP,
                            unique transaction ids
    │
    ▼
cleanse_transactions        silver: typed date, year / month / quarter,
                            currency upper-cased, amount converted to USD,
                            first row kept per transaction id
    │
    ├── monthly_pl          gold: year, quarter, month, category
    ├── department_spend    gold: year, department
    └── ytd_totals          gold: running total of monthly sums, reset each year
```

Bronze rows carry `transaction_id`, `transaction_date`, `category`, `department`, `amount`, and `currency`. Categories are `Revenue`, `COGS`, `OPEX`, `Payroll`, `Capex`, and `Tax`. Departments are `Sales`, `Marketing`, `Engineering`, `Finance`, `HR`, and `Operations`. The category carries the accounting meaning, so amounts stay positive.

USD conversion uses the stub rates until a live FX table is available:

| Currency | USD rate |
|----------|----------|
| USD | 1.00 |
| EUR | 1.08 |
| GBP | 1.27 |

Unknown currencies are rejected. They are not passed through as if they were already USD.

Gold figures are rounded to cents after each sum. The year-to-date total is the running sum of those rounded monthly totals, and it starts over in January. Months with no transactions are left out.

`check_transactions` only reports problems. `cleanse_transactions` is what builds the silver rows, and it raises if a required value is missing or the currency is not one of the three above.

## Layout

```
src/fabric_finance/transforms.py    silver cleanse and gold aggregates
src/fabric_finance/quality.py      bronze quality checks
tests/                             pytest suite for both
.github/workflows/ci.yml           runs the suite on pull requests
```

## Run the tests

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

The same install and `pytest` command run in GitHub Actions on every pull request.
