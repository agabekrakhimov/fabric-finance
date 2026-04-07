# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
# META       "default_lakehouse_name": "FinanceLH",
# META       "default_lakehouse_workspace_id": ""
# META     }
# META   }
# META }

# MARKDOWN ********************

# META {
# META   "language": "markdown",
# META   "language_group": "synapse_pyspark"
# META }

# ## Finance Data Ingestion Notebook
# 
# This notebook ingests sample financial transactions into the **FinanceLH** Lakehouse
# and prepares them for reporting via the **FinanceModel** Semantic Model.

# CELL ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, DateType
from pyspark.sql.functions import col, to_date
import datetime

spark = SparkSession.builder.getOrCreate()

# CELL ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# Sample finance transactions data
data = [
    ("TXN001", "2024-01-05", "Revenue",  "Product Sales",    15000.00, "USD"),
    ("TXN002", "2024-01-10", "Expense",  "Operating Costs",  -4500.00, "USD"),
    ("TXN003", "2024-01-15", "Revenue",  "Service Fees",      8200.00, "USD"),
    ("TXN004", "2024-01-20", "Expense",  "Marketing",        -2100.00, "USD"),
    ("TXN005", "2024-02-03", "Revenue",  "Product Sales",    17500.00, "USD"),
    ("TXN006", "2024-02-08", "Expense",  "Salaries",        -12000.00, "USD"),
    ("TXN007", "2024-02-14", "Revenue",  "Consulting",        5300.00, "USD"),
    ("TXN008", "2024-02-22", "Expense",  "Office Supplies",   -800.00, "USD"),
    ("TXN009", "2024-03-01", "Revenue",  "Product Sales",    21000.00, "USD"),
    ("TXN010", "2024-03-15", "Expense",  "Operating Costs",  -5100.00, "USD"),
]

schema = StructType([
    StructField("TransactionID", StringType(), False),
    StructField("TransactionDate", StringType(), False),
    StructField("Category",       StringType(), False),
    StructField("Description",    StringType(), False),
    StructField("Amount",         DoubleType(), False),
    StructField("Currency",       StringType(), False),
])

df = spark.createDataFrame(data, schema=schema)
df = df.withColumn("TransactionDate", to_date(col("TransactionDate"), "yyyy-MM-dd"))

# CELL ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# Write to the Lakehouse as a Delta table
df.write.format("delta").mode("overwrite").saveAsTable("transactions")

print("Transactions table created successfully.")
df.show()

# CELL ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# Create a summary view by month and category
summary_df = (
    df.groupBy(
        "Category",
        "Currency"
    )
    .agg({"Amount": "sum"})
    .withColumnRenamed("sum(Amount)", "TotalAmount")
    .orderBy("Category")
)

summary_df.write.format("delta").mode("overwrite").saveAsTable("transactions_summary")

print("Summary table created successfully.")
summary_df.show()
