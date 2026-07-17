# Python Data Lineage Analysis Guide

## What is Considered a Transformation

In Python, a **transformation** is any operation that reads data from one or more sources and writes it to a destination, potentially modifying the data in the process.

### Transformation Granularity for JobEvents

**One JobEvent per:**
- Single data read → transform → write operation
- Single function call that performs ETL (Extract, Transform, Load)
- Single DataFrame operation that writes to persistent storage
- Single API call that moves/transforms data
- Single file processing operation (read → process → write)

**NOT separate JobEvents:**
- Intermediate DataFrame operations in memory (part of the transformation logic)
- Multiple transformations on the same DataFrame before writing (one job with complex transformation)
- Helper functions that don't directly read/write data

## What is Considered a Dataset

### Source Datasets (Inputs)
- Files read by pandas: `pd.read_csv()`, `pd.read_excel()`, `pd.read_parquet()`, `pd.read_json()`
- Database tables: `pd.read_sql()`, `pd.read_sql_query()`, `pd.read_sql_table()`
- Spark DataFrames: `spark.read.csv()`, `spark.read.parquet()`, `spark.read.jdbc()`
- API responses that return data: `requests.get()` with data extraction
- Cloud storage: S3, Azure Blob, GCS file reads
- Message queues: Kafka topics, RabbitMQ queues

### Output Datasets
- Files written: `df.to_csv()`, `df.to_excel()`, `df.to_parquet()`, `df.to_json()`
- Database tables: `df.to_sql()`, database insert operations
- Spark writes: `df.write.csv()`, `df.write.parquet()`, `df.write.jdbc()`
- API POST/PUT operations with data
- Cloud storage writes
- Message queue publishing

### NOT Datasets
- In-memory DataFrames (intermediate processing)
- Python variables and lists (unless they represent persistent data)
- Configuration dictionaries
- Logging outputs
- Print statements