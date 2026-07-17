# SQL Data Lineage Analysis Guide

## What is considered Context

Statements that set execution environment but don't move data. Context affects how subsequent data movements are interpreted.

## Context-Setting Statements

- `USE` - Database selection
- `SET` - Session variables and settings
- `DECLARE` - Variable declarations
- `CREATE SCHEMA` - Schema definitions
- `CREATE DATABASE` - Database definitions
- `SET SCHEMA` - Schema context changes
- Connection strings and database URLs
- Transaction control statements (`BEGIN`, `COMMIT`, `ROLLBACK`) - affect scope but don't move data
- `PREPARE` statements - define but don't execute

## Context Storage

```json
context = {
    "current_database": [
        {"line": 1, "value": "production_db"},
        {"line": 45, "value": "staging_db"}
    ],
    "current_schema": [
        {"line": 2, "value": "sales"},
        {"line": 50, "value": "marketing"}
    ],
    "session_variables": {
        "@start_date": [
            {"line": 5, "value": "2024-01-01"},
            {"line": 100, "value": "2024-06-01"}
        ],
        "@table_prefix": [
            {"line": 6, "value": "prod_"},
            {"line": 105, "value": "test_"}
        ]
    },
    "prepared_statements": {
        "insert_stmt": [
            {"line": 10, "value": "INSERT INTO customers..."}
        ]
    }
}
```

## Context handling Workflow

1. **Initialize** - Scan file start for initial context (USE statements, SET variables)
2. **Process line-by-line**:
   - If context statement → Update context, increment version
   - If data movement → Resolve references using current context
3. **Resolve** - Replace variables, apply current database/schema to unqualified table names

- **Don't assume static context** - Database/schema can change mid-script
- **Version context** - Track changes by referencing line numbers
- **Resolve all references** - Use context before generating lineage
- **Handle unqualified names** - Apply current database.schema to table names
- **Track session variables** - They may affect table names or query logic
- **Document context version** - Reference in lineage metadata

## What is Considered a Transformation

In SQL, a **transformation** is any statement that reads data from one or more sources and writes it to a destination, potentially modifying the data in the process.

### SQL Statements That Move Data (Transformations)

**Data Manipulation Language (DML):**
- `INSERT INTO ... SELECT` - Inserts data from query results
- `INSERT INTO ... VALUES` - Inserts literal data
- `UPDATE ... FROM` - Updates rows using data from other tables
- `DELETE ... USING` - Deletes rows based on other tables
- `MERGE` / `UPSERT` - Combines insert/update operations
- `REPLACE INTO` - MySQL-specific insert or replace
- `INSERT OVERWRITE` - Hive/Spark-specific overwrite operation

**Data Definition Language (DDL) with Data Movement:**
- `CREATE TABLE AS SELECT` (CTAS) - Creates table from query
- `CREATE VIEW` - Creates view definition (logical transformation)
- `CREATE MATERIALIZED VIEW` - Creates physical view with data
- `SELECT INTO` - Creates new table from query (SQL Server, PostgreSQL)
- `CREATE TABLE ... LIKE ... AS SELECT` - Creates table structure and populates

**Stored Procedures and Functions:**
- `CALL procedure_name()` - Executes stored procedure that moves data
- `EXECUTE function_name()` - Executes function that moves data
- Dynamic SQL execution (`EXECUTE IMMEDIATE`, `sp_executesql`)

**Bulk Operations:**
- `COPY` - PostgreSQL bulk load
- `LOAD DATA` - MySQL bulk load
- `BULK INSERT` - SQL Server bulk load
- `INSERT INTO ... FROM file` - File-based inserts

**Database-Specific Operations:**
- `TRUNCATE ... INSERT` - Clear and reload pattern
- `CREATE EXTERNAL TABLE` - Hive/Spark external table creation
- `REFRESH MATERIALIZED VIEW` - Reloads materialized view data
- `ALTER TABLE ... EXCHANGE PARTITION` - Partition swapping

### Transformation Granularity for JobEvents

**One JobEvent per:**
- Single `INSERT INTO ... SELECT` statement
- Single `CREATE TABLE AS SELECT` statement
- Single `CREATE VIEW` statement
- Single `CREATE MATERIALIZED VIEW` statement
- Single `UPDATE` statement with data from other tables
- Single `MERGE` statement
- Single stored procedure execution that moves data
- Single function execution that moves/transforms data
- Single bulk load operation
- Single dynamic SQL execution that moves data

**NOT separate JobEvents:**
- Subqueries within a larger query (part of the parent query's transformation)
- Common Table Expressions (CTEs) - part of the main query
- Multiple INSERT statements in a transaction (each is separate unless part of stored procedure)
- Window functions within a query (part of transformation logic)
- CASE statements and conditional logic (part of transformation logic)


## What is Considered a Dataset

### Source Datasets (Inputs)
- Tables in FROM clause: `FROM sales.customers`
- Tables in JOIN clauses: `JOIN sales.orders ON ...`
- Tables in subqueries: `FROM (SELECT * FROM sales.products)`
- Tables in CTEs: `WITH cte AS (SELECT * FROM sales.items)`
- Views referenced in queries: `FROM sales.customer_view`
- Materialized views: `FROM sales.summary_mv`
- External tables: `FROM external_schema.data_file`
- Temporary tables: `FROM #temp_table` or `FROM temp.staging_data`
- Tables in MERGE source: `USING sales.updates`
- Tables in UPDATE FROM clause: `FROM sales.reference_data`
- Tables in DELETE USING clause: `USING sales.archive_list`

### Output Datasets
- Table created by CREATE TABLE AS: `CREATE TABLE sales.summary AS SELECT ...`
- Table populated by INSERT INTO: `INSERT INTO sales.customers ...`
- Table modified by UPDATE: `UPDATE sales.orders SET ...`
- Table modified by MERGE: `MERGE INTO sales.inventory ...`
- View created: `CREATE VIEW sales.active_customers AS ...`
- Materialized view created: `CREATE MATERIALIZED VIEW sales.daily_summary AS ...`
- Temporary table created: `CREATE TEMP TABLE staging_data AS ...`
- Table created by SELECT INTO: `SELECT * INTO sales.backup FROM sales.customers`
- Table modified by DELETE: `DELETE FROM sales.archive WHERE ...`

### NOT Datasets
- Temporary result sets from subqueries (unless materialized)
- CTEs (Common Table Expressions) - they're part of the query, not separate datasets
- Variables holding scalar values
- Cursor definitions
- Table variables (unless they persist beyond the query)
- System tables/views used for metadata only
- Information schema tables (unless explicitly queried for data lineage)
