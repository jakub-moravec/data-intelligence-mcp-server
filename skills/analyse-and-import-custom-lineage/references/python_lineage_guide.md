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

### Examples

**✓ CORRECT - One JobEvent:**
```python
# Read, transform, and write in one logical operation
df = pd.read_csv('input/customers.csv')
df['full_name'] = df['first_name'] + ' ' + df['last_name']
df['total_spent'] = df['price'] * df['quantity']
df.to_csv('output/customer_summary.csv', index=False)
```

**✓ CORRECT - One JobEvent per write operation:**
```python
# JobEvent 1: Load and filter
df = pd.read_csv('input/orders.csv')
filtered_df = df[df['status'] == 'completed']
filtered_df.to_csv('temp/filtered_orders.csv', index=False)

# JobEvent 2: Aggregate and summarize
summary_df = filtered_df.groupby('region')['amount'].sum()
summary_df.to_csv('output/sales_summary.csv')
```

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

## Understanding Lineage and Transformation Logic

### How Data Reading Looks Like

**Pandas - CSV Files:**
```python
df = pd.read_csv('data/customers.csv')
df = pd.read_csv('s3://bucket/data/orders.csv')
```
- **Input Dataset:** File path or S3 URI
- **Columns Read:** All columns in the file (or specified in `usecols` parameter)

**Pandas - Database:**
```python
import sqlalchemy
engine = sqlalchemy.create_engine('postgresql://user:pass@host:5432/dbname')
df = pd.read_sql('SELECT * FROM customers WHERE status = "active"', engine)
df = pd.read_sql_table('orders', engine, schema='sales')
```
- **Input Dataset:** Database table referenced in query or table name
- **Connection:** Extract from connection string (host, port, database)

**PySpark - Files:**
```python
df = spark.read.csv('hdfs://namenode:9000/data/customers.csv', header=True)
df = spark.read.parquet('s3a://bucket/data/orders/')
df = spark.read.json('gs://bucket/data/events.json')
```
- **Input Dataset:** File path (HDFS, S3, GCS)
- **Format:** CSV, Parquet, JSON, etc.

**PySpark - Database:**
```python
df = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://host:5432/dbname") \
    .option("dbtable", "customers") \
    .option("user", "username") \
    .option("password", "password") \
    .load()
```
- **Input Dataset:** Table specified in `dbtable` option
- **Connection:** Extract from JDBC URL

### How Data Writing Looks Like

**Pandas - CSV Files:**
```python
df.to_csv('output/customer_summary.csv', index=False)
df.to_csv('s3://bucket/output/results.csv')
```
- **Output Dataset:** File path or S3 URI
- **Columns Written:** All columns in DataFrame (or specified in `columns` parameter)

**Pandas - Database:**
```python
df.to_sql('customer_summary', engine, schema='analytics', 
          if_exists='replace', index=False)
```
- **Output Dataset:** Table name with schema
- **Write Mode:** `if_exists` parameter ('replace', 'append', 'fail')

**PySpark - Files:**
```python
df.write.csv('hdfs://namenode:9000/output/results/', header=True, mode='overwrite')
df.write.parquet('s3a://bucket/output/data/', mode='append')
```
- **Output Dataset:** Directory path
- **Write Mode:** 'overwrite', 'append', 'ignore', 'error'

**PySpark - Database:**
```python
df.write \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://host:5432/dbname") \
    .option("dbtable", "sales_summary") \
    .option("user", "username") \
    .option("password", "password") \
    .mode("overwrite") \
    .save()
```
- **Output Dataset:** Table specified in `dbtable` option

### How to Identify Transformations

#### Direct Transformations (Column values flow to output)

**1. Column Calculations:**
```python
df['total_amount'] = df['price'] * df['quantity']
df['tax'] = df['total_amount'] * 0.1
df['discount_price'] = df['price'] * (1 - df['discount_rate'])
```
- **Transformation Type:** TRANSFORMATION
- **Lineage:** `price` + `quantity` → `total_amount` (calculation: price * quantity)
- **Lineage:** `total_amount` → `tax` (calculation: total_amount * 0.1)
- **Lineage:** `price` + `discount_rate` → `discount_price` (calculation: price * (1 - discount_rate))

**2. String Operations:**
```python
df['full_name'] = df['first_name'] + ' ' + df['last_name']
df['email_domain'] = df['email'].str.split('@').str[1]
df['upper_name'] = df['customer_name'].str.upper()
```
- **Transformation Type:** TRANSFORMATION
- **Lineage:** `first_name` + `last_name` → `full_name` (concatenation)
- **Lineage:** `email` → `email_domain` (extract domain)
- **Lineage:** `customer_name` → `upper_name` (uppercase conversion)

**3. Aggregations:**
```python
summary = df.groupby('region').agg({
    'amount': 'sum',
    'order_id': 'count',
    'price': 'mean'
}).reset_index()
summary.columns = ['region', 'total_sales', 'order_count', 'avg_price']
```
- **Transformation Type:** AGGREGATION
- **Lineage:** `region` → `region` (IDENTITY - grouping key)
- **Lineage:** `amount` → `total_sales` (AGGREGATION: sum)
- **Lineage:** `order_id` → `order_count` (AGGREGATION: count)
- **Lineage:** `price` → `avg_price` (AGGREGATION: mean)

**4. Column Renames:**
```python
df = df.rename(columns={
    'customer_id': 'cust_id',
    'customer_name': 'name'
})
```
- **Transformation Type:** IDENTITY
- **Lineage:** `customer_id` → `cust_id` (rename)
- **Lineage:** `customer_name` → `name` (rename)

**5. Apply Functions:**
```python
def calculate_tier(total_spent):
    if total_spent > 10000:
        return 'Gold'
    elif total_spent > 5000:
        return 'Silver'
    else:
        return 'Bronze'

df['customer_tier'] = df['total_spent'].apply(calculate_tier)
```
- **Transformation Type:** TRANSFORMATION
- **Lineage:** `total_spent` → `customer_tier` (custom function logic)

**6. PySpark Transformations:**
```python
from pyspark.sql.functions import col, concat, lit, sum, avg

df = df.withColumn('full_name', concat(col('first_name'), lit(' '), col('last_name')))
df = df.withColumn('total_amount', col('price') * col('quantity'))

summary = df.groupBy('region').agg(
    sum('amount').alias('total_sales'),
    avg('price').alias('avg_price')
)
```
- **Lineage:** `first_name` + `last_name` → `full_name` (concatenation)
- **Lineage:** `price` + `quantity` → `total_amount` (multiplication)
- **Lineage:** `amount` → `total_sales` (AGGREGATION: sum)
- **Lineage:** `price` → `avg_price` (AGGREGATION: avg)

#### Indirect Transformations (Column influences result but values don't flow)

**1. Filtering (WHERE equivalent):**
```python
filtered_df = df[df['status'] == 'active']
filtered_df = df[(df['amount'] > 100) & (df['region'] == 'US')]
```
- **INDIRECT Lineage:** `status` influences which rows are included
- **INDIRECT Lineage:** `amount` and `region` influence filtering
- **DIRECT Lineage:** All other columns flow through as IDENTITY

**2. Joins:**
```python
result = orders.merge(customers, on='customer_id', how='left')
result = orders.merge(customers, 
                     left_on='cust_id', 
                     right_on='customer_id',
                     how='inner')
```
- **INDIRECT Lineage:** Join keys (`customer_id`, `cust_id`) determine matching
- **DIRECT Lineage:** All selected columns from both DataFrames

**3. Sorting:**
```python
sorted_df = df.sort_values('order_date', ascending=False)
sorted_df = df.sort_values(['region', 'amount'], ascending=[True, False])
```
- **INDIRECT Lineage:** Sort columns affect row ordering
- **DIRECT Lineage:** All columns flow through as IDENTITY

### How to Identify Column Mappings

**Step-by-step approach:**

1. **Track DataFrame transformations** from read to write
2. **For each output column, trace back through operations:**
   - Direct assignment: `df['new_col'] = df['old_col']`
   - Calculation: `df['total'] = df['price'] * df['quantity']`
   - Rename: `df.rename(columns={'old': 'new'})`
   - Aggregation: `df.groupby('key')['value'].sum()`

3. **Determine transformation type:**
   - No change or rename: IDENTITY
   - Aggregation function: AGGREGATION
   - Any other operation: TRANSFORMATION

4. **Document transformation description:**
   - For IDENTITY: Can omit description
   - For AGGREGATION: "sum of amount", "count of orders", "mean of price"
   - For TRANSFORMATION: "price * quantity", "first_name + ' ' + last_name", "custom tier calculation"

**Example Analysis:**
```python
# Read data
customers = pd.read_csv('input/customers.csv')
orders = pd.read_csv('input/orders.csv')

# Transform
merged = customers.merge(orders, on='customer_id')
merged['full_name'] = merged['first_name'] + ' ' + merged['last_name']
summary = merged.groupby(['customer_id', 'full_name']).agg({
    'order_id': 'count',
    'amount': 'sum'
}).reset_index()
summary.columns = ['customer_id', 'full_name', 'order_count', 'total_spent']

# Calculate tier
summary['tier'] = summary['total_spent'].apply(
    lambda x: 'Gold' if x > 10000 else 'Silver' if x > 5000 else 'Bronze'
)

# Write
summary.to_csv('output/customer_summary.csv', index=False)
```

**Column Mappings:**
- `customers.customer_id` → `customer_id` (IDENTITY)
- `customers.first_name` + `customers.last_name` → `full_name` (TRANSFORMATION: "first_name + ' ' + last_name")
- `orders.order_id` → `order_count` (AGGREGATION: "count of order_id")
- `orders.amount` → `total_spent` (AGGREGATION: "sum of amount")
- `total_spent` → `tier` (TRANSFORMATION: "tier calculation based on total_spent")

## What is NOT Lineage

### Configuration and Setup
```python
# NOT lineage - configuration
import pandas as pd
import numpy as np
pd.set_option('display.max_columns', None)

# NOT lineage - connection setup
from sqlalchemy import create_engine
engine = create_engine('postgresql://user:pass@host:5432/db')
```

### Logging and Debugging
```python
# NOT lineage - logging
import logging
logging.info('Processing started')
print(f'Processing {len(df)} records')

# NOT lineage - debugging
print(df.head())
print(df.info())
print(df.describe())
```

### Data Validation Without Movement
```python
# NOT lineage - validation only
assert df['amount'].min() >= 0, 'Negative amounts found'
if df['customer_id'].isnull().any():
    print('Warning: Null customer IDs found')

# NOT lineage - data quality checks
invalid_count = len(df[df['email'].str.contains('@') == False])
```

### Helper Functions Without Data Movement
```python
# NOT lineage - utility function
def format_currency(amount):
    return f'${amount:,.2f}'

# NOT lineage - validation function
def is_valid_email(email):
    return '@' in email and '.' in email
```

### Exception Handling
```python
# NOT lineage - error handling
try:
    df = pd.read_csv('data.csv')
except FileNotFoundError:
    print('File not found')
    df = pd.DataFrame()
```

### Comments and Documentation
```python
# NOT lineage - comments
"""
This script processes customer data
Author: John Doe
Date: 2024-01-15
"""
```

## Special Cases

### Functions That Perform ETL
Document the entire function as one JobEvent if it performs a complete read-transform-write operation:

```python
def process_customer_data():
    # This entire function is one JobEvent
    df = pd.read_csv('input/customers.csv')
    df['full_name'] = df['first_name'] + ' ' + df['last_name']
    df.to_csv('output/processed_customers.csv')
```

### Multiple Writes in One Script
Each write operation is a separate JobEvent:

```python
# JobEvent 1
df1 = pd.read_csv('input/orders.csv')
df1_filtered = df1[df1['status'] == 'completed']
df1_filtered.to_csv('output/completed_orders.csv')

# JobEvent 2
df2_summary = df1_filtered.groupby('region')['amount'].sum()
df2_summary.to_csv('output/regional_summary.csv')
```

### Intermediate DataFrames
In-memory DataFrames are NOT separate datasets unless they're written to persistent storage:

```python
# One JobEvent - intermediate DataFrames are part of transformation logic
df = pd.read_csv('input/data.csv')
temp1 = df[df['status'] == 'active']  # NOT a dataset
temp2 = temp1.groupby('region')['amount'].sum()  # NOT a dataset
temp2.to_csv('output/summary.csv')  # This is the output dataset
```

### API Calls
Document API calls that move data:

```python
# JobEvent - API read and file write
import requests
response = requests.get('https://api.example.com/customers')
data = response.json()
df = pd.DataFrame(data)
df.to_csv('output/api_customers.csv')
```

## Summary Checklist

When analyzing Python code for lineage:

- ✓ Identify each `read` operation (pd.read_*, spark.read.*)
- ✓ Identify each `write` operation (to_csv, to_sql, write.*)
- ✓ Track DataFrame transformations between read and write
- ✓ Map each output column to its source column(s)
- ✓ Classify transformations as IDENTITY, AGGREGATION, or TRANSFORMATION
- ✓ Document transformation descriptions for non-IDENTITY mappings
- ✓ Note indirect lineage (filtering, joins, sorting)
- ✓ Extract connection details from database operations
- ✗ Ignore imports and configuration
- ✗ Ignore logging and debugging statements
- ✗ Ignore validation without data movement
- ✗ Ignore helper functions that don't read/write data
- ✗ Ignore in-memory intermediate DataFrames (part of transformation logic)