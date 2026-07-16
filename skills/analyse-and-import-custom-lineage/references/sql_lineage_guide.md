# SQL Data Lineage Analysis Guide

## What is Considered a Transformation

In SQL, a **transformation** is any operation that reads data from one or more sources and writes it to a destination, potentially modifying the data in the process.

### Transformation Granularity for JobEvents

**One JobEvent per:**
- Single `INSERT INTO ... SELECT` statement
- Single `CREATE TABLE AS SELECT` statement
- Single `UPDATE` statement with data from other tables
- Single `MERGE` statement
- Single stored procedure execution
- Single function execution that moves/transforms data
- Single view creation (if materializing data)

**NOT separate JobEvents:**
- Multiple statements within a single transaction (document as one job with multiple inputs/outputs)
- Subqueries within a larger query (part of the parent query's transformation)
- Common Table Expressions (CTEs) - part of the main query

### Examples

**✓ CORRECT - One JobEvent:**
```sql
INSERT INTO sales_summary (region, total_sales, order_count)
SELECT region, SUM(amount), COUNT(*)
FROM orders
WHERE order_date >= '2024-01-01'
GROUP BY region;
```

**✓ CORRECT - One JobEvent per statement:**
```sql
-- JobEvent 1
CREATE TABLE temp_filtered AS
SELECT * FROM orders WHERE status = 'completed';

-- JobEvent 2
INSERT INTO sales_summary
SELECT region, SUM(amount) FROM temp_filtered GROUP BY region;
```

## What is Considered a Dataset

### Source Datasets (Inputs)
- Tables referenced in `FROM` clause
- Tables in `JOIN` clauses
- Tables in subqueries that provide data
- Views (if they represent persistent data sources)
- External tables
- Temporary tables (if they persist data between operations)

### Output Datasets
- Target table in `INSERT INTO`
- Table created by `CREATE TABLE AS`
- Table updated by `UPDATE` statement
- Table modified by `MERGE` statement
- Materialized views

### NOT Datasets
- Variables or parameters
- Inline values (`VALUES (1, 2, 3)`)
- System tables used for metadata only
- CTEs that don't persist (part of query logic)

## Understanding Lineage and Transformation Logic

### How Data Reading Looks Like

**Basic SELECT:**
```sql
SELECT customer_id, customer_name, email
FROM customers
WHERE status = 'active';
```
- **Input Dataset:** `customers` table
- **Columns Read:** `customer_id`, `customer_name`, `email`, `status`

**JOINs:**
```sql
SELECT o.order_id, c.customer_name, o.amount
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id;
```
- **Input Datasets:** `orders`, `customers`
- **Columns Read:** `orders.order_id`, `orders.amount`, `orders.customer_id`, `customers.customer_name`, `customers.customer_id`

**Subqueries:**
```sql
SELECT * FROM orders
WHERE customer_id IN (SELECT customer_id FROM vip_customers);
```
- **Input Datasets:** `orders`, `vip_customers`

### How Data Writing Looks Like

**INSERT INTO ... SELECT:**
```sql
INSERT INTO sales_summary (region, total_sales)
SELECT region, SUM(amount)
FROM orders
GROUP BY region;
```
- **Output Dataset:** `sales_summary`
- **Columns Written:** `region`, `total_sales`

**CREATE TABLE AS SELECT:**
```sql
CREATE TABLE customer_orders AS
SELECT c.customer_id, c.customer_name, COUNT(o.order_id) as order_count
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name;
```
- **Output Dataset:** `customer_orders`
- **Columns Written:** `customer_id`, `customer_name`, `order_count`

**UPDATE:**
```sql
UPDATE customers c
SET total_spent = (
    SELECT SUM(amount) FROM orders o WHERE o.customer_id = c.customer_id
)
WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.customer_id);
```
- **Output Dataset:** `customers`
- **Input Dataset:** `orders`
- **Column Written:** `total_spent`

### How to Identify Transformations

#### Direct Transformations (Column values flow to output)

**1. Column Calculations:**
```sql
SELECT 
    price * quantity AS total_amount,
    price * quantity * 0.1 AS tax_amount
FROM order_items;
```
- **Transformation Type:** TRANSFORMATION
- **Lineage:** `price` + `quantity` → `total_amount` (calculation: price * quantity)
- **Lineage:** `price` + `quantity` → `tax_amount` (calculation: price * quantity * 0.1)

**2. Aggregations:**
```sql
SELECT 
    region,
    SUM(amount) AS total_sales,
    COUNT(*) AS order_count,
    AVG(amount) AS avg_order_value
FROM orders
GROUP BY region;
```
- **Transformation Type:** AGGREGATION
- **Lineage:** `region` → `region` (IDENTITY - distinct values flow through)
- **Lineage:** `amount` → `total_sales` (AGGREGATION: SUM)
- **Lineage:** (all rows) → `order_count` (AGGREGATION: COUNT)
- **Lineage:** `amount` → `avg_order_value` (AGGREGATION: AVG)

**3. String Manipulations:**
```sql
SELECT 
    UPPER(customer_name) AS customer_name_upper,
    CONCAT(first_name, ' ', last_name) AS full_name,
    SUBSTRING(email, 1, POSITION('@' IN email) - 1) AS email_username
FROM customers;
```
- **Transformation Type:** TRANSFORMATION
- **Lineage:** `customer_name` → `customer_name_upper` (UPPER function)
- **Lineage:** `first_name` + `last_name` → `full_name` (concatenation)
- **Lineage:** `email` → `email_username` (substring extraction)

**4. CASE Statements:**
```sql
SELECT 
    customer_id,
    CASE 
        WHEN total_spent > 10000 THEN 'Gold'
        WHEN total_spent > 5000 THEN 'Silver'
        ELSE 'Bronze'
    END AS customer_tier
FROM customers;
```
- **Transformation Type:** TRANSFORMATION
- **Lineage:** `total_spent` → `customer_tier` (CASE logic)

**5. Column Renames:**
```sql
SELECT 
    customer_id AS cust_id,
    customer_name AS name
FROM customers;
```
- **Transformation Type:** IDENTITY
- **Lineage:** `customer_id` → `cust_id` (rename)
- **Lineage:** `customer_name` → `name` (rename)

#### Indirect Transformations (Column influences result but values don't flow)

**1. WHERE Clause (Filtering):**
```sql
SELECT customer_id, customer_name
FROM customers
WHERE status = 'active' AND region = 'US';
```
- **INDIRECT Lineage:** `status` influences which rows are included
- **INDIRECT Lineage:** `region` influences which rows are included
- **DIRECT Lineage:** `customer_id` → `customer_id` (IDENTITY)
- **DIRECT Lineage:** `customer_name` → `customer_name` (IDENTITY)

**2. JOIN Conditions:**
```sql
SELECT o.order_id, c.customer_name
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id;
```
- **INDIRECT Lineage:** `orders.customer_id` and `customers.customer_id` determine matching
- **DIRECT Lineage:** `orders.order_id` → `order_id` (IDENTITY)
- **DIRECT Lineage:** `customers.customer_name` → `customer_name` (IDENTITY)

**3. HAVING Clause:**
```sql
SELECT region, SUM(amount) AS total_sales
FROM orders
GROUP BY region
HAVING SUM(amount) > 100000;
```
- **INDIRECT Lineage:** `amount` in HAVING clause filters aggregated results
- **DIRECT Lineage:** `region` → `region` (IDENTITY)
- **DIRECT Lineage:** `amount` → `total_sales` (AGGREGATION)

**4. ORDER BY:**
```sql
SELECT customer_id, customer_name
FROM customers
ORDER BY last_purchase_date DESC;
```
- **INDIRECT Lineage:** `last_purchase_date` affects row ordering
- **DIRECT Lineage:** `customer_id` → `customer_id` (IDENTITY)
- **DIRECT Lineage:** `customer_name` → `customer_name` (IDENTITY)

### How to Identify Column Mappings

**Step-by-step approach:**

1. **Identify output columns** from the SELECT list or INSERT column list
2. **For each output column, trace back to source columns:**
   - Direct references: `SELECT customer_id` → source is `customer_id`
   - Calculations: `SELECT price * quantity AS total` → sources are `price` and `quantity`
   - Aggregations: `SELECT SUM(amount)` → source is `amount`
   - Functions: `SELECT UPPER(name)` → source is `name`

3. **Determine transformation type:**
   - No change: IDENTITY
   - Aggregation function: AGGREGATION
   - Any other operation: TRANSFORMATION

4. **Document transformation description:**
   - For IDENTITY: Can omit description
   - For AGGREGATION: "SUM of amount", "COUNT of orders"
   - For TRANSFORMATION: "price * quantity", "UPPER(customer_name)", "CONCAT(first_name, ' ', last_name)"

**Example Analysis:**
```sql
INSERT INTO customer_summary (customer_id, full_name, total_orders, total_spent, tier)
SELECT 
    c.customer_id,
    CONCAT(c.first_name, ' ', c.last_name) AS full_name,
    COUNT(o.order_id) AS total_orders,
    SUM(o.amount) AS total_spent,
    CASE 
        WHEN SUM(o.amount) > 10000 THEN 'Gold'
        ELSE 'Silver'
    END AS tier
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.first_name, c.last_name;
```

**Column Mappings:**
- `customers.customer_id` → `customer_id` (IDENTITY)
- `customers.first_name` + `customers.last_name` → `full_name` (TRANSFORMATION: "CONCAT(first_name, ' ', last_name)")
- `orders.order_id` → `total_orders` (AGGREGATION: "COUNT of order_id")
- `orders.amount` → `total_spent` (AGGREGATION: "SUM of amount")
- `orders.amount` → `tier` (TRANSFORMATION: "CASE statement based on SUM(amount)")

## What is NOT Lineage

### Configuration and Metadata Operations
```sql
-- NOT lineage - just setting session parameters
SET search_path TO public;
SET timezone TO 'UTC';

-- NOT lineage - metadata query
SELECT table_name FROM information_schema.tables;

-- NOT lineage - schema definition without data
CREATE TABLE customers (
    customer_id INT PRIMARY KEY,
    customer_name VARCHAR(100)
);
```

### Access Control
```sql
-- NOT lineage - permission management
GRANT SELECT ON customers TO analyst_role;
REVOKE INSERT ON orders FROM public;
```

### Transaction Control
```sql
-- NOT lineage - transaction boundaries
BEGIN TRANSACTION;
COMMIT;
ROLLBACK;
```

### Comments and Documentation
```sql
-- NOT lineage - just comments
-- This query calculates customer metrics
/* 
 * Author: John Doe
 * Date: 2024-01-15
 */
```

### Index and Performance Operations
```sql
-- NOT lineage - performance optimization
CREATE INDEX idx_customer_email ON customers(email);
ANALYZE customers;
VACUUM orders;
```

### Data Validation Without Movement
```sql
-- NOT lineage - validation only, no data movement
SELECT COUNT(*) FROM orders WHERE amount < 0; -- Just checking for invalid data
```

## Special Cases

### Stored Procedures
Document each data movement operation within the procedure as a separate JobEvent:

```sql
CREATE PROCEDURE process_daily_sales()
BEGIN
    -- JobEvent 1
    INSERT INTO temp_sales
    SELECT * FROM orders WHERE order_date = CURRENT_DATE;
    
    -- JobEvent 2
    INSERT INTO sales_summary
    SELECT region, SUM(amount) FROM temp_sales GROUP BY region;
    
    -- JobEvent 3
    DELETE FROM temp_sales;
END;
```

### Temporary Tables
- If temporary table is used to pass data between operations: Document as a dataset
- If temporary table is only used within a single query: Part of query logic, not a separate dataset

### Views
- **Materialized Views:** Document as output datasets (data is physically stored)
- **Regular Views:** Generally not documented as separate jobs (they're query definitions, not data movement)
- **Exception:** If a view is the primary interface to data and represents a logical transformation layer, it may be documented

## Summary Checklist

When analyzing SQL code for lineage:

- ✓ Identify each INSERT, CREATE TABLE AS, UPDATE, MERGE statement
- ✓ Document stored procedures and functions that move data
- ✓ Trace all tables in FROM and JOIN clauses as inputs
- ✓ Identify target tables as outputs
- ✓ Map each output column to its source column(s)
- ✓ Classify transformations as IDENTITY, AGGREGATION, or TRANSFORMATION
- ✓ Document transformation descriptions for non-IDENTITY mappings
- ✓ Note indirect lineage (WHERE, JOIN conditions, HAVING, ORDER BY)
- ✗ Ignore DDL without data movement
- ✗ Ignore access control statements
- ✗ Ignore transaction control
- ✗ Ignore comments and metadata queries