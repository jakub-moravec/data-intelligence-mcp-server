# Python Data Lineage Analysis Guide

## What is considered Context

Statements that set execution environment but don't move data. Context affects how subsequent data movements are interpreted.

## Context-Setting Statements

- Environment variable reads (`os.getenv()`, `os.environ[]`)
- Configuration file loading (`configparser`, `yaml.load()`, `json.load()` for config)
- Command-line argument parsing (`argparse`, `sys.argv`)
- Global variable assignments at module level
- Class-level constants and class variables
- Function default parameters
- Decorator definitions (when they set context)
- Context managers setup (`with` statement initialization)
- Connection string definitions
- Spark session configuration (`SparkSession.builder.config()`)
- Database connection setup (before queries)
- Import statements with aliasing
- `__init__()` methods that set instance state

## Context Storage

```json
context = {
    "environment_vars": {
        "DATA_PATH": [
            {"line": 5, "value": "/data/dev"},
            {"line": 150, "value": "/data/prod"}
        ],
        "DB_HOST": [
            {"line": 6, "value": "localhost"},
            {"line": 155, "value": "prod-db.example.com"}
        ]
    },
    "config_values": {
        "input_format": [
            {"line": 10, "value": "csv"},
            {"line": 160, "value": "parquet"}
        ],
        "batch_size": [
            {"line": 11, "value": 1000},
            {"line": 165, "value": 10000}
        ]
    },
    "connection_strings": {
        "db_url": [
            {"line": 15, "value": "postgresql://localhost:5432/dev"},
            {"line": 170, "value": "postgresql://prod-server:5432/prod"}
        ]
    },
    "spark_config": [
        {"line": 20, "value": {"master": "local[*]", "app.name": "ETL"}},
        {"line": 175, "value": {"master": "yarn", "app.name": "ETL_Prod"}}
    ],
    "file_paths": {
        "input_path": [
            {"line": 25, "value": "/tmp/input"},
            {"line": 180, "value": "/prod/input"}
        ]
    }
}
```

## Context handling Workflow

1. **Initialize** - Scan for imports, global variables, environment reads, config loading
2. **Process line-by-line or function-by-function**:
   - If context statement → Update context, track line number
   - If data movement → Resolve references using current context
3. **Resolve** - Replace variables, f-strings, environment variables with actual values

- **Don't assume static context** - Variables can be reassigned, config can change
- **Version context** - Track changes by referencing line numbers
- **Resolve all references** - Use context before generating lineage
- **Handle f-strings and string formatting** - Resolve to actual paths/values
- **Track function parameters** - They may affect file paths or table names
- **Follow variable scope** - Global vs local context
- **Handle conditional logic** - Context may vary based on if/else branches
- **Document context version** - Reference in lineage metadata

## What is Considered a Transformation

In Python, a **transformation** is any operation that reads data from one or more sources and writes it to a destination, potentially modifying the data in the process.

### Python Operations That Move Data (Transformations)

**Pandas Operations:**
- `df.to_csv()` - Writes DataFrame to CSV
- `df.to_excel()` - Writes DataFrame to Excel
- `df.to_parquet()` - Writes DataFrame to Parquet
- `df.to_json()` - Writes DataFrame to JSON
- `df.to_sql()` - Writes DataFrame to database table
- `df.to_hdf()` - Writes DataFrame to HDF5
- `df.to_feather()` - Writes DataFrame to Feather format
- `df.to_pickle()` - Serializes DataFrame to pickle

**PySpark Operations:**
- `df.write.csv()` - Writes DataFrame to CSV
- `df.write.parquet()` - Writes DataFrame to Parquet
- `df.write.json()` - Writes DataFrame to JSON
- `df.write.jdbc()` - Writes DataFrame to database via JDBC
- `df.write.saveAsTable()` - Saves as Hive/Spark table
- `df.write.insertInto()` - Inserts into existing table
- `df.write.format().save()` - Generic write with format
- `rdd.saveAsTextFile()` - Saves RDD to text files

**Database Operations:**
- SQLAlchemy `session.add()` / `session.commit()` - Inserts/updates records
- SQLAlchemy `session.bulk_insert_mappings()` - Bulk inserts
- `psycopg2` cursor `execute()` with INSERT/UPDATE/DELETE
- `pymysql` cursor `execute()` with data modification
- `sqlite3` cursor `execute()` with data modification
- `cx_Oracle` cursor `execute()` with data modification
- ORM operations (Django, SQLAlchemy) that persist data

**File I/O Operations:**
- `open().write()` - Writes to file
- `json.dump()` - Writes JSON to file
- `yaml.dump()` - Writes YAML to file
- `pickle.dump()` - Serializes object to file
- `csv.writer.writerow()` - Writes CSV rows
- `h5py` file writes - HDF5 file operations
- `numpy.save()` / `numpy.savez()` - Saves NumPy arrays

**Cloud Storage Operations:**
- `boto3` S3 `put_object()` - Uploads to S3
- `boto3` S3 `upload_file()` - Uploads file to S3
- Azure Blob `upload_blob()` - Uploads to Azure Blob Storage
- GCS `blob.upload_from_file()` - Uploads to Google Cloud Storage
- `s3fs` file writes - S3 filesystem operations
- `gcsfs` file writes - GCS filesystem operations

**API Operations:**
- `requests.post()` - HTTP POST with data
- `requests.put()` - HTTP PUT with data
- `requests.patch()` - HTTP PATCH with data
- GraphQL mutations via `gql` or `requests`
- REST API calls that create/update resources
- SOAP API calls that modify data

**Message Queue Operations:**
- Kafka `producer.send()` - Sends message to Kafka topic
- RabbitMQ `channel.basic_publish()` - Publishes to RabbitMQ
- Redis `redis.set()` / `redis.lpush()` - Writes to Redis
- AWS SQS `send_message()` - Sends to SQS queue
- Azure Service Bus `send()` - Sends to Service Bus

**ETL Framework Operations:**
- Apache Airflow task outputs
- Luigi task outputs
- Prefect task results that persist data
- Dagster asset materializations
- dbt model runs (via Python)

**Data Science/ML Operations:**
- `joblib.dump()` - Saves ML models
- `pickle.dump()` - Saves models/data
- TensorFlow `model.save()` - Saves models
- PyTorch `torch.save()` - Saves models
- scikit-learn `dump()` - Saves models

### Transformation Granularity for JobEvents

**One JobEvent per:**
- Single data read → transform → write operation
- Single function call that performs ETL (Extract, Transform, Load)
- Single DataFrame operation that writes to persistent storage
- Single API call that moves/transforms data
- Single file processing operation (read → process → write)
- Single database transaction that modifies data
- Single message queue publish operation
- Single cloud storage upload operation
- Single model training and save operation

**NOT separate JobEvents:**
- Intermediate DataFrame operations in memory (part of the transformation logic)
- Multiple transformations on the same DataFrame before writing (one job with complex transformation)
- Helper functions that don't directly read/write data
- Data validation steps (part of transformation logic)
- Logging operations
- DataFrame method chaining (`.filter().select().groupby()`)
- List comprehensions and map/filter operations in memory


## What is Considered a Dataset

### Source Datasets (Inputs)

**Pandas Sources:**
- CSV files: `pd.read_csv("path/to/file.csv")`
- Excel files: `pd.read_excel("path/to/file.xlsx")`
- Parquet files: `pd.read_parquet("path/to/file.parquet")`
- JSON files: `pd.read_json("path/to/file.json")`
- HDF5 files: `pd.read_hdf("path/to/file.h5")`
- Feather files: `pd.read_feather("path/to/file.feather")`
- Database tables: `pd.read_sql("SELECT * FROM table", conn)`
- Database queries: `pd.read_sql_query("SELECT ...", conn)`
- Clipboard: `pd.read_clipboard()`

**PySpark Sources:**
- CSV files: `spark.read.csv("path")`
- Parquet files: `spark.read.parquet("path")`
- JSON files: `spark.read.json("path")`
- ORC files: `spark.read.orc("path")`
- Avro files: `spark.read.format("avro").load("path")`
- JDBC tables: `spark.read.jdbc(url, table, properties)`
- Hive tables: `spark.table("database.table")`
- Text files: `spark.read.text("path")`

**Database Sources:**
- Tables queried via SQLAlchemy: `session.query(Model).all()`
- Tables queried via raw SQL: `cursor.execute("SELECT * FROM table")`
- Views referenced in queries
- Stored procedure results
- Database-specific sources (PostgreSQL, MySQL, Oracle, SQL Server)

**File Sources:**
- Text files: `open("file.txt").read()`
- JSON files: `json.load(open("file.json"))`
- YAML files: `yaml.safe_load(open("file.yaml"))`
- XML files: `xml.etree.ElementTree.parse("file.xml")`
- Pickle files: `pickle.load(open("file.pkl", "rb"))`
- NumPy files: `numpy.load("file.npy")`
- HDF5 files: `h5py.File("file.h5", "r")`

**Cloud Storage Sources:**
- S3 objects: `s3.get_object(Bucket="bucket", Key="key")`
- S3 files via pandas: `pd.read_csv("s3://bucket/key")`
- Azure Blob: `blob_client.download_blob()`
- GCS objects: `blob.download_as_string()`

**API Sources:**
- REST API GET: `requests.get(url).json()`
- GraphQL queries: `client.execute(query)`
- SOAP API responses
- WebSocket data streams

**Message Queue Sources:**
- Kafka topics: `consumer.poll()`
- RabbitMQ queues: `channel.basic_get(queue)`
- Redis streams: `redis.xread()`
- AWS SQS: `sqs.receive_message()`

### Output Datasets

**Pandas Outputs:**
- CSV files: `df.to_csv("output.csv")`
- Excel files: `df.to_excel("output.xlsx")`
- Parquet files: `df.to_parquet("output.parquet")`
- JSON files: `df.to_json("output.json")`
- HDF5 files: `df.to_hdf("output.h5", key="data")`
- Database tables: `df.to_sql("table", conn)`
- Feather files: `df.to_feather("output.feather")`

**PySpark Outputs:**
- CSV files: `df.write.csv("path")`
- Parquet files: `df.write.parquet("path")`
- JSON files: `df.write.json("path")`
- JDBC tables: `df.write.jdbc(url, table, properties)`
- Hive tables: `df.write.saveAsTable("table")`
- ORC files: `df.write.orc("path")`

**Database Outputs:**
- Tables modified via INSERT: `cursor.execute("INSERT INTO ...")`
- Tables modified via UPDATE: `cursor.execute("UPDATE ...")`
- Tables modified via ORM: `session.add(obj); session.commit()`
- Bulk inserts: `session.bulk_insert_mappings()`

**File Outputs:**
- Text files: `open("output.txt", "w").write(data)`
- JSON files: `json.dump(data, open("output.json", "w"))`
- YAML files: `yaml.dump(data, open("output.yaml", "w"))`
- Pickle files: `pickle.dump(obj, open("output.pkl", "wb"))`
- NumPy files: `numpy.save("output.npy", array)`

**Cloud Storage Outputs:**
- S3 uploads: `s3.put_object(Bucket="bucket", Key="key", Body=data)`
- S3 via pandas: `df.to_csv("s3://bucket/key")`
- Azure Blob: `blob_client.upload_blob(data)`
- GCS uploads: `blob.upload_from_string(data)`

**API Outputs:**
- REST API POST: `requests.post(url, json=data)`
- REST API PUT: `requests.put(url, json=data)`
- GraphQL mutations: `client.execute(mutation)`

**Message Queue Outputs:**
- Kafka: `producer.send("topic", value=data)`
- RabbitMQ: `channel.basic_publish(exchange, routing_key, body)`
- Redis: `redis.set(key, value)`
- AWS SQS: `sqs.send_message(QueueUrl=url, MessageBody=data)`

### NOT Datasets

- In-memory DataFrames (intermediate processing)
- Python variables and lists (unless they represent persistent data)
- Dictionaries used for configuration
- Temporary variables in functions
- Generator expressions (unless materialized)
- Iterator objects (unless consumed and persisted)
- Lambda functions
- Logging outputs (unless explicitly logging data to files)
- Print statements
- Debug outputs
- Cache/memoization results (unless persisted)
- Function return values (unless persisted)