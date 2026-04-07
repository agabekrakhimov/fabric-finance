# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "FinanceLakehouse",
# META       "default_lakehouse_name": "FinanceLakehouse",
# META       "known_lakehouses": [
# META         {
# META           "id": "00000000-0000-0000-0000-000000000001"
# META         }
# META       ]
# META     }
# META   }
# META }

# CELL ********************

# %% [markdown]
# # Finance Starter Notebook
# 
# This notebook demonstrates a typical **Bronze → Silver → Gold** medallion
# architecture for financial data inside Microsoft Fabric.
#
# **Layers**
# | Layer  | Folder in Lakehouse | Description |
# |--------|--------------------|---------------------------------------------------------|
# | Bronze | `raw/`             | Raw source data as received (CSV, JSON, Parquet)       |
# | Silver | `curated/`         | Cleansed, typed, and deduplicated finance tables        |
# | Gold   | `gold/`            | Aggregated KPIs ready for Power BI semantic model      |

# CELL ********************

# ── 0. Imports & Spark session ────────────────────────────────────────────────
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField,
    StringType, DoubleType, DateType, IntegerType
)

spark = SparkSession.builder.getOrCreate()
print(f"Spark version: {spark.version}")

# CELL ********************

# ── 1. BRONZE — generate sample finance data ─────────────────────────────────
#
# In production, replace this cell with a real data source:
#   • mssparkutils.fs.cp(source_url, "Files/raw/transactions.csv")
#   • df = spark.read.option("header", True).csv("Files/raw/transactions.csv")

from datetime import date, timedelta
import random, string

random.seed(42)

CATEGORIES  = ["Revenue", "COGS", "OPEX", "Payroll", "Capex", "Tax"]
DEPARTMENTS = ["Sales", "Marketing", "Engineering", "Finance", "HR", "Operations"]
CURRENCIES  = ["USD", "EUR", "GBP"]

def rand_date(start_year=2023):
    base = date(start_year, 1, 1)
    # use 365 days to cover the full non-leap year; for leap years this stays within the year
    days_in_year = (date(start_year + 1, 1, 1) - base).days
    return (base + timedelta(days=random.randint(0, days_in_year - 1))).isoformat()

rows = [
    (
        f"TXN-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}",
        rand_date(),
        random.choice(CATEGORIES),
        random.choice(DEPARTMENTS),
        round(random.uniform(1_000, 500_000), 2),
        random.choice(CURRENCIES),
    )
    for _ in range(500)
]

schema = StructType([
    StructField("transaction_id", StringType(),  False),
    StructField("transaction_date", StringType(), False),
    StructField("category",        StringType(),  False),
    StructField("department",      StringType(),  False),
    StructField("amount",          DoubleType(),  False),
    StructField("currency",        StringType(),  False),
])

bronze_df = spark.createDataFrame(rows, schema)
bronze_df.write.format("delta").mode("overwrite").save("Files/raw/transactions")
print(f"Bronze: {bronze_df.count()} rows written to Files/raw/transactions")
bronze_df.show(5, truncate=False)

# CELL ********************

# ── 2. SILVER — cleanse and type the raw data ─────────────────────────────────

silver_df = (
    spark.read.format("delta").load("Files/raw/transactions")
    # cast date string to DateType
    .withColumn("transaction_date", F.to_date("transaction_date", "yyyy-MM-dd"))
    # derive year / month / quarter for time-intelligence
    .withColumn("year",    F.year("transaction_date"))
    .withColumn("month",   F.month("transaction_date"))
    .withColumn("quarter", F.quarter("transaction_date"))
    # normalise currency to upper-case
    .withColumn("currency", F.upper("currency"))
    # drop exact duplicates (safety net)
    .dropDuplicates(["transaction_id"])
    # simple USD normalisation (stub — replace with real FX rates)
    .withColumn(
        "amount_usd",
        F.when(F.col("currency") == "EUR", F.col("amount") * 1.08)
         .when(F.col("currency") == "GBP", F.col("amount") * 1.27)
         .otherwise(F.col("amount"))
    )
)

silver_df.write.format("delta").mode("overwrite").partitionBy("year", "month").save("Files/curated/transactions")
print(f"Silver: {silver_df.count()} rows written to Files/curated/transactions")
silver_df.printSchema()

# CELL ********************

# ── 3. GOLD — aggregate KPIs for reporting ────────────────────────────────────

# 3a. Monthly P&L summary by category
monthly_pl = (
    silver_df
    .groupBy("year", "quarter", "month", "category")
    .agg(
        F.round(F.sum("amount_usd"), 2).alias("total_amount_usd"),
        F.count("transaction_id").alias("transaction_count"),
        F.round(F.avg("amount_usd"), 2).alias("avg_amount_usd"),
    )
    .orderBy("year", "month", "category")
)

monthly_pl.write.format("delta").mode("overwrite").save("Tables/gold_monthly_pl")
print("Gold: gold_monthly_pl saved as a managed Delta table")
monthly_pl.show(10)

# CELL ********************

# 3b. Department spend summary
dept_spend = (
    silver_df
    .groupBy("year", "department")
    .agg(
        F.round(F.sum("amount_usd"), 2).alias("total_spend_usd"),
        F.count("transaction_id").alias("transaction_count"),
    )
    .orderBy("year", F.desc("total_spend_usd"))
)

dept_spend.write.format("delta").mode("overwrite").save("Tables/gold_dept_spend")
print("Gold: gold_dept_spend saved as a managed Delta table")
dept_spend.show(10)

# CELL ********************

# 3c. Running totals (cumulative YTD spend)
from pyspark.sql.window import Window

ytd_window = Window.partitionBy("year").orderBy("month").rowsBetween(Window.unboundedPreceding, 0)

ytd_df = (
    silver_df
    .groupBy("year", "month")
    .agg(F.round(F.sum("amount_usd"), 2).alias("monthly_total_usd"))
    .withColumn("ytd_total_usd", F.round(F.sum("monthly_total_usd").over(ytd_window), 2))
    .orderBy("year", "month")
)

ytd_df.write.format("delta").mode("overwrite").save("Tables/gold_ytd_totals")
print("Gold: gold_ytd_totals saved as a managed Delta table")
ytd_df.show(12)

# CELL ********************

# %% [markdown]
# ## Summary
#
# Three Gold Delta tables are now available in **FinanceLakehouse**:
#
# | Table | Description |
# |-------|-------------|
# | `gold_monthly_pl`  | Monthly P&L by category — feeds the P&L Matrix visual |
# | `gold_dept_spend`  | Annual department spend — feeds the Department Spend bar chart |
# | `gold_ytd_totals`  | YTD running totals — feeds the YTD KPI card |
#
# The **FinanceSemanticModel** Power BI semantic model connects to these tables.
print("✅ Finance Notebook completed successfully.")
