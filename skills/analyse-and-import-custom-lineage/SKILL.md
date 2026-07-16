---
name: analyse-and-import-custom-lineage
description: Use this skill to help users document custom lineage in watsonx.data intelligence using OpenLineage JobEvents for systems without automated scanning capabilities. Use this skill whenever user can provide any of these inputs for this agent to understand and document custom lineage a) user knows how some system, that is not supported for automated lineage scanning by watsonx.data intelligence, works b) user has architecture diagrams, specifications, or technical documentation for some system c) user has source code of transfromations
---

## Core Capabilities
- Interactive lineage information gathering through conversation
- AI-assisted lineage discovery from documentation and code
- OpenLineage JobEvent payload generation
- Lineage visualization and validation

## Common Guidelines for Using This Skill

The purpose of this skill is process the inputs users provide, identify data lineage entities (datasets and job), data lineage relationships, capture additional context metadata, and generate OpenLineage JobEvent payloads representing all of this information.

### Never Invent Technical Details

The skill should document lineage at the maximum granularity based on the provided inputs, but never invent any information that isn't explicitly provided in the user's input.

### Identify data source and target coordinates precisely

Technology, hostname, and port number are critical for system identification and cross-system lineage stitching. 

If the source code, documentation, or user input does NOT explicitly contain:
- Hostnames
- Port numbers
- Connection strings
- Technology identifiers
- Any other technical coordinates

**YOU MUST:**
1. **STOP** processing immediately
2. **ASK** the user to provide the missing information
3. **NEVER** invent, assume, or guess these values

### Required Information Collection

**For Source/Target Systems (mandatory):**
- System name and type
- Namespace (e.g., 'production.crm')
- Dataset/table name
- Hierarchy structure (e.g., database > schema > table)
- Hierarchy level values (e.g., database: 'CRMDB', schema: 'public', table: 'customers')
- Columns

**For Source/Target Systems (optional):**
- Data types for columns
- Connection URI

**For Job Information (mandatory):**
- Tool/system name and type
- Job/process name
- Job description

**For Job Information (optional):**
- Processing type (BATCH, STREAMING, etc.)

**For Transformations (optional):**
- Column mappings
- Column renames
- Calculated/derived columns
- Filters/aggregations
- System-generated columns

**When Information is Missing - MANDATORY PROTOCOL:**

**STOP IMMEDIATELY** if you cannot determine from the provided inputs:
- Technology type (Oracle, Snowflake, PostgreSQL, etc.)
- Hostname, port number, server address, account name, or another data source identifier for given technology
- Database name (if applicable)
- Any other identifying coordinates

**REQUIRED ACTION:** Ask the user explicitly:
"I cannot find [specific missing information] in the [source code/documentation]. To create correct OpenLineage namespaces, I need you to provide:
- [List specific missing items]"

### Naming Conventions (Apply to All JobEvents)

**Review Official Conventions:**
Before creating JobEvents, review generic naming conventions and retrieve official naming conventions for the involved technologies from assets/openlineage_naming_conventions.md

**Job Namespaces:**
- Format: `technology://host:port`
- Examples: `oracle://internal.myorg.com:1551`, `datastage://dsserver:443`
- Be consistent across related jobs and datasets

**Job Names:**
- Use known best practices for technologies that have them defined at assets/openlineage_naming_conventions.md
- Per each technology, check how many segments the name is expected to have and what is their meaning
- If the job represents a database transformation like a stored procedure or function, follow the defined best practices for the datasets for given technology, and only change the last name segment to the name of the transformation (Example for Oracle stored procedure: `schema.storedprocedure`)
- Use qualified names: `project.job`, `directory.script`, `database.schema.storedprocedure`
- Examples: `mydatastageproject.load_jobs`, `warehouse.staging.load_orders`
- Include full path for clarity

**Dataset Namespaces:**
- Use known best practices from assets/openlineage_naming_conventions.md
- Where not defined, use common pattern: `technology://host:port`
- Examples: `mysql://production:8080`, `awsathena://athena.dallas.amazonaws.com`
- Be consistent across related jobs and datasets

**Dataset Names:**
- Use known best practices from assets/openlineage_naming_conventions.md
- Per each technology, check how many segments the name is expected to have and what is their meaning
- Use qualified names: `database.schema.table`, `schema.table`, `folder.file`
- Examples: `crm.public.customers`, `staging.orders`
- Include full path for clarity

**Name Construction from Context:**
- Entities like tables and stored procedures might already be referenced by their qualified names
- Use context (e.g., current active schema at the point when a table is created)

### Response Formats (Use for Both Workflows)

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

### Error Handling 
- Always request missing required information before proceeding
- Ask for verification when data appears invalid or inconsistent
- Seek clarification when inputs are ambiguous or have multiple interpretations

## Workflows

### Workflow 1: User-Directed Lineage Documentation
**When to use:** User knows the lineage structure and can describe it explicitly.

**Process:** Engage in conversation → Generate JobEvents → Present summary → Incorporate feedback → Package ZIP

**Prerequisites:** User has knowledge of source/target systems, transformations, and optionally column mappings.

### Workflow 2: AI-Assisted Lineage Discovery
**When to use:** User has documentation, diagrams, or code that describes the lineage.

**Process:** Analyze materials → Extract data flows → Propose lineage → Validate with user → Refine → Package ZIP

**Prerequisites:** User can provide relevant documentation/code with sufficient detail and validate discovered lineage.



## Workflow 2 Specific: AI-Assisted Lineage Discovery

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

### Input processing methodology
- Bellow, in Code Analysis Patters, we define what to look for when searching for lineage
- When presented with a set of code inputs (scripts, programs, etc), proceed in the following way
   - Process each file independently
   - For each file, first identify what transformation entities it contains (stored procedures, sql statements, file movement commands, etc). 
   - Create a list of the transformations you will analyse in a separate file. At the top add a count of number of occurances for each transformation type. You will use this as a counter. Bellow, list all of them (provide transformation type and location in the file). You will use this as a todo-list.
   - The proceed to analysing each of these transformation one-by-one, and create an OpenLineage payload for each relevant transformation. 
   - Track the progress in your progress file.  

### Code Analysis Patterns

Identify the programming language that you are analyzing, and load the relevant lineage guide: references/<programming_language>_lineage_guide.md. Follow the relevant guide. If guide is not available for specific language, extrapolate the principles from the other guides. 

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

**Step 1: Identify Data Sources, Targets, and Jobs **

Jobs: 
- write operations (INSERT, UPDATE, CREATE TABLE AS INSERT statements)
- file write operations
- API POST/PUT operations with data
- message publishing operations
- Break down complex scripts to individual operations and document each of them as a separate job. 
- For example, a job should be  a single SQL statement, a single file load, a single stored procedure, a single function, etc. 
- If a complex pipeline consist of several independent data movements, document each as a separate job (and JobEvent), and use the intermediate result storages (tables, files, temporary tables, in memory data)

Data sources: 
- Database connections (JDBC URLs, connection strings)
- file paths (CSV, Parquet, JSON)
- API endpoints that return data
- message queues/topics (Kafka, RabbitMQ)
- cloud storage (S3, Azure Blob, GCS)

Extract: System type, connection details, dataset names

Targets: 
- Targets of write operations (INSERT, UPDATE, CREATE TABLE AS INSERT statements)
- Targets of file write operations
- Targets of API POST/PUT operations with data
- Targets of message publishing operations

Extract: Target system type, target dataset names, write patterns (append, overwrite, upsert)


**Ask for missing information:** If unclear from inputs what are the involved technologies, their hostnames, ports, or other necessary inputs, ask the user to provide this information.

**MANDATORY CHECKPOINT:** Before proceeding to Step 2, verify you have ACTUAL values (not invented) for all data sources. If ANY information is missing or unclear, STOP and ask the user.


**Step 2: Identify Individual Transformations**
Look for: 
**DIRECT lineage** - Source column values flow into the output column (possibly transformed):
- Column calculations/derivations (e.g., price * quantity)
- Aggregation functions (SUM, AVG, COUNT, MIN, MAX) - use subtype AGGREGATION
- Data type conversions and string manipulations
- GROUP BY columns that appear in SELECT - use subtype IDENTITY (the distinct values flow through)
- Column renames or CASE statements

**INDIRECT lineage** - Source column influences the result but values don't flow to output:
- WHERE clause filtering conditions (determines which rows are included)
- JOIN conditions (determines how tables are matched)
- HAVING clause conditions (filters aggregated results)
- ORDER BY, PARTITION BY (affects row ordering/grouping but not output values)

**Special Case - GROUP BY Columns:**
- Columns in both SELECT and GROUP BY: Use DIRECT/IDENTITY (values flow through as distinct values)
- Columns only in GROUP BY (not in SELECT): Use INDIRECT/GROUP_BY (only influences grouping)

This list of operations is not exhaustive - are just common cases. Make sure you identify all the data movements within a script, even if they are not performed using one of these mechanisms. 

Always document ONLY direct lineage if a particular source acts as both direct and indirect source.

Document: Transformation type (DIRECT, INDIRECT), subtype (IDENTITY, MASKED, TRANSFORMATION), transformation description, input fields used, output field produced


**Step 3: Map Column Lineage**
For each output column, determine: Which input column(s) it comes from, what transformation is applied, whether it's a direct copy, renamed, or calculated

Create mappings: `output_column → [input_dataset.input_column] (transformation_type)`

**Step 4: Validate Discovered Lineage**
Ask yourself:
- Does data actually move from source to destination?
- Is there a clear job/process that performs this movement?
- Can I identify the input and output datasets?
- Are the column mappings logical and complete?
- ✗ Am I confusing configuration with data flow?
- ✗ Am I including operations that don't move data?

**Step 5: Present Findings to User**
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

1. **False Positive: Configuration Files** - ❌ Don't treat config files as data sources unless they're actually read as data. Only document if the config data flows into a dataset.
2. **False Positive: Metadata Operations** - ❌ Schema validation, data profiling, or quality checks aren't lineage. Only document if data is actually transformed or moved.
3. **False Positive: Temporary Variables** - ❌ Intermediate variables in code aren't datasets. Only document persistent datasets (tables, files, topics).
4. **Missing Context: Incomplete Transformations** - ❌ Don't guess at transformations if not clear in code. Ask user to clarify ambiguous transformations.
5. **Over-Specification: Too Much Detail** - ❌ Don't document every line of code. Focus on data movement and significant transformations.

## OpenLineage JobEvent Structure

JobEvents document static job lineage without execution-specific run information.

**Required Fields:**
- `eventTime`: ISO-8601 current timestamp
- `job`: Object with namespace, name, and facets
- `producer`: "https://github.com/IBM/data-intelligence-mcp-server"

**Key Characteristics:**
- NO `run` object (distinguishes JobEvent from RunEvent)
- NO `eventType`(irrelevant for JobEvent)
- Includes `inputs` and `outputs` arrays
- Job facets include documentation and jobType

See the structure of the Job Event in assets/openlineage_payload_template.json. 


### Dataset Facets
The following dataset facets should be included in the payload:
- `SchemaDatasetFacet` (inputs and outputs, provide whenever you have information about columns, reference: assets/openlineage_schema_facet_example.json)
- `DataSourceDatasetFacet` (inputs and outputs, provide always to capture details of the datasource, reference: assets/openlineage_datasource_facet_example.json)
- `HierarchyDatasetFacet` (inputs and outputs, provide always to capture the names and types of dataset parent entities, reference: assets/openlineage_hierarchy_facet_example.json). Common hierarchy levels are below, but always reflect the actual hierarchy based on what you know about the dataset.
  - Relational Databases (3 levels): database → schema → table (Example: `CRMDB` → `public` → `customers`)
  - Cloud Storage (variable levels): bucket → folder → subfolder → file (Example: `my-bucket` → `data` → `2024` → `customers.parquet`)
  - Data Warehouses (3-4 levels): warehouse → database → schema → table (Example: `prod-warehouse` → `analytics` → `public` → `sales`)
  - File Systems (variable levels): volume → directory → subdirectory → file (Example: `/data` → `raw` → `crm` → `customers.csv`)
- `ColumnLineageFacet` (outputs only, provide provide whenever column lineage information is known, reference: assets/openlineage_columnlineage_facet_example.json).  


## JobEvent Creation Instructions

### Step 1: Gather Required Information
Collect all necessary details through conversation:
- Understand what are the technologies involved
- Review the naming conventions in "Common Guidelines" section above
- Retrieve official naming conventions for the involved technologies from assets/openlineage_naming_conventions.md
- Job namespace and name (follow naming conventions strictly, use right number of segments with right values)
- Job description and type (BATCH, STREAMING, etc.)
- Input datasets (namespace, name, columns, data types) - follow naming conventions strictly
- Output datasets (namespace, name, columns, data types) - follow naming conventions strictly
- Dataset hierarchy information (levels such as database, schema, table with their values - where relevant as some databases don't have concept of logical database names or schemas)
- Column mappings and transformations
- Data source connection URIs

**VALIDATION CHECKPOINT - MANDATORY:**

Before proceeding to Step 2, verify you have ACTUAL values (not invented) for:
- [ ] Technology type (from code or user)
- [ ] Hostname, port, or any other relevant data source identifier (from code or user) - NOT invented
- [ ] Port (from code or user) - NOT invented
- [ ] All namespace components

**If ANY checkbox is unchecked:** STOP and ask user for missing information.

### Step 2: Construct the JobEvent JSON
Generate one Job event per job. Each Job event should be captured in a separate JSON document. 

Build the JSON structure following the template stored in file assets/openlineage_payload_template.json

### Step 3: Populate All Fields

** NAMESPACE VALIDATION - MANDATORY:**

Before setting namespace values, verify hostname and port are:
- [ ] From actual source code OR
- [ ] Explicitly provided by user
- [ ] NOT invented/assumed/guessed

**If verification fails:** STOP and ask user.

- **producer** in the root and **_producer** in all facets should be https://github.com/IBM/data-intelligence-mcp-server
- **eventTime**: Generate current timestamp in ISO-8601 format (e.g., `2024-01-15T10:00:00.000Z`)
- **job.namespace**: Use the job namespace corresponding to the technology of the job, host, and port if provided (`technology://host:port`)
- **job.name**: Use the job name based on the processed inputs, formatted according to the naming conventions
- **job.facets.documentation.description**: Use the job description from conversation
- **job.facets.jobType.processingType**: Set to "BATCH" or "STREAMING" based on job type
- **inputs**: Create array with all input datasets
- **outputs**: Create array with all output datasets
- **For datasets**:
  - namespace: Use the dataset namespace corresponding to the technology of the dataset, host, and port if provided (`technology://host:port`)
  - name: Use the dataset name based on the processed inputs, formatted according to the naming conventions
  - Include hierarchy facet with appropriate levels (e.g., database, schema, table)
  - Include schema facet with all fields (and if user provided them, also with their types)
  - Include columnLineage facet on outputs if user specified how the transformation moves data, otherwise don't include this - lineage will be derived from the schema

### Step 4: Validate the Generated JSON


**Automated Validation:**
Before packaging, run the automated validation script to ensure all JobEvents are valid:

Run the validation script on all generated JobEvent files:
```bash
python skills/analyse-and-import-custom-lineage/scripts/validate_jobevent.py <jobevent_file.json>
```

Or validate all JSON files in a directory:
```bash
python skills/analyse-and-import-custom-lineage/scripts/validate_jobevent.py <directory_path>
```

**Content Validation:**
- All namespaces follow naming conventions from assets/openlineage_naming_conventions.md
- All dataset names follow naming conventions from assets/openlineage_naming_conventions.md
- All columnLineage mappings reference valid input fields
- Column names in columnLineage match schema field names


- If ALL validations pass: Proceed to Step 5
- If ANY validation fails: Fix the issues in the JSON files and re-run validation


### Step 5: Save the JobEvent and Prepare ZIP File
Once validated and approved:
1. Save the JSON to a file named: `<job-namespace>_<job-name>_jobevent.json`, replace all special characters like slashes and colons by underscores
2. Run the validation script (Step 6) to ensure all JobEvents are valid
3. Package the JobEvent file(s) into a ZIP file for MDI ingestion
4. Inform user that the ZIP file has been created successfully and validation passed

## Column Lineage Best Practices

Understand difference between direct and indirect lineage. 

**DIRECT lineage** - Source column values flow into the output column (possibly transformed):
- Column calculations/derivations (e.g., price * quantity)
- Aggregation functions (SUM, AVG, COUNT, MIN, MAX) - use subtype AGGREGATION
- Data type conversions and string manipulations
- GROUP BY columns that appear in SELECT - use subtype IDENTITY (the distinct values flow through)
- Column renames or CASE statements

**INDIRECT lineage** - Source column influences the result but values don't flow to output:
- WHERE clause filtering conditions (determines which rows are included)
- JOIN conditions (determines how tables are matched)
- HAVING clause conditions (filters aggregated results)
- ORDER BY, PARTITION BY (affects row ordering/grouping but not output values)

**Special Case - GROUP BY Columns:**
- Columns in both SELECT and GROUP BY: Use DIRECT/IDENTITY (values flow through as distinct values)
- Columns only in GROUP BY (not in SELECT): Use INDIRECT/GROUP_BY (only influences grouping)

Always document ONLY direct lineage if a particular source acts as both direct and indirect source.

**INCORRECT**: Grouping multiple operations into end-to-end pipelines
**CORRECT**: One job per independent operation (each PROC SQL, each DATA step, etc.)

**Transformation Types:**
- `IDENTITY`: Direct copy, no transformation
- `AGGREGATION`: Data is aggregated using functions like sum or count
- `TRANSFORMATION`: Calculation or complex logic

**Best Practices:**
- Always include transformationDescription unless the transformation type is `IDENTITY`
- List all inputFields that contribute to output
- Be specific about calculations if information is available

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

### Additional Instructions
- Do not generate any other file outputs other than the OpenLineage events (JSON files) and the ZIP file.
