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

### Examples

**✓ CORRECT - One JobEvent:**
```java
// Read, transform, and write in one logical operation
Dataset<Row> df = spark.read()
    .format("csv")
    .option("header", "true")
    .load("input/customers.csv");

Dataset<Row> transformed = df
    .withColumn("full_name", concat(col("first_name"), lit(" "), col("last_name")))
    .withColumn("total_amount", col("price").multiply(col("quantity")));

transformed.write()
    .format("parquet")
    .mode("overwrite")
    .save("output/customer_summary.parquet");
```

**✓ CORRECT - One JobEvent per write:**
```java
// JobEvent 1: Filter and save intermediate
Dataset<Row> filtered = orders
    .filter(col("status").equalTo("completed"));
filtered.write().parquet("temp/filtered_orders");

// JobEvent 2: Aggregate and save final
Dataset<Row> summary = filtered
    .groupBy("region")
    .agg(sum("amount").as("total_sales"));
summary.write().parquet("output/sales_summary");
```

## What is Considered a Dataset

### Source Datasets (Inputs)
- Files read by Spark: `.read().csv()`, `.read().parquet()`, `.read().json()`
- Database tables: `.read().jdbc()`, JDBC `ResultSet` from queries
- Kafka topics: `.read().format("kafka")`
- Cloud storage: S3, Azure Blob, GCS file reads
- REST API responses with data
- Message queues: RabbitMQ, ActiveMQ

### Output Datasets
- Files written by Spark: `.write().csv()`, `.write().parquet()`, `.write().json()`
- Database tables: `.write().jdbc()`, JDBC `PreparedStatement` inserts
- Kafka topics: `.write().format("kafka")`
- Cloud storage writes
- REST API POST/PUT with data
- Message queue publishing

### NOT Datasets
- In-memory DataFrames/Datasets (intermediate processing)
- Java collections (List, Map, Set) unless they represent persistent data
- Configuration objects
- Logging outputs
- Temporary variables

## Understanding Lineage and Transformation Logic

### How Data Reading Looks Like

**Spark - CSV Files:**
```java
Dataset<Row> df = spark.read()
    .format("csv")
    .option("header", "true")
    .option("inferSchema", "true")
    .load("hdfs://namenode:9000/data/customers.csv");
```
- **Input Dataset:** File path (HDFS, S3, local)
- **Columns Read:** All columns (or specified in schema)

**Spark - Database (JDBC):**
```java
Dataset<Row> df = spark.read()
    .format("jdbc")
    .option("url", "jdbc:postgresql://host:5432/dbname")
    .option("dbtable", "customers")
    .option("user", "username")
    .option("password", "password")
    .load();

// Or with query
Dataset<Row> df = spark.read()
    .format("jdbc")
    .option("url", "jdbc:postgresql://host:5432/dbname")
    .option("query", "SELECT * FROM customers WHERE status = 'active'")
    .option("user", "username")
    .option("password", "password")
    .load();
```
- **Input Dataset:** Table name or query
- **Connection:** Extract from JDBC URL

**JDBC - Direct Database Access:**
```java
Connection conn = DriverManager.getConnection(
    "jdbc:postgresql://host:5432/dbname", "user", "pass");
Statement stmt = conn.createStatement();
ResultSet rs = stmt.executeQuery("SELECT * FROM customers");
```
- **Input Dataset:** Table in SQL query
- **Connection:** From connection string

**Spark - Kafka:**
```java
Dataset<Row> df = spark.read()
    .format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("subscribe", "customer-events")
    .load();
```
- **Input Dataset:** Kafka topic name

### How Data Writing Looks Like

**Spark - Parquet Files:**
```java
df.write()
    .format("parquet")
    .mode("overwrite")  // or "append", "ignore", "error"
    .save("hdfs://namenode:9000/output/results/");
```
- **Output Dataset:** Directory path
- **Write Mode:** overwrite, append, ignore, error

**Spark - Database (JDBC):**
```java
df.write()
    .format("jdbc")
    .option("url", "jdbc:postgresql://host:5432/dbname")
    .option("dbtable", "sales_summary")
    .option("user", "username")
    .option("password", "password")
    .mode("overwrite")
    .save();
```
- **Output Dataset:** Table name
- **Write Mode:** overwrite, append

**JDBC - Direct Database Insert:**
```java
String sql = "INSERT INTO customer_summary (customer_id, full_name, total_spent) VALUES (?, ?, ?)";
PreparedStatement pstmt = conn.prepareStatement(sql);
pstmt.setInt(1, customerId);
pstmt.setString(2, fullName);
pstmt.setDouble(3, totalSpent);
pstmt.executeUpdate();
```
- **Output Dataset:** Table name from INSERT statement

**Spark - Kafka:**
```java
df.write()
    .format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("topic", "processed-events")
    .save();
```
- **Output Dataset:** Kafka topic name

### How to Identify Transformations

#### Direct Transformations (Column values flow to output)

**1. Column Calculations:**
```java
import static org.apache.spark.sql.functions.*;

Dataset<Row> transformed = df
    .withColumn("total_amount", col("price").multiply(col("quantity")))
    .withColumn("tax", col("total_amount").multiply(0.1))
    .withColumn("discount_price", col("price").multiply(lit(1).minus(col("discount_rate"))));
```
- **Transformation Type:** TRANSFORMATION
- **Lineage:** `price` + `quantity` → `total_amount` (calculation: price * quantity)
- **Lineage:** `total_amount` → `tax` (calculation: total_amount * 0.1)
- **Lineage:** `price` + `discount_rate` → `discount_price` (calculation: price * (1 - discount_rate))

**2. String Operations:**
```java
Dataset<Row> transformed = df
    .withColumn("full_name", concat(col("first_name"), lit(" "), col("last_name")))
    .withColumn("email_domain", split(col("email"), "@").getItem(1))
    .withColumn("upper_name", upper(col("customer_name")));
```
- **Transformation Type:** TRANSFORMATION
- **Lineage:** `first_name` + `last_name` → `full_name` (concatenation)
- **Lineage:** `email` → `email_domain` (extract domain)
- **Lineage:** `customer_name` → `upper_name` (uppercase conversion)

**3. Aggregations:**
```java
Dataset<Row> summary = df
    .groupBy("region")
    .agg(
        sum("amount").as("total_sales"),
        count("order_id").as("order_count"),
        avg("price").as("avg_price")
    );
```
- **Transformation Type:** AGGREGATION
- **Lineage:** `region` → `region` (IDENTITY - grouping key)
- **Lineage:** `amount` → `total_sales` (AGGREGATION: sum)
- **Lineage:** `order_id` → `order_count` (AGGREGATION: count)
- **Lineage:** `price` → `avg_price` (AGGREGATION: avg)

**4. Column Renames:**
```java
Dataset<Row> renamed = df
    .withColumnRenamed("customer_id", "cust_id")
    .withColumnRenamed("customer_name", "name");
```
- **Transformation Type:** IDENTITY
- **Lineage:** `customer_id` → `cust_id` (rename)
- **Lineage:** `customer_name` → `name` (rename)

**5. User-Defined Functions (UDF):**
```java
// Define UDF
spark.udf().register("calculateTier", (Double totalSpent) -> {
    if (totalSpent > 10000) return "Gold";
    else if (totalSpent > 5000) return "Silver";
    else return "Bronze";
}, DataTypes.StringType);

// Use UDF
Dataset<Row> withTier = df
    .withColumn("customer_tier", callUDF("calculateTier", col("total_spent")));
```
- **Transformation Type:** TRANSFORMATION
- **Lineage:** `total_spent` → `customer_tier` (UDF logic)

**6. Window Functions:**
```java
import org.apache.spark.sql.expressions.Window;
import org.apache.spark.sql.expressions.WindowSpec;

WindowSpec windowSpec = Window
    .partitionBy("region")
    .orderBy(col("amount").desc());

Dataset<Row> ranked = df
    .withColumn("rank", row_number().over(windowSpec))
    .withColumn("running_total", sum("amount").over(windowSpec));
```
- **Lineage:** `region` + `amount` → `rank` (TRANSFORMATION: row_number over window)
- **Lineage:** `amount` → `running_total` (AGGREGATION: sum over window)

#### Indirect Transformations (Column influences result but values don't flow)

**1. Filtering:**
```java
Dataset<Row> filtered = df
    .filter(col("status").equalTo("active"))
    .filter(col("amount").gt(100).and(col("region").equalTo("US")));
```
- **INDIRECT Lineage:** `status` influences which rows are included
- **INDIRECT Lineage:** `amount` and `region` influence filtering
- **DIRECT Lineage:** All other columns flow through as IDENTITY

**2. Joins:**
```java
Dataset<Row> result = orders
    .join(customers, orders.col("customer_id").equalTo(customers.col("customer_id")), "left")
    .select(
        orders.col("order_id"),
        customers.col("customer_name"),
        orders.col("amount")
    );
```
- **INDIRECT Lineage:** Join keys (`customer_id`) determine matching
- **DIRECT Lineage:** Selected columns from both DataFrames

**3. Sorting:**
```java
Dataset<Row> sorted = df
    .orderBy(col("order_date").desc(), col("amount").desc());
```
- **INDIRECT Lineage:** Sort columns affect row ordering
- **DIRECT Lineage:** All columns flow through as IDENTITY

### How to Identify Column Mappings

**Step-by-step approach:**

1. **Track DataFrame transformations** from read to write
2. **For each output column, trace back through operations:**
   - Direct reference: `.select(col("customer_id"))`
   - Calculation: `.withColumn("total", col("price").multiply(col("quantity")))`
   - Rename: `.withColumnRenamed("old_name", "new_name")`
   - Aggregation: `.groupBy("key").agg(sum("value"))`

3. **Determine transformation type:**
   - No change or rename: IDENTITY
   - Aggregation function: AGGREGATION
   - Any other operation: TRANSFORMATION

4. **Document transformation description:**
   - For IDENTITY: Can omit description
   - For AGGREGATION: "sum of amount", "count of orders", "avg of price"
   - For TRANSFORMATION: "price * quantity", "concat(first_name, ' ', last_name)", "UDF calculateTier"

**Example Analysis:**
```java
// Read data
Dataset<Row> customers = spark.read()
    .format("csv")
    .option("header", "true")
    .load("input/customers.csv");

Dataset<Row> orders = spark.read()
    .format("csv")
    .option("header", "true")
    .load("input/orders.csv");

// Transform
Dataset<Row> merged = customers
    .join(orders, "customer_id");

Dataset<Row> withFullName = merged
    .withColumn("full_name", concat(col("first_name"), lit(" "), col("last_name")));

Dataset<Row> summary = withFullName
    .groupBy("customer_id", "full_name")
    .agg(
        count("order_id").as("order_count"),
        sum("amount").as("total_spent")
    );

// Calculate tier
Dataset<Row> withTier = summary
    .withColumn("tier", 
        when(col("total_spent").gt(10000), "Gold")
        .when(col("total_spent").gt(5000), "Silver")
        .otherwise("Bronze")
    );

// Write
withTier.write()
    .format("parquet")
    .mode("overwrite")
    .save("output/customer_summary.parquet");
```

**Column Mappings:**
- `customers.customer_id` → `customer_id` (IDENTITY)
- `customers.first_name` + `customers.last_name` → `full_name` (TRANSFORMATION: "concat(first_name, ' ', last_name)")
- `orders.order_id` → `order_count` (AGGREGATION: "count of order_id")
- `orders.amount` → `total_spent` (AGGREGATION: "sum of amount")
- `total_spent` → `tier` (TRANSFORMATION: "when/otherwise tier calculation")

## What is NOT Lineage

### Configuration and Setup
```java
// NOT lineage - Spark configuration
SparkConf conf = new SparkConf()
    .setAppName("DataProcessing")
    .setMaster("local[*]");
SparkSession spark = SparkSession.builder()
    .config(conf)
    .getOrCreate();

// NOT lineage - JDBC driver loading
Class.forName("org.postgresql.Driver");
```

### Logging and Debugging
```java
// NOT lineage - logging
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
Logger logger = LoggerFactory.getLogger(MyClass.class);
logger.info("Processing started");

// NOT lineage - debugging
df.show(10);
df.printSchema();
System.out.println("Record count: " + df.count());
```

### Data Validation Without Movement
```java
// NOT lineage - validation only
long invalidCount = df.filter(col("amount").lt(0)).count();
if (invalidCount > 0) {
    logger.warn("Found {} invalid records", invalidCount);
}

// NOT lineage - data quality checks
Dataset<Row> nullCheck = df.filter(col("customer_id").isNull());
```

### Helper Methods Without Data Movement
```java
// NOT lineage - utility method
public static String formatCurrency(double amount) {
    return String.format("$%.2f", amount);
}

// NOT lineage - validation method
public static boolean isValidEmail(String email) {
    return email != null && email.contains("@") && email.contains(".");
}
```

### Exception Handling
```java
// NOT lineage - error handling
try {
    Dataset<Row> df = spark.read().csv("data.csv");
} catch (AnalysisException e) {
    logger.error("Failed to read file", e);
    return;
}
```

### Comments and Documentation
```java
// NOT lineage - comments
/**
 * This class processes customer data
 * @author John Doe
 * @version 1.0
 */
```

## Special Cases

### Methods That Perform ETL
Document the entire method as one JobEvent if it performs a complete read-transform-write operation:

```java
public void processCustomerData() {
    // This entire method is one JobEvent
    Dataset<Row> df = spark.read().csv("input/customers.csv");
    Dataset<Row> transformed = df.withColumn("full_name", 
        concat(col("first_name"), lit(" "), col("last_name")));
    transformed.write().parquet("output/processed_customers.parquet");
}
```

### Multiple Writes in One Method
Each write operation is a separate JobEvent:

```java
public void processOrders() {
    // JobEvent 1
    Dataset<Row> filtered = orders.filter(col("status").equalTo("completed"));
    filtered.write().parquet("output/completed_orders");
    
    // JobEvent 2
    Dataset<Row> summary = filtered.groupBy("region").agg(sum("amount"));
    summary.write().parquet("output/regional_summary");
}
```

### Intermediate DataFrames
In-memory DataFrames are NOT separate datasets unless they're written to persistent storage:

```java
// One JobEvent - intermediate DataFrames are part of transformation logic
Dataset<Row> df = spark.read().csv("input/data.csv");
Dataset<Row> temp1 = df.filter(col("status").equalTo("active"));  // NOT a dataset
Dataset<Row> temp2 = temp1.groupBy("region").agg(sum("amount"));  // NOT a dataset
temp2.write().parquet("output/summary.parquet");  // This is the output dataset
```

### Streaming Applications
For Spark Structured Streaming, document each streaming query as a JobEvent:

```java
// JobEvent - Streaming read and write
Dataset<Row> stream = spark.readStream()
    .format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("subscribe", "input-topic")
    .load();

Dataset<Row> processed = stream
    .selectExpr("CAST(value AS STRING)")
    .withColumn("processed_time", current_timestamp());

processed.writeStream()
    .format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("topic", "output-topic")
    .option("checkpointLocation", "/tmp/checkpoint")
    .start();
```

## Summary Checklist

When analyzing Java code for lineage:

- ✓ Identify each `.read()` operation (Spark, JDBC)
- ✓ Identify each `.write()` operation (Spark, JDBC)
- ✓ Track DataFrame/Dataset transformations between read and write
- ✓ Map each output column to its source column(s)
- ✓ Classify transformations as IDENTITY, AGGREGATION, or TRANSFORMATION
- ✓ Document transformation descriptions for non-IDENTITY mappings
- ✓ Note indirect lineage (filtering, joins, sorting)
- ✓ Extract connection details from JDBC URLs
- ✓ Document UDFs and their logic
- ✗ Ignore Spark configuration and session creation
- ✗ Ignore logging and debugging statements
- ✗ Ignore validation without data movement
- ✗ Ignore helper methods that don't read/write data
- ✗ Ignore in-memory intermediate DataFrames (part of transformation logic)
- ✗ Ignore exception handling blocks