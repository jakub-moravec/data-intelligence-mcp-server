# Java Data Lineage Analysis Guide

## What is Considered a Transformation

In Java, a **transformation** is any operation that reads data from one or more sources and writes it to a destination, potentially modifying the data in the process. This commonly occurs in Spark applications, JDBC operations, and ETL frameworks.

### Transformation Granularity for JobEvents

**One JobEvent per:**
- Single Spark DataFrame write operation
- Single JDBC batch insert/update
- Single file processing operation (read → transform → write)
- Single method that performs complete ETL
- Single Kafka message processing with output
- Single REST API call that moves/transforms data

**NOT separate JobEvents:**
- Intermediate DataFrame transformations in memory (part of the transformation logic)
- Multiple transformations on the same DataFrame before writing (one job with complex transformation)
- Helper methods that don't directly read/write data
- Builder pattern method chains (part of single operation)