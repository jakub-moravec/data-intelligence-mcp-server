# SQL Data Lineage Analysis Guide

## What is Considered a Transformation

In SQL, a **transformation** is any statement that reads data from one or more sources and writes it to a destination, potentially modifying the data in the process.

### Transformation Granularity for JobEvents

**One JobEvent per:**
- Single `INSERT INTO ... SELECT` statement
- Single `CREATE TABLE AS SELECT` statement
- Single `CREATE VIEW` statement
- Single `UPDATE` statement with data from other tables
- Single `MERGE` statement
- Single stored procedure execution
- Single function execution that moves/transforms data

**NOT separate JobEvents:**
- Subqueries within a larger query (part of the parent query's transformation)
- Common Table Expressions (CTEs) - part of the main query
