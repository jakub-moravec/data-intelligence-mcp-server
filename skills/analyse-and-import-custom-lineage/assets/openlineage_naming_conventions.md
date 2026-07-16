# OpenLineage Naming Conventions

**Version: 1.50.0**

Source: https://openlineage.io/docs/spec/naming

## Overview

Employing a unique naming strategy per resource ensures that the spec is followed uniformly regardless of metadata producer.

Jobs and Datasets have their own namespaces, job namespaces being derived from schedulers and dataset namespaces from datasources.

## Dataset Naming

A dataset, or `table`, is organized according to a producer, namespace, database and table name.

## Dataset Naming Examples by Data Store

| Data Store | Type | Namespace | Name |
|------------|------|-----------|------|
| **Athena** | Warehouse | `awsathena://athena.{region_name}.amazonaws.com` | `{catalog}.{database}.{table}` |
| **AWS Glue** | Data catalog | `arn:aws:glue:{region}:{account_id}` | `table/{database_name}/{table_name}` |
| **Azure Cosmos DB** | Warehouse | `azurecosmos://{host}/dbs/{database}` | `colls/{table}` |
| **Azure Data Explorer** | Warehouse | `azurekusto://{host}.kusto.windows.net` | `{database}/{table}` |
| **Azure Synapse** | Warehouse | `sqlserver://{host}:{port}` | `{schema}.{table}` |
| **BigQuery** | Warehouse | `bigquery` | `{project_id}.{dataset_name}.{table_name}` |
| **Cassandra** | Warehouse | `cassandra://{host}:{port}` | `{keyspace}.{table}` |
| **Milvus** | Vector database | `milvus://{host}:{port}` | `{database}.{collection}` |
| **Microsoft Fabric Warehouse** | Warehouse | `fabric-warehouse://{sql_analytics_endpoint}` or `fabric-warehouse://{sql_analytics_endpoint}:{port}` | `{database}.{schema}.{table}` |
| **MySQL** | Warehouse | `mysql://{host}:{port}` | `{database}.{table}` |
| **CrateDB** | Warehouse | `crate://{host}:{port}` | `{database}.{schema}.{table}` |
| **DB2** | Warehouse | `db2://{host}:{port}` | `{database}.{schema}.{table}` |
| **Hive** | Warehouse | `hive://{host}:{port}` | `{database}.{table}` |
| **MSSQL** | Warehouse | `mssql://{host}:{port}` | `{database}.{schema}.{table}` |
| **Oracle** | Warehouse | `oracle://{host}:{port}` | `{serviceName}.{schema}.{table}` or `{sid}.{schema}.{table}` |
| **Postgres** | Warehouse | `postgres://{host}:{port}` | `{database}.{schema}.{table}` |
| **Teradata** | Warehouse | `teradata://{host}:{port}` | `{database}.{table}` |
| **Redshift** | Warehouse | `redshift://{cluster_identifier}.{region_name}:{port}` | `{database}.{schema}.{table}` |
| **Snowflake** | Warehouse | `snowflake://{organization_name}-{account_name}` or `snowflake://{account-locator}.{compliance}.{cloud_region_id}).{cloud}` | `{database}.{schema}.{table}` |
| **Trino** | Warehouse | `trino://{host}:{port}` | `{catalog}.{schema}.{table}` |
| **ABFSS (Azure Data Lake Gen2)** | Data lake | `abfss://{container_name}@{service_name}.dfs.core.windows.net` | `{path}` |
| **DBFS (Databricks File System)** | Distributed file system | `dbfs://{workspace_name}` | `{path}` |
| **GCS** | Blob storage | `gs://{bucket_name}` | `{object_key}` |
| **HDFS** | Distributed file system | `hdfs://{namenode_host}:{namenode_port}` | `{path}` |
| **Local file system** | File system | `file` | `{path}` |
| **Remote file system** | File system | `file://{host}` | `{path}` |
| **Box** | Document Management System | `box://{host}:{port}/{enterprise_ID}` | `{object_key}` |
| **FileNet** | Document Management System | `filenet://{host}:{port}/{repository_ID}` | `{object_key}` |
| **S3** | Blob Storage | `s3://{bucket_name}` | `{object_key}` |
| **SharePoint** | Document Management System | `mssharepoint://{host}:{port}/{site}` | `{object_key}` |

## Notes

- The namespace typically includes the protocol/scheme and host information
- The name typically includes the hierarchical path to the specific data object (database, schema, table, or file path)
- For cloud services, region and account information may be included in the namespace
- File systems use paths as the name component
- Document management systems use object keys as the name component