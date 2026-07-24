# Snowflake Snowpark Notebooks and Workbooks Data Lineage Analysis Guide

## What is considered Context

Statements that set execution environment but don't move data. Context affects how subsequent data movements are interpreted.

## Context-Setting Statements

- `USE DATABASE` - Database selection
- `USE SCHEMA` - Schema selection
- `USE WAREHOUSE` - Warehouse selection
- `USE ROLE` - Role context changes
- Session variables via `session.sql()` with SET commands
- Snowpark session configuration (`session.builder.configs()`)
- Import statements - Python library imports
- Variable assignments - Python variables holding connection info or table names
- Function/UDF definitions - User-defined functions (context for transformations)

## Context Storage

```json
context = {
    "current_database": [
        {"cell": 1, "value": "PRODUCTION_DB"},
        {"cell": 5, "value": "STAGING_DB"}
    ],
    "current_schema": [
        {"cell": 1, "value": "SALES"},
        {"cell": 6, "value": "MARKETING"}
    ],
    "current_warehouse": [
        {"cell": 1, "value": "COMPUTE_WH"},
        {"cell": 8, "value": "TRANSFORM_WH"}
    ],
    "session_variables": {
        "start_date": [
            {"cell": 2, "value": "2024-01-01"},
            {"cell": 10, "value": "2024-06-01"}
        ]
    },
    "python_variables": {
        "table_name": [
            {"cell": 3, "value": "customers"},
            {"cell": 12, "value": "customers_v2"}
        ]
    }
}
```

## Context handling Workflow

1. **Initialize** - Scan notebook start for initial context (USE statements, session config)
2. **Process cell-by-cell**:
   - If context statement → Update context, track cell number
   - If data movement → Resolve references using current context
3. **Resolve** - Replace Python variables, apply current database.schema to unqualified table names

- **Don't assume static context** - Database/schema can change between cells
- **Version context** - Track changes by referencing cell numbers
- **Resolve all references** - Use context before generating lineage
- **Handle Python variables** - Track variables that hold table names or paths
- **Document context version** - Reference in lineage metadata

## What is Considered a Transformation

In Snowflake Snowpark Notebooks/Workbooks, a **transformation** is any operation that reads data from one or more sources and writes it to a destination. Each query cell that produces output is a separate transformation.

### Snowpark Operations That Move Data (Transformations)

**DataFrame Operations with Writes:**
- `df.write.save_as_table()` - Writes DataFrame to table
- `df.write.mode("overwrite").save_as_table()` - Overwrites table
- `df.write.mode("append").save_as_table()` - Appends to table
- `table.merge()` - Merges data into target table
- `table.update()` - Updates rows in table
- `table.delete()` - Deletes rows from table

**SQL Execution via session.sql():**
- `session.sql("CREATE TABLE ... AS SELECT")` - Creates table from query
- `session.sql("INSERT INTO ... SELECT")` - Inserts data from query
- `session.sql("UPDATE ... FROM")` - Updates using other tables
- `session.sql("MERGE INTO ...")` - Merge operation
- `session.sql("CREATE VIEW ...")` - Creates view definition
- `session.sql("CREATE MATERIALIZED VIEW ...")` - Creates materialized view

**Data Loading:**
- `session.read.csv()` followed by write - Loads CSV data
- `session.read.parquet()` followed by write - Loads Parquet data
- `session.read.json()` followed by write - Loads JSON data
- `session.read.table()` followed by transformations and write - Table-to-table transformation
- `COPY INTO` via session.sql() - Bulk load from stage

**Stored Procedures:**
- `session.call()` - Executes stored procedure that moves data
- Stored procedure deployment from notebook - Creates procedure that moves data

### Transformation Granularity for JobEvents

**One JobEvent per:**
- Single cell executing SQL that creates/modifies a table
- Single cell with DataFrame write operation
- Single cell with merge/update/delete operation
- Single stored procedure call that moves data
- Single COPY INTO operation
- Single cell that produces a result set (for analysis/visualization)
- Single cell that creates a chart/plot from data

**NOT separate JobEvents:**
- DataFrame transformations without write (`.select()`, `.filter()`, `.join()` without `.write`)
- Intermediate DataFrames assigned to variables (part of larger transformation)
- Multiple operations in same cell that write to same table
- Helper function definitions (context, not transformations)

## What is Considered a Dataset

### Source Datasets (Inputs)

- Tables read via `session.table()`: `session.table("customers")`
- Tables in SQL FROM clause: `session.sql("SELECT * FROM orders")`
- Tables in DataFrame joins: `df1.join(df2, ...)`
- Views referenced: `session.table("customer_view")`
- Materialized views: `session.table("summary_mv")`
- External tables: `session.table("external_data")`
- Stages with files: `@my_stage/data.csv`
- Tables in MERGE source: `USING updates`
- Tables in UPDATE FROM: `FROM reference_data`
- CSV/Parquet/JSON files: `session.read.csv("@stage/file.csv")`

### Output Datasets

- Tables created by `save_as_table()`: `df.write.save_as_table("output_table")`
- Tables created by CREATE TABLE AS: `CREATE TABLE summary AS SELECT ...`
- Tables modified by INSERT: `INSERT INTO customers ...`
- Tables modified by UPDATE: `UPDATE orders SET ...`
- Tables modified by MERGE: `MERGE INTO inventory ...`
- Tables modified by DELETE: `DELETE FROM archive ...`
- Views created: `CREATE VIEW active_customers AS ...`
- Materialized views created: `CREATE MATERIALIZED VIEW daily_summary AS ...`
- Result sets displayed in notebook (for visualization/analysis)
- Charts/plots generated from data
- Data written to stages: `COPY INTO @stage/output.csv`

### NOT Datasets

- Intermediate DataFrames not written to storage
- Python variables holding scalar values
- Temporary result sets from `.show()` or `.collect()` (unless explicitly saved)
- UDF definitions
- Session configuration objects
- Metadata queries (SHOW TABLES, DESCRIBE, etc.)