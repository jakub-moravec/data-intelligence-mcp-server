# Java Data Lineage Analysis Guide

## What is considered Context

Statements that set execution environment but don't move data. Context affects how subsequent data movements are interpreted.

## Context-Setting Statements

- Configuration objects (`SparkConf`, `Properties`, `Configuration`)
- Connection string definitions
- Environment variable reads (`System.getenv()`, `System.getProperty()`)
- Spring `@Configuration` classes and `@Bean` definitions
- Dependency injection container setup
- Resource initialization (connection pools, file system handles)
- Class-level constants and static initializers
- Constructor parameters that set instance state
- Builder pattern setup methods (before `.build()`)
- Session/context creation (`SparkSession.builder()`, `Connection` creation)

## Context Storage

```json
context = {
    "spark_config": [
        {"line": 15, "value": {"master": "local[*]", "app_name": "ETL_Job"}},
        {"line": 120, "value": {"master": "yarn", "app_name": "ETL_Job_Prod"}}
    ],
    "connection_strings": {
        "db_url": [
            {"line": 20, "value": "jdbc:postgresql://localhost:5432/dev_db"},
            {"line": 125, "value": "jdbc:postgresql://prod-server:5432/prod_db"}
        ]
    },
    "file_paths": {
        "input_path": [
            {"line": 25, "value": "/data/input"},
            {"line": 130, "value": "/prod/data/input"}
        ],
        "output_path": [
            {"line": 26, "value": "/data/output"},
            {"line": 131, "value": "/prod/data/output"}
        ]
    },
    "environment_vars": {
        "DATA_SOURCE": [
            {"line": 30, "value": "dev"},
            {"line": 135, "value": "production"}
        ]
    },
    "active_session": [
        {"line": 40, "value": "SparkSession@dev"},
        {"line": 140, "value": "SparkSession@prod"}
    ]
}
```

## Context handling Workflow

1. **Initialize** - Scan for configuration setup, imports, and class-level context
2. **Process method-by-method**:
   - If context statement → Update context, track line number
   - If data movement → Resolve references using current context
3. **Resolve** - Replace variables, configuration values, and environment references with actual values

- **Don't assume static context** - Configuration can change at runtime
- **Version context** - Track changes by referencing line numbers
- **Resolve all references** - Use context before generating lineage
- **Track dependency injection** - Spring beans and injected values affect context
- **Follow builder patterns** - Configuration accumulates until `.build()` or execution
- **Handle conditional logic** - Context may vary based on if/switch statements
- **Document context version** - Reference in lineage metadata

## What is Considered a Transformation

In Java, a **transformation** is any operation that reads data from one or more sources and writes it to a destination, potentially modifying the data in the process. This commonly occurs in Spark applications, JDBC operations, and ETL frameworks.

### Java Operations That Move Data (Transformations)

**Apache Spark Operations:**
- `DataFrame.write()` - Writes DataFrame to storage
- `Dataset.write()` - Writes Dataset to storage
- `RDD.saveAsTextFile()` - Saves RDD to text files
- `RDD.saveAsObjectFile()` - Saves RDD to object files
- `DataFrame.insertInto()` - Inserts into existing table
- `DataFrame.saveAsTable()` - Saves as managed/external table
- `spark.sql("INSERT INTO ...")` - SQL-based insert
- `spark.sql("CREATE TABLE AS SELECT ...")` - CTAS operation

**JDBC Operations:**
- `PreparedStatement.executeUpdate()` - Single row update/insert
- `PreparedStatement.executeBatch()` - Batch insert/update
- `Statement.execute("INSERT INTO ...")` - Direct SQL insert
- `Statement.execute("UPDATE ...")` - Direct SQL update
- `Statement.execute("MERGE ...")` - Merge operation
- `Connection.commit()` - Commits transaction with data changes

**File I/O Operations:**
- `FileWriter.write()` - Writes to file
- `BufferedWriter.write()` - Buffered file writing
- `Files.write()` - NIO file writing
- `PrintWriter.println()` - Formatted file output
- `ObjectOutputStream.writeObject()` - Serialized object writing
- CSV/JSON/XML library write operations (Jackson, Gson, OpenCSV)

**Stream Processing:**
- Kafka `Producer.send()` - Sends message to Kafka topic
- Kafka Streams `to()` - Writes to output topic
- Flink `DataStream.addSink()` - Adds sink to stream
- Flink `DataStream.writeAsText()` - Writes stream to file
- Storm `bolt.emit()` - Emits tuple to next component

**REST/API Operations:**
- HTTP POST/PUT requests that create/update data
- REST client calls that move data between systems
- GraphQL mutations that modify data
- gRPC calls that transfer data

**ETL Framework Operations:**
- Apache Camel route endpoints that write data
- Spring Batch `ItemWriter.write()` - Batch item writing
- Talend component outputs
- Apache NiFi processor outputs

**Cloud SDK Operations:**
- AWS S3 `putObject()` - Uploads to S3
- Azure Blob `upload()` - Uploads to blob storage
- GCS `create()` - Creates object in Google Cloud Storage
- AWS Glue job executions
- Azure Data Factory pipeline activities

### Transformation Granularity for JobEvents

**One JobEvent per:**
- Single Spark DataFrame write operation
- Single JDBC batch insert/update
- Single file processing operation (read → transform → write)
- Single method that performs complete ETL
- Single Kafka message processing with output
- Single REST API call that moves/transforms data
- Single stream processing job execution
- Single cloud storage upload/download operation
- Single batch job execution (Spring Batch, etc.)

**NOT separate JobEvents:**
- Intermediate DataFrame transformations in memory (part of the transformation logic)
- Multiple transformations on the same DataFrame before writing (one job with complex transformation)
- Helper methods that don't directly read/write data
- Builder pattern method chains (part of single operation)
- Map/filter/reduce operations before final write (part of transformation logic)
- Data validation steps (part of transformation logic)
- Logging and monitoring calls


## What is Considered a Dataset

### Source Datasets (Inputs)

**Spark Sources:**
- DataFrames read from files: `spark.read().parquet("path")`
- DataFrames read from tables: `spark.table("database.table")`
- DataFrames read from JDBC: `spark.read().jdbc(url, table, props)`
- RDDs from text files: `sc.textFile("path")`
- Datasets from various sources: `spark.read().format("csv").load()`
- Streaming sources: `spark.readStream().format("kafka")`

**JDBC Sources:**
- Tables in SELECT queries: `SELECT * FROM schema.table`
- Tables in JOIN clauses: `FROM orders o JOIN customers c`
- Views referenced in queries: `SELECT * FROM customer_view`
- Result sets from stored procedures: `CallableStatement.execute()`

**File Sources:**
- CSV files: `new CSVReader(new FileReader("data.csv"))`
- JSON files: `ObjectMapper.readValue(new File("data.json"))`
- XML files: `DocumentBuilder.parse(new File("data.xml"))`
- Parquet files: `ParquetReader.read()`
- Avro files: `DataFileReader.read()`
- Text files: `Files.readAllLines(Paths.get("data.txt"))`

**Stream Sources:**
- Kafka topics consumed: `consumer.subscribe(Arrays.asList("topic"))`
- Kafka Streams input topics: `builder.stream("input-topic")`
- Flink sources: `env.addSource(new FlinkKafkaConsumer<>())`
- Message queue inputs: JMS, RabbitMQ, ActiveMQ sources

**Cloud Storage Sources:**
- S3 objects: `s3Client.getObject("bucket", "key")`
- Azure Blob storage: `blobClient.download()`
- Google Cloud Storage: `storage.get(blobId)`
- HDFS files: `FileSystem.open(path)`

**API Sources:**
- REST API responses: `restTemplate.getForObject(url, Class)`
- GraphQL query results: `graphQLClient.query()`
- gRPC service responses: `stub.getData(request)`

### Output Datasets

**Spark Outputs:**
- DataFrames written to files: `df.write().parquet("path")`
- DataFrames written to tables: `df.write().saveAsTable("table")`
- DataFrames written via JDBC: `df.write().jdbc(url, table, props)`
- RDDs saved to files: `rdd.saveAsTextFile("path")`
- Streaming outputs: `query.writeStream().format("kafka")`

**JDBC Outputs:**
- Tables modified by INSERT: `INSERT INTO schema.table VALUES (...)`
- Tables modified by UPDATE: `UPDATE schema.table SET ...`
- Tables modified by MERGE: `MERGE INTO schema.table ...`
- Tables created: `CREATE TABLE schema.table AS SELECT ...`

**File Outputs:**
- CSV files written: `csvWriter.writeAll(records)`
- JSON files written: `objectMapper.writeValue(new File("out.json"), data)`
- XML files written: `transformer.transform(source, new StreamResult(file))`
- Parquet files written: `ParquetWriter.write()`
- Text files written: `Files.write(Paths.get("out.txt"), lines)`

**Stream Outputs:**
- Kafka topics produced to: `producer.send(new ProducerRecord<>("topic", data))`
- Kafka Streams output topics: `stream.to("output-topic")`
- Flink sinks: `stream.addSink(new FlinkKafkaProducer<>())`
- Message queue outputs: JMS, RabbitMQ, ActiveMQ destinations

**Cloud Storage Outputs:**
- S3 objects written: `s3Client.putObject("bucket", "key", file)`
- Azure Blob storage written: `blobClient.upload(data)`
- Google Cloud Storage written: `storage.create(blobInfo, content)`
- HDFS files written: `FileSystem.create(path)`

**API Outputs:**
- REST API POST/PUT: `restTemplate.postForObject(url, data, Class)`
- GraphQL mutations: `graphQLClient.mutate()`
- gRPC service calls: `stub.updateData(request)`

### NOT Datasets

- In-memory collections (List, Set, Map) unless persisted
- Temporary variables holding intermediate results
- DataFrame transformations not yet written (`.select()`, `.filter()`, `.map()`)
- RDD transformations not yet materialized
- Stream processing intermediate operators
- Cache/persist operations (optimization, not separate datasets)
- Broadcast variables in Spark
- Accumulators in Spark
- Configuration objects
- Connection objects themselves
- Logger outputs (unless explicitly logging data to files)
- Metrics and monitoring data (unless persisted)