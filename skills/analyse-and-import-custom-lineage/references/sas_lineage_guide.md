# SAS Data Lineage Analysis Guide

## What is Considered a Transformation

In SAS, a **transformation** is any operation that reads data from one or more sources and writes it to a destination, potentially modifying the data in the process. SAS uses DATA steps and PROC steps for data manipulation.

### Transformation Granularity for JobEvents

**One JobEvent per:**
- Single DATA step that creates an output dataset
- Single PROC SQL statement (INSERT, CREATE TABLE AS)
- Single PROC step that creates output (PROC SORT with OUT=, PROC MEANS with OUTPUT OUT=)
- Single PROC TRANSPOSE
- Single PROC APPEND
- Single stored process execution that moves data

**NOT separate JobEvents:**
- Multiple SET statements within a single DATA step (multiple inputs to one job)
- BY-group processing within a DATA step (part of transformation logic)
- Multiple OUTPUT statements to the same dataset (part of single DATA step)
- Macro expansions (document the expanded code)

### Examples

**✓ CORRECT - One JobEvent:**
```sas
DATA work.customer_summary;
    SET work.customers;
    full_name = CATX(' ', first_name, last_name);
    total_amount = price * quantity;
RUN;
```

**✓ CORRECT - One JobEvent per DATA/PROC step:**
```sas
/* JobEvent 1 */
DATA work.filtered_orders;
    SET work.orders;
    WHERE status = 'completed';
RUN;

/* JobEvent 2 */
PROC SQL;
    CREATE TABLE work.sales_summary AS
    SELECT region, SUM(amount) AS total_sales
    FROM work.filtered_orders
    GROUP BY region;
QUIT;
```

## What is Considered a Dataset

### Source Datasets (Inputs)
- SAS datasets in SET statement: `SET work.customers;`
- SAS datasets in MERGE statement: `MERGE work.orders work.customers;`
- SAS datasets in UPDATE statement: `UPDATE work.master work.transactions;`
- Tables in PROC SQL FROM clause: `FROM work.orders`
- External files: `INFILE 'path/to/file.csv';`
- Database tables via LIBNAME: `SET mylib.customers;`

### Output Datasets
- Dataset created by DATA step: `DATA work.output;`
- Table created by PROC SQL: `CREATE TABLE work.summary AS`
- Dataset created by PROC with OUT= option: `PROC SORT DATA=work.input OUT=work.sorted;`
- Files written: `FILE 'path/to/output.csv';`
- Database tables via LIBNAME: `DATA mylib.customers;`

### NOT Datasets
- Temporary variables within DATA step
- Macro variables
- Format catalogs
- Index files (unless explicitly created as separate operation)
- _NULL_ dataset (used for processing without output)

## Understanding Lineage and Transformation Logic

### How Data Reading Looks Like

**DATA Step - SET Statement:**
```sas
DATA work.output;
    SET work.customers;
    /* All columns from customers are available */
RUN;
```
- **Input Dataset:** `work.customers`
- **Columns Read:** All columns in the dataset

**DATA Step - Multiple Inputs:**
```sas
DATA work.combined;
    SET work.customers work.prospects;
    /* Concatenates both datasets */
RUN;
```
- **Input Datasets:** `work.customers`, `work.prospects`

**DATA Step - MERGE:**
```sas
DATA work.customer_orders;
    MERGE work.customers (IN=c) 
          work.orders (IN=o);
    BY customer_id;
    IF c AND o;  /* Inner join */
RUN;
```
- **Input Datasets:** `work.customers`, `work.orders`
- **Join Key:** `customer_id`

**PROC SQL - SELECT:**
```sas
PROC SQL;
    SELECT customer_id, customer_name, email
    FROM work.customers
    WHERE status = 'active';
QUIT;
```
- **Input Dataset:** `work.customers`
- **Columns Read:** `customer_id`, `customer_name`, `email`, `status`

**External File Input:**
```sas
DATA work.imported;
    INFILE 'C:\data\customers.csv' DLM=',' FIRSTOBS=2;
    INPUT customer_id customer_name $ email $;
RUN;
```
- **Input Dataset:** File path `C:\data\customers.csv`

### How Data Writing Looks Like

**DATA Step Output:**
```sas
DATA work.customer_summary;
    SET work.customers;
    full_name = CATX(' ', first_name, last_name);
RUN;
```
- **Output Dataset:** `work.customer_summary`
- **Columns Written:** All columns from input plus `full_name`

**PROC SQL - CREATE TABLE:**
```sas
PROC SQL;
    CREATE TABLE work.sales_summary AS
    SELECT region, SUM(amount) AS total_sales
    FROM work.orders
    GROUP BY region;
QUIT;
```
- **Output Dataset:** `work.sales_summary`
- **Columns Written:** `region`, `total_sales`

**PROC SQL - INSERT INTO:**
```sas
PROC SQL;
    INSERT INTO work.customer_archive
    SELECT * FROM work.customers
    WHERE last_update < '01JAN2020'd;
QUIT;
```
- **Output Dataset:** `work.customer_archive`

**External File Output:**
```sas
DATA _NULL_;
    SET work.customers;
    FILE 'C:\output\customers.csv' DLM=',';
    PUT customer_id customer_name email;
RUN;
```
- **Output Dataset:** File path `C:\output\customers.csv`

### How to Identify Transformations

#### Direct Transformations (Column values flow to output)

**1. Column Calculations:**
```sas
DATA work.orders_with_totals;
    SET work.orders;
    total_amount = price * quantity;
    tax_amount = total_amount * 0.1;
    discount_price = price * (1 - discount_rate);
RUN;
```
- **Transformation Type:** TRANSFORMATION
- **Lineage:** `price` + `quantity` → `total_amount` (calculation: price * quantity)
- **Lineage:** `total_amount` → `tax_amount` (calculation: total_amount * 0.1)
- **Lineage:** `price` + `discount_rate` → `discount_price` (calculation: price * (1 - discount_rate))

**2. String Operations:**
```sas
DATA work.customers_formatted;
    SET work.customers;
    full_name = CATX(' ', first_name, last_name);
    email_domain = SCAN(email, 2, '@');
    upper_name = UPCASE(customer_name);
RUN;
```
- **Transformation Type:** TRANSFORMATION
- **Lineage:** `first_name` + `last_name` → `full_name` (CATX concatenation)
- **Lineage:** `email` → `email_domain` (SCAN to extract domain)
- **Lineage:** `customer_name` → `upper_name` (UPCASE function)

**3. Aggregations (PROC SQL):**
```sas
PROC SQL;
    CREATE TABLE work.regional_summary AS
    SELECT 
        region,
        SUM(amount) AS total_sales,
        COUNT(*) AS order_count,
        AVG(amount) AS avg_order_value
    FROM work.orders
    GROUP BY region;
QUIT;
```
- **Transformation Type:** AGGREGATION
- **Lineage:** `region` → `region` (IDENTITY - grouping key)
- **Lineage:** `amount` → `total_sales` (AGGREGATION: SUM)
- **Lineage:** (all rows) → `order_count` (AGGREGATION: COUNT)
- **Lineage:** `amount` → `avg_order_value` (AGGREGATION: AVG)

**4. Aggregations (PROC MEANS):**
```sas
PROC MEANS DATA=work.orders NOPRINT;
    CLASS region;
    VAR amount;
    OUTPUT OUT=work.summary 
           SUM=total_sales 
           MEAN=avg_sales 
           N=order_count;
RUN;
```
- **Transformation Type:** AGGREGATION
- **Lineage:** `region` → `region` (IDENTITY - classification variable)
- **Lineage:** `amount` → `total_sales` (AGGREGATION: SUM)
- **Lineage:** `amount` → `avg_sales` (AGGREGATION: MEAN)
- **Lineage:** `amount` → `order_count` (AGGREGATION: N)

**5. Column Renames:**
```sas
DATA work.customers_renamed;
    SET work.customers (RENAME=(customer_id=cust_id customer_name=name));
RUN;
```
- **Transformation Type:** IDENTITY
- **Lineage:** `customer_id` → `cust_id` (rename)
- **Lineage:** `customer_name` → `name` (rename)

**6. Conditional Logic:**
```sas
DATA work.customers_with_tier;
    SET work.customers;
    IF total_spent > 10000 THEN customer_tier = 'Gold';
    ELSE IF total_spent > 5000 THEN customer_tier = 'Silver';
    ELSE customer_tier = 'Bronze';
RUN;
```
- **Transformation Type:** TRANSFORMATION
- **Lineage:** `total_spent` → `customer_tier` (IF-THEN-ELSE logic)

**7. BY-Group Processing:**
```sas
DATA work.customer_totals;
    SET work.orders;
    BY customer_id;
    
    RETAIN running_total 0;
    
    IF FIRST.customer_id THEN running_total = 0;
    running_total + amount;
    
    IF LAST.customer_id THEN OUTPUT;
    
    KEEP customer_id running_total;
RUN;
```
- **Transformation Type:** AGGREGATION
- **Lineage:** `customer_id` → `customer_id` (IDENTITY - BY variable)
- **Lineage:** `amount` → `running_total` (AGGREGATION: cumulative sum by group)

#### Indirect Transformations (Column influences result but values don't flow)

**1. WHERE Clause (Filtering):**
```sas
DATA work.active_customers;
    SET work.customers;
    WHERE status = 'active' AND region = 'US';
RUN;
```
- **INDIRECT Lineage:** `status` influences which rows are included
- **INDIRECT Lineage:** `region` influences which rows are included
- **DIRECT Lineage:** All other columns flow through as IDENTITY

**2. IF Statement (Subsetting):**
```sas
DATA work.high_value_orders;
    SET work.orders;
    IF amount > 1000;
RUN;
```
- **INDIRECT Lineage:** `amount` influences which rows are included
- **DIRECT Lineage:** All columns flow through as IDENTITY

**3. MERGE with BY (Join Condition):**
```sas
DATA work.customer_orders;
    MERGE work.customers (IN=c) work.orders (IN=o);
    BY customer_id;
    IF c AND o;
RUN;
```
- **INDIRECT Lineage:** `customer_id` determines matching
- **DIRECT Lineage:** All selected columns from both datasets

**4. PROC SORT (Ordering):**
```sas
PROC SORT DATA=work.customers OUT=work.customers_sorted;
    BY region DESCENDING last_purchase_date;
RUN;
```
- **INDIRECT Lineage:** `region` and `last_purchase_date` affect row ordering
- **DIRECT Lineage:** All columns flow through as IDENTITY

### How to Identify Column Mappings

**Step-by-step approach:**

1. **Identify input datasets** from SET, MERGE, UPDATE, or FROM clauses
2. **Identify output dataset** from DATA statement or CREATE TABLE
3. **For each output column, trace back to source:**
   - Direct reference: Column exists in input with same name
   - Assignment: `new_col = old_col;` or `new_col = expression;`
   - Calculation: `total = price * quantity;`
   - Function: `upper_name = UPCASE(name);`
   - Aggregation: `SUM(amount)`, `COUNT(*)`, `MEAN(price)`

4. **Determine transformation type:**
   - No change or rename: IDENTITY
   - Aggregation function: AGGREGATION
   - Any other operation: TRANSFORMATION

5. **Document transformation description:**
   - For IDENTITY: Can omit description
   - For AGGREGATION: "SUM of amount", "COUNT of orders", "MEAN of price"
   - For TRANSFORMATION: "price * quantity", "CATX(' ', first_name, last_name)", "IF-THEN-ELSE tier logic"

**Example Analysis:**
```sas
/* Read data */
DATA work.merged;
    MERGE work.customers (IN=c) work.orders (IN=o);
    BY customer_id;
    IF c AND o;
RUN;

/* Transform */
DATA work.customer_summary;
    SET work.merged;
    BY customer_id;
    
    RETAIN order_count 0 total_spent 0;
    
    IF FIRST.customer_id THEN DO;
        order_count = 0;
        total_spent = 0;
    END;
    
    full_name = CATX(' ', first_name, last_name);
    order_count + 1;
    total_spent + amount;
    
    IF LAST.customer_id THEN DO;
        IF total_spent > 10000 THEN tier = 'Gold';
        ELSE IF total_spent > 5000 THEN tier = 'Silver';
        ELSE tier = 'Bronze';
        OUTPUT;
    END;
    
    KEEP customer_id full_name order_count total_spent tier;
RUN;
```

**Column Mappings:**
- `customers.customer_id` → `customer_id` (IDENTITY)
- `customers.first_name` + `customers.last_name` → `full_name` (TRANSFORMATION: "CATX(' ', first_name, last_name)")
- `orders.order_id` → `order_count` (AGGREGATION: "COUNT by customer_id")
- `orders.amount` → `total_spent` (AGGREGATION: "SUM by customer_id")
- `total_spent` → `tier` (TRANSFORMATION: "IF-THEN-ELSE tier calculation")

## What is NOT Lineage

### Configuration and Options
```sas
/* NOT lineage - SAS options */
OPTIONS COMPRESS=YES REUSE=YES;
OPTIONS MPRINT MLOGIC SYMBOLGEN;

/* NOT lineage - LIBNAME assignment */
LIBNAME mylib 'C:\data\sas';
```

### Logging and Debugging
```sas
/* NOT lineage - PUT statements for logging */
DATA _NULL_;
    SET work.customers;
    PUT 'Processing customer: ' customer_id=;
RUN;

/* NOT lineage - PROC PRINT for viewing */
PROC PRINT DATA=work.customers (OBS=10);
RUN;

/* NOT lineage - PROC CONTENTS for metadata */
PROC CONTENTS DATA=work.customers;
RUN;
```

### Data Validation Without Movement
```sas
/* NOT lineage - validation only */
PROC SQL;
    SELECT COUNT(*) AS invalid_count
    FROM work.orders
    WHERE amount < 0;
QUIT;

/* NOT lineage - frequency check */
PROC FREQ DATA=work.customers;
    TABLES status;
RUN;
```

### Macro Definitions
```sas
/* NOT lineage - macro definition */
%MACRO process_data(input_ds, output_ds);
    DATA &output_ds;
        SET &input_ds;
        /* transformation logic */
    RUN;
%MEND;

/* Document the expanded macro call as lineage */
```

### Format and Label Definitions
```sas
/* NOT lineage - format definition */
PROC FORMAT;
    VALUE tier_fmt
        1 = 'Bronze'
        2 = 'Silver'
        3 = 'Gold';
RUN;

/* NOT lineage - label assignment */
DATA work.customers;
    SET work.customers;
    LABEL customer_id = 'Customer ID'
          customer_name = 'Customer Name';
RUN;
```

### Index Creation
```sas
/* NOT lineage - index creation */
PROC DATASETS LIBRARY=work NOLIST;
    MODIFY customers;
    INDEX CREATE customer_id;
QUIT;
```

## Special Cases

### Stored Processes
Document each data movement operation within the stored process as a separate JobEvent:

```sas
/* Stored Process: process_daily_sales */

/* JobEvent 1 */
DATA work.temp_sales;
    SET work.orders;
    WHERE order_date = TODAY();
RUN;

/* JobEvent 2 */
PROC SQL;
    CREATE TABLE work.sales_summary AS
    SELECT region, SUM(amount) AS total_sales
    FROM work.temp_sales
    GROUP BY region;
QUIT;

/* JobEvent 3 */
PROC DATASETS LIBRARY=work NOLIST;
    DELETE temp_sales;
QUIT;
```

### Temporary Datasets
- If temporary dataset is used to pass data between steps: Document as a dataset
- If temporary dataset is only used within a single DATA step: Part of step logic

### PROC TRANSPOSE
Document as a transformation that reshapes data:

```sas
PROC TRANSPOSE DATA=work.sales_wide OUT=work.sales_long;
    BY customer_id;
    VAR jan feb mar apr;
RUN;
```
- **Input:** `work.sales_wide` with columns `customer_id`, `jan`, `feb`, `mar`, `apr`
- **Output:** `work.sales_long` with columns `customer_id`, `_NAME_`, `COL1`
- **Transformation:** Reshape from wide to long format

### Multiple OUTPUT Statements
If multiple OUTPUT statements write to different datasets, document as separate JobEvents:

```sas
DATA work.high_value work.low_value;
    SET work.orders;
    IF amount > 1000 THEN OUTPUT work.high_value;
    ELSE OUTPUT work.low_value;
RUN;
```
- **JobEvent 1:** `work.orders` → `work.high_value` (filtered by amount > 1000)
- **JobEvent 2:** `work.orders` → `work.low_value` (filtered by amount <= 1000)

## Summary Checklist

When analyzing SAS code for lineage:

- ✓ Identify each DATA step that creates output
- ✓ Identify each PROC SQL statement (CREATE TABLE, INSERT)
- ✓ Identify each PROC step with output (OUT=, OUTPUT OUT=)
- ✓ Document stored processes with data movement
- ✓ Trace all datasets in SET, MERGE, UPDATE statements as inputs
- ✓ Identify target datasets from DATA statements or CREATE TABLE
- ✓ Map each output column to its source column(s)
- ✓ Classify transformations as IDENTITY, AGGREGATION, or TRANSFORMATION
- ✓ Document transformation descriptions for non-IDENTITY mappings
- ✓ Note indirect lineage (WHERE, IF, BY, JOIN conditions)
- ✗ Ignore OPTIONS statements
- ✗ Ignore LIBNAME assignments (unless they define the connection)
- ✗ Ignore PROC PRINT, PROC CONTENTS (metadata only)
- ✗ Ignore format and label definitions
- ✗ Ignore index creation
- ✗ Ignore macro definitions (document expanded code)
- ✗ Ignore validation without data movement