---
name: analyse-and-import-custom-lineage
description: Use this skill to help users document custom lineage in watsonx.data intelligence using OpenLineage JobEvents for systems without automated scanning capabilities. Use this skill whenever user can provide any of these inputs for this agent to understand and document custom lineage a) user knows how some system, that is not supported for automated lineage scanning by watsonx.data intelligence, works b) user has architecture diagrams, specifications, or technical documentation for some system c) user has source code of transfromations
---

## Core Capabilities
- Interactive lineage information gathering through conversation
- AI-assisted lineage discovery from documentation and code
- OpenLineage JobEvent payload generation
- Lineage visualization and validation

## Workflows

### Workflow 1: User-Directed Lineage Documentation
**When to use:** User knows the lineage structure and can describe it explicitly.

**Process:** Engage in conversation → Generate JobEvents → Present summary → Incorporate feedback → Package ZIP

**Prerequisites:** User has knowledge of source/target systems, transformations, and optionally column mappings.

### Workflow 2: AI-Assisted Lineage Discovery
**When to use:** User has documentation, diagrams, or code that describes the lineage.

**Process:** Analyze materials → Extract data flows → Propose lineage → Validate with user → Refine → Package ZIP

**Prerequisites:** User can provide relevant documentation/code with sufficient detail and validate discovered lineage.

## Information Gathering

### Required Questions
**Source/Target Systems:**
- System name and type (mandatory)
- Namespace (e.g., 'production.crm') (mandatory)
- Dataset/table name (mandatory)
- Hierarchy structure (e.g., database > schema > table) (mandatory)
- Hierarchy level values (e.g., database: 'CRMDB', schema: 'public', table: 'customers') (mandatory)
- Columns (mandatory)
- Data types (optional)
- Connection URI (optional)

**Job Information:**
- Tool/system name and type (mandatory)
- Job/process name (mandatory)
- Job description (mandatory)
- Processing type (BATCH, STREAMING, etc.) (optional)

**Transformations:**
- Column mappings (optional)
- Column renames (optional)
- Calculated/derived columns (optional)
- Filters/aggregations (optional)
- System-generated columns (optional)

### Response Formats

**Lineage Summary:**
```
Dataset lineage summary:

Input: <namespace>.<dataset-name>
  Columns: <column1>, <column2>, ...

Job: <job-namespace>.<job-name>
  Description: <job-description>
  Type: <BATCH|STREAMING>

Output: <namespace>.<dataset-name>
  Columns: <column1>, <column2>, ...

Column Mappings:
  <source-col> → <target-col> (IDENTITY|RENAMED|CALCULATED)
  <source-col> → <target-col> (transformation description)
```

**Validation Request:**
```
I've prepared the lineage documentation. Please review:

[Summary displayed]

Does this look correct? 
- Reply "yes" to proceed
- Reply "no" and describe what needs to change
- Ask questions if anything is unclear
```

## OpenLineage JobEvent Structure

JobEvents document static job lineage without execution-specific run information.

**Required Fields:**
- `eventType`: "COMPLETE" (for static job documentation)
- `eventTime`: ISO-8601 current timestamp
- `job`: Object with namespace, name, and facets
- `producer`: "https://github.com/IBM/data-intelligence-mcp-server"

**Key Characteristics:**
- NO `run` object (distinguishes JobEvent from RunEvent)
- Includes `inputs` and `outputs` arrays
- Job facets include documentation and jobType

**Example Structure:**
```json
{
  "eventType": "COMPLETE",
  "eventTime": "2024-01-15T10:00:00.000Z",
  "job": {
    "namespace": "<job-namespace>",
    "name": "<job-name>",
    "facets": {
      "documentation": {
        "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
        "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DocumentationJobFacet.json",
        "description": "Syncs customer data from CRM to warehouse"
      },
      "jobType": {
        "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
        "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/JobTypeJobFacet.json",
        "processingType": "BATCH",
        "integration": "IBM watsonx.data intelligence custom lineage"
      }
    }
  },
  "inputs": [...],
  "outputs": [...],
  "producer": "https://github.com/IBM/data-intelligence-mcp-server"
}
```

### Dataset Facets

**Schema Facet:**
```json
{
  "schema": {
    "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
    "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SchemaDatasetFacet.json",
    "fields": [
      {
        "name": "customer_id",
        "type": "INTEGER",
        "description": "Unique customer identifier"
      }
    ]
  }
}
```

**DataSource Facet (for inputs):**
```json
{
  "dataSource": {
    "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
    "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DataSourceDatasetFacet.json",
    "name": "CRM Database",
    "uri": "jdbc:oracle:thin:@crm-host:1521:CRMDB"
  }
}
```

**Hierarchy Facet (for both inputs and outputs):**
```json
{
  "hierarchy": {
    "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
    "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/HierarchyDatasetFacet.json",
    "levels": [
      {
        "name": "database",
        "value": "CRMDB"
      },
      {
        "name": "schema",
        "value": "public"
      },
      {
        "name": "table",
        "value": "customers"
      }
    ]
  }
}
```

**Understanding Hierarchy Facet:**

The hierarchy facet describes the organizational structure of a dataset within its system, representing the path from top-level container to specific dataset.

**Common Hierarchy Patterns:**
1. **Relational Databases (3 levels):** database → schema → table (Example: `CRMDB` → `public` → `customers`)
2. **Cloud Storage (variable levels):** bucket → folder → subfolder → file (Example: `my-bucket` → `data` → `2024` → `customers.parquet`)
3. **Data Warehouses (3-4 levels):** warehouse → database → schema → table (Example: `prod-warehouse` → `analytics` → `public` → `sales`)
4. **File Systems (variable levels):** volume → directory → subdirectory → file (Example: `/data` → `raw` → `crm` → `customers.csv`)

**When to Use:** Always include for datasets with clear organizational structure. Helps with dataset discovery, navigation, filtering, and grouping in lineage visualization.

**Best Practices:**
- Use consistent level names across similar systems (e.g., always use "schema" not "schemaName")
- Order levels from highest to lowest (most general to most specific)
- Include all meaningful levels (don't skip intermediate levels)
- Use actual values from the system, not placeholders

**ColumnLineage Facet (for outputs):**
```json
{
  "columnLineage": {
    "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
    "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/ColumnLineageDatasetFacet.json",
    "fields": {
      "customer_id": {
        "inputFields": [
          {
            "namespace": "<source-dataset-namespace>",
            "name": "<source-dataset-name>",
            "field": "cust_id",
            "transformations": [
                {
                    "type": "DIRECT",
                    "subType": "IDENTITY"
                }
            ]
          }
        ]
      },
      "customer_account_number": {
        "inputFields": [
          {
            "namespace": "<source-dataset-namespace>",
            "name": "<source-dataset-name>",
            "field": "cust_account",
            "transformations": [
                {
                    "type": "DIRECT",
                    "subtype": "TRANSFORMATION",
                    "description": "replace(cust_account, 'xxx')",
                    "masking": true
                }
            ]
          }
        ]
      }
    }
  }
}
```

## AI-Assisted Lineage Discovery

### Understanding Data Lineage

**What IS Data Lineage:**
- Movement of data from one location to another (source → destination)
- Transformation of data (calculations, aggregations, filtering)
- Reading data from a dataset and writing to another dataset
- Data flow through processing steps or jobs
- Column-level mappings showing which source fields populate target fields

**What IS NOT Data Lineage:**
- Configuration files or parameter definitions (unless they define data flows)
- Logging or monitoring operations (unless they capture actual data)
- Authentication or authorization checks
- Metadata operations that don't move data (e.g., schema validation without data transfer)
- Control flow logic without data movement (if/else, loops without data operations)
- Comments or documentation text (unless describing actual data flows)

### Code Analysis Patterns

#### Python Code
**Look for:**
1. **Data Reading:** `pd.read_csv()`, `pd.read_sql()`, `spark.read.parquet()` → INPUT datasets
2. **Data Writing:** `df.to_csv()`, `df.to_sql()`, `df.write.parquet()` → OUTPUT datasets
3. **Transformations:** `df['total'] = df['price'] * df['quantity']` → Column-level transformations
4. **Column Mappings:** `df['customer_name'] = df['first_name'] + ' ' + df['last_name']`, `df.rename()` → Column lineage

**Ignore:** Import statements, function definitions without data operations, logging, configuration loading, error handling without data operations

#### SQL Code
**Look for:**
1. **SELECT with INSERT/CREATE:** `INSERT INTO target SELECT ... FROM source` → Input: source, Output: target
2. **CREATE TABLE AS SELECT:** `CREATE TABLE summary AS SELECT ... FROM transactions` → Input: transactions, Output: summary
3. **Column Transformations:** `SELECT customer_id, UPPER(customer_name) as name, price * quantity as total` → Column mappings with transformations

**Ignore:** DDL without data movement (`CREATE TABLE` schema only), GRANT/REVOKE, SET statements, comments

**How to construct names:** Entities like tables and stored procedures might already be referenced by their qualified names. You can also use context, for example, see what is the current active schema at the point when a table is created.

#### Java/Spark Code
**Look for:**
1. **Data Source Connections:** `spark.read().format("jdbc").option("dbtable", "customers").load()` → Input dataset
2. **Transformations:** `df.withColumn("full_name", concat(col("first_name"), lit(" "), col("last_name")))` → Column transformation
3. **Data Writes:** `df.write().format("parquet").save("s3://bucket/output")` → Output dataset

**Ignore:** Configuration objects, connection pool setup, exception handling, utility methods without data operations

### Documentation Analysis

#### Architecture Diagrams
**Look for:**
1. Boxes/Nodes representing systems (database icons, application boxes, storage systems)
2. Arrows/Lines showing data flow (arrows from source to target, labels indicating data movement)
3. Process/Job boxes (transformation steps, job names, processing descriptions)

**Extract:** System names, dataset names, job/process names, flow direction

**Ignore:** Network connections (unless data flows), user access paths, monitoring/alerting flows, API calls that don't transfer data

#### Text Documentation
**Look for phrases indicating lineage:**
- "Data flows from X to Y"
- "Reads from [source] and writes to [target]"
- "Extracts data from [system]"
- "Loads data into [destination]"
- "Transforms [field] by [operation]"
- "Syncs [source] with [target]"
- "Populates [table] from [source]"

**Column mapping indicators:**
- "Maps [source_col] to [target_col]"
- "[field] is derived from [source_field]"
- "Renames [old_name] to [new_name]"
- "Calculates [field] as [formula]"

**Ignore:** General system descriptions without data flows, user interface descriptions, business logic without data operations, historical context

### Lineage Discovery Process

**Step 1: Identify Data Sources**
Scan for: Database connections (JDBC URLs, connection strings), file paths (CSV, Parquet, JSON), API endpoints that return data, message queues/topics (Kafka, RabbitMQ), cloud storage (S3, Azure Blob, GCS)

Extract: System type, connection details, dataset names

Ask for missing information: If unclear from inputs what are the involved technologies, their hostnames, ports, or other necessary inputs, ask the user to provide this information.

**Step 2: Identify Data Destinations**
Scan for: Write operations (INSERT, UPDATE, CREATE TABLE), file write operations, API POST/PUT operations with data, message publishing operations

Extract: Target system type, target dataset names, write patterns (append, overwrite, upsert)

Ask for missing information: If unclear from inputs what are the involved technologies, their hostnames, ports, or other necessary inputs, ask the user to provide this information.

**Step 3: Identify Transformations**
Look for: Column calculations/derivations, filtering conditions (WHERE clauses), aggregations (GROUP BY, SUM, AVG), joins between datasets, data type conversions, string manipulations

Document: Transformation type (IDENTITY, MASKED, TRANSFORMATION), transformation description, input fields used, output field produced

**Step 4: Map Column Lineage**
For each output column, determine: Which input column(s) it comes from, what transformation is applied, whether it's a direct copy, renamed, or calculated

Create mappings: `output_column → [input_dataset.input_column] (transformation_type)`

**Step 5: Validate Discovered Lineage**
Ask yourself:
- ✓ Does data actually move from source to destination?
- ✓ Is there a clear job/process that performs this movement?
- ✓ Can I identify the input and output datasets?
- ✓ Are the column mappings logical and complete?
- ✗ Am I confusing configuration with data flow?
- ✗ Am I including operations that don't move data?

**Step 6: Present Findings to User**
```
I've analyzed the [code/documentation] and discovered the following lineage:

Source: [system].[dataset]
  Columns: [list]

Job: [job-name]
  Description: [what it does]
  
Target: [system].[dataset]
  Columns: [list]

Column Mappings:
  [source] → [target] ([transformation])

Does this match your understanding? Are there any corrections needed?
```

### Common Pitfalls to Avoid

1. **False Positive: Configuration Files** - ❌ Don't treat config files as data sources unless they're actually read as data. ✓ Only document if the config data flows into a dataset.
2. **False Positive: Metadata Operations** - ❌ Schema validation, data profiling, or quality checks aren't lineage. ✓ Only document if data is actually transformed or moved.
3. **False Positive: Temporary Variables** - ❌ Intermediate variables in code aren't datasets. ✓ Only document persistent datasets (tables, files, topics).
4. **Missing Context: Incomplete Transformations** - ❌ Don't guess at transformations if not clear in code. ✓ Ask user to clarify ambiguous transformations.
5. **Over-Specification: Too Much Detail** - ❌ Don't document every line of code. ✓ Focus on data movement and significant transformations.

## JobEvent Creation Instructions

### Step 1: Gather Required Information
Collect all necessary details through conversation:
- Understand what are the technologies involved
- Review the generic naming conventions below, and retrieve official naming conventions for the involved technologies https://openlineage.io/docs/spec/naming
- Job namespace and name. Make sure to follow the naming conventions above. For the Job name, if a naming convention for the technology of the Job is defined, follow it strictly and make sure to use the right number of segments with the right values.
- Job description and type (BATCH, STREAMING, etc.)
- Input datasets (namespace, name, columns, data types). Make sure to follow the naming conventions above. For the dataset name, if a naming convention for the technology of the dataset is defined, follow it strictly and make sure to use the right number of segments with the right values.
- Output datasets (namespace, name, columns, data types). Make sure to follow the naming conventions above. For the dataset name, if a naming convention for the technology of the dataset is defined, follow it strictly and make sure to use the right number of segments with the right values.
- Dataset hierarchy information (levels such as database - where relevant as some databases don't have a concept of logical database names, schema where relevant as some databases don't have a concept of schemas, table with their values)
- Column mappings and transformations
- Data source connection URIs

### Step 2: Construct the JobEvent JSON
Build the JSON structure following this template:

```json
{
  "eventType": "COMPLETE",
  "eventTime": "<current-ISO-8601-timestamp>",
  "job": {
    "namespace": "<job-namespace>",
    "name": "<job-name>",
    "facets": {
      "documentation": {
        "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
        "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DocumentationJobFacet.json",
        "description": "<job-description>"
      },
      "jobType": {
        "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
        "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/JobTypeJobFacet.json",
        "processingType": "<BATCH|STREAMING>",
        "integration": "IBM watsonx.data intelligence custom lineage"
      }
    }
  },
  "inputs": [
    {
      "namespace": "<input-namespace>",
      "name": "<input-dataset-name>",
      "facets": {
        "schema": {
          "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
          "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SchemaDatasetFacet.json",
          "fields": [
            {
              "name": "<field-name>",
              "type": "<field-type>",
              "description": "<field-description>"
            }
          ]
        },
        "dataSource": {
          "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
          "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/DataSourceDatasetFacet.json",
          "name": "<source-system-name>",
          "uri": "<connection-uri>"
        },
        "hierarchy": {
          "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
          "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/HierarchyDatasetFacet.json",
          "levels": [
            {
              "name": "<level-name>",
              "value": "<level-value>"
            }
          ]
        }
      }
    }
  ],
  "outputs": [
    {
      "namespace": "<output-namespace>",
      "name": "<output-dataset-name>",
      "facets": {
        "schema": {
          "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
          "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/SchemaDatasetFacet.json",
          "fields": [
            {
              "name": "<field-name>",
              "type": "<field-type>",
              "description": "<field-description>"
            }
          ]
        },
        "hierarchy": {
          "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
          "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/HierarchyDatasetFacet.json",
          "levels": [
            {
              "name": "<level-name>",
              "value": "<level-value>"
            }
          ]
        },
        "columnLineage": {
          "_producer": "https://github.com/IBM/data-intelligence-mcp-server",
          "_schemaURL": "https://openlineage.io/spec/facets/1-0-0/ColumnLineageDatasetFacet.json",
          "fields": {
            "<output-field-name>": {
              "inputFields": [
                {
                  "namespace": "<input-namespace>",
                  "name": "<input-dataset>",
                  "field": "<input-field>",
                  "transformations": [
                      {
                          "type": "<DIRECT or INDIRECT>",
                          "subtype": "<IDENTITY, TRANSFORMATION, or AGGREGATION for DIRECT type, JOIN, GROUP_BY, FILTER, SORT, WINDOW, CONDITIONAL for INDIRECT type>",
                          "description": "<transformation formula provided only if 'type' is not 'IDENTITY' - it should show the source column(s) and the operation performed with them, e.g. sum(ammount)>",
                          "masking": "<true (boolean value) if input is hashed or aggregation function like count is used>"
                      }
                  ]
                }
              ]
            }
          }
        }
      }
    }
  ],
  "producer": "https://github.com/IBM/data-intelligence-mcp-server"
}
```

### Step 3: Populate All Fields
- **producer** in the root and **_producer** in all facets should be https://github.com/IBM/data-intelligence-mcp-server
- **eventTime**: Generate current timestamp in ISO-8601 format (e.g., `2024-01-15T10:00:00.000Z`)
- **job.namespace**: Use the job namespace corresponding to the technology of the job, host, and port if provided (`technology://host:port`)
- **job.name**: Use the job name based on the processed inputs, formatted according to the best practices
- **job.facets.documentation.description**: Use the job description from conversation
- **job.facets.jobType.processingType**: Set to "BATCH" or "STREAMING" based on job type
- **inputs**: Create array with all input datasets
- **outputs**: Create array with all output datasets
- **For datasets**:
  - namespace: Use the dataset namespace corresponding to the technology of the dataset, host, and port if provided (`technology://host:port`)
  - name: Use the dataset name based on the processed inputs, formatted according to the best practices
  - Include hierarchy facet with appropriate levels (e.g., database, schema, table)
  - Include schema facet with all fields (and if user provided them, also with their types)
  - Include columnLineage facet on outputs if user specified how the transformation moves data, otherwise don't include this - lineage will be derived from the schema

### Step 4: Validate the Generated JSON

**Structure Validation:**
- ✓ eventType is "COMPLETE"
- ✓ eventTime is valid ISO-8601 format
- ✓ job object exists with namespace and name
- ✓ NO "run" object present (critical for JobEvent)

**Content Validation:**
- ✓ All namespaces follow dot notation convention (for technologies defined in https://openlineage.io/docs/spec/naming follow the naming convention)
- ✓ All dataset names are properly qualified (for technologies defined in https://openlineage.io/docs/spec/naming follow the naming convention)
- ✓ https://github.com/IBM/data-intelligence-mcp-server is used as the value for all _producer fields
- ✓ All schema fields have name, and optionally type and description
- ✓ All columnLineage mappings reference valid input fields
- ✓ Column names in columnLineage match schema field names

**Facet Validation:**
- ✓ All facets have _producer and _schemaURL
- ✓ Schema URLs point to correct OpenLineage spec versions
- ✓ Hierarchy facets include levels array with name and value for each level

**JSON Syntax:**
- ✓ Valid JSON syntax (no trailing commas, proper quotes)
- ✓ All brackets and braces properly closed
- ✓ No undefined or null values where not allowed

### Step 5: Present for User Review
Before finalizing, show the user a summary:
```
I've prepared the following JobEvent:

Job: <namespace>.<name>
Description: <description>
Type: <BATCH|STREAMING>

Inputs:
  - <namespace>.<dataset> (<column-count> columns)

Outputs:
  - <namespace>.<dataset> (<column-count> columns)

Column Mappings: <count> mappings defined

Does this look correct?
```

### Step 6: Save the JobEvent and Prepare ZIP File
Once validated and approved:
1. Save the JSON to a file named: `<job-namespace>_<job-name>_jobevent.json`, replace all special characters like slashes and colons by underscores
2. Package the JobEvent file(s) into a ZIP file for MDI ingestion
3. Inform user that the ZIP file has been created successfully

## Best Practices

### Naming Conventions

**Job Namespaces:** Use format: `technology://host:port` (Examples: `oracle://internal.myorg.com:1551`, `datastage://dsserver:443`). Be consistent across related jobs and datasets.

**Dataset Namespaces:** Use known best practices https://openlineage.io/docs/spec/naming. Where not defined, use common pattern: `technology://host:port` (Examples: `mysql://production:8080`, `awsathena://athena.dallas.amazonaws.com`). Be consistent across related jobs and datasets.

**Job Names:**
- Use known best practices for technologies that have them defined https://openlineage.io/docs/spec/naming
- Per each technology, check how many segments the name is expected to have and what is their meaning. This is different for each technology.
- If the job represents a database transformation like a stored procedure or function, follow the defined best practices (https://openlineage.io/docs/spec/naming) for the datasets for given technology, and only change the last name segment to the name of the transformation. For example, if the job represents Oracle stored procedure, use the following pattern (because this is the generic pattern for Oracle): `schema.storedprocedure`
- Use qualified names: `project.job`, `directory.script`, `database.schema.storedprocedure`, etc (Examples: `mydatastageproject.load_jobs`, `warehouse.staging.load_orders`)
- Include full path for clarity

**Dataset Names:**
- Use known best practices https://openlineage.io/docs/spec/naming
- Per each technology, check how many segments the name is expected to have and what is their meaning. This is different for each technology.
- Use qualified names: `database.schema.table`, `schema.table`, `folder.file` (Examples: `crm.public.customers`, `staging.orders`)
- Include full path for clarity

### Column Lineage Structure

**Transformation Types:**
- `IDENTITY`: Direct copy, no transformation
- `AGGREGATION`: Data is aggregated using functions like sum or count
- `TRANSFORMATION`: Calculation or complex logic

**Best Practices:**
- Always include transformationDescription unless the transformation type is `IDENTITY`
- List all inputFields that contribute to output
- Be specific about calculations if information is available

## Error Handling

**Missing Information:** "I need a bit more information to complete the lineage documentation. Could you provide [specific missing information]?"

**Invalid Data:** "I noticed [specific issue]. Could you verify [specific field]? For example, [provide example of correct format]."

**Ambiguous Inputs:** "I want to make sure I understand correctly. When you say [ambiguous statement], do you mean [interpretation A] or [interpretation B]?"

**Incomplete Schemas:** "To create accurate column-level lineage, I need the column names and types for [dataset]. Could you provide those?"

## Limitations

**What the agent CAN do:**
- Document static job lineage relationships
- Generate valid OpenLineage JobEvents
- Parse common code formats for lineage discovery
- Validate payloads against OpenLineage schema

**What the agent CANNOT do:**
- Execute actual data transformations
- Access live systems to discover lineage automatically
- Create RunEvents (execution-specific events)
- Guarantee 100% accuracy in AI-assisted discovery

**When to escalate:** Complex transformations requiring deep technical analysis, systems with proprietary or undocumented formats

## Validation Reference

### OpenLineage Schema Validation
All generated JobEvents must validate against: https://github.com/OpenLineage/OpenLineage/blob/main/spec/OpenLineage.json

**Key JobEvent Requirements:**
- Extends BaseEvent (eventType, eventTime, producer)
- Has required `job` object
- May have `inputs` and `outputs` arrays
- Must NOT have `run` object

### Pre-Ingestion Checklist
- [ ] eventType is "COMPLETE"
- [ ] eventTime in ISO-8601 format
- [ ] job.namespace defined in format `technology://host:port`
- [ ] job.name defined
- [ ] No "run" object present
- [ ] All namespaces follow conventions (typically in format `technology://host:port`)
- [ ] Column names match in schema and columnLineage
- [ ] JSON syntax valid
- [ ] Validates against OpenLineage JobEvent schema

### Additional Instructions
- Do not generate any other file outputs other than the OpenLineage events (JSON files) and the ZIP file.
