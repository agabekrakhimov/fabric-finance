# fabric-finance-starter

A **Microsoft Fabric** ready starter project for financial analytics.

## What's inside

| Item | Fabric Type | Description |
|------|-------------|-------------|
| `FinanceLakehouse.Lakehouse` | Lakehouse | Delta Lake storage with **raw / curated / gold** folders |
| `FinanceNotebook.Notebook` | Notebook (PySpark) | Medallion ETL: Bronze → Silver → Gold for transactions |
| `FinanceSemanticModel.SemanticModel` | Power BI Semantic Model | DirectLake model with DAX measures (P&L, EBITDA, YTD) |

---

## Architecture

```
FinanceLakehouse
├── Files/
│   ├── raw/           ← Bronze: raw CSV / JSON / Parquet ingestion
│   └── curated/       ← Silver: cleansed & typed Delta tables
└── Tables/
    ├── gold_monthly_pl    ← Monthly P&L by category
    ├── gold_dept_spend    ← Annual department spend
    └── gold_ytd_totals    ← YTD running totals
          ↑
FinanceSemanticModel (DirectLake)
  • Measures: Total Revenue, Gross Profit, Gross Margin %, EBITDA, EBITDA Margin %
  • DateTable (calculated, 2020-2030)
  • Relationships: MonthlyPL / DeptSpend / YTDTotals → DateTable
```

---

## Quick Start

### Prerequisites

- Microsoft Fabric capacity (F2 or higher, or a trial)
- Fabric Git Integration enabled on your workspace

### Import via Git Integration

1. In your Fabric workspace go to **Workspace settings → Git integration**.
2. Connect to this repository and select the branch you want to sync.
3. Click **Update all** — Fabric will create the Lakehouse, Notebook, and Semantic Model automatically.

### Run the notebook

1. Open **FinanceNotebook** in your workspace.
2. Attach it to **FinanceLakehouse** (already configured in the notebook metadata).
3. Click **Run all** — this generates 500 sample transactions and populates the three Gold tables.

### Explore the semantic model

1. Open **FinanceSemanticModel** in Power BI.
2. The DirectLake tables are ready to use — drag measures onto a report canvas.
3. Key measures available out of the box:

| Measure | Description |
|---------|-------------|
| `Total Revenue USD` | Sum of Revenue category transactions |
| `Total COGS USD` | Sum of COGS category transactions |
| `Gross Profit USD` | Revenue − COGS |
| `Gross Margin %` | Gross Profit / Revenue |
| `Total OPEX USD` | OPEX + Payroll spend |
| `EBITDA USD` | Gross Profit − OPEX |
| `EBITDA Margin %` | EBITDA / Revenue |
| `Total Dept Spend USD` | Total spend by department |
| `Latest YTD Total USD` | YTD running total for selected period |

---

## Project structure

```
fabric-finance-starter/
├── .fabric/
│   └── workspace.yml                          # Workspace metadata
│
├── FinanceLakehouse.Lakehouse/
│   ├── .platform                              # Fabric item metadata
│   └── lakehouse.metadata.json                # Folder layout (raw/curated/gold)
│
├── FinanceNotebook.Notebook/
│   ├── .platform                              # Fabric item metadata
│   └── notebook-content.py                   # PySpark ETL notebook
│
└── FinanceSemanticModel.SemanticModel/
    ├── .platform                              # Fabric item metadata
    ├── definition.pbism                       # Compatibility level
    └── definition/
        └── model.tmdl                         # TMDL: tables, measures, relationships
```

---

## Customising the notebook

The sample data generator in Cell 1 can be replaced with a real data source:

```python
# Load from ADLS Gen2 / OneLake
mssparkutils.fs.cp(
    "abfss://container@storageaccount.dfs.core.windows.net/transactions.csv",
    "Files/raw/transactions.csv"
)
df = spark.read.option("header", True).csv("Files/raw/transactions.csv")
```

FX conversion rates in Cell 2 (Silver layer) are stubs — replace them with a
live rates table or a `notebookutils.credentials` call to your FX API.

---

## Contributing

Pull requests are welcome. Please keep Fabric item folders clean — do not commit
`.pbix` files or large binary data files.

## License

MIT
