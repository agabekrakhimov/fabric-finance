# fabric-finance-starter

A Microsoft Fabric starter workspace for finance analytics, containing:

- **FinanceLH** – Lakehouse for storing raw and refined financial data
- **FinanceNotebook** – Notebook for ingesting and transforming finance data into the Lakehouse
- **FinanceModel (Common)** – Shared Power BI Semantic Model built on top of the Lakehouse

## Getting Started

1. Connect this repository to a Microsoft Fabric workspace via **Workspace settings → Git integration**.
2. Sync the workspace — Fabric will provision the Lakehouse, Notebook, and Semantic Model automatically.
3. Open **FinanceNotebook** and run it to load sample data into the Lakehouse.
4. Open **FinanceModel** in Power BI to explore and build reports on the finance data.

## Repository Structure

```
FinanceLH.Lakehouse/          # Lakehouse item
FinanceNotebook.Notebook/     # Notebook item
FinanceModel.SemanticModel/   # Shared Power BI Semantic Model (common)
```