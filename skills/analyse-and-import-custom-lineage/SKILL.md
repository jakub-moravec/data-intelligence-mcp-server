---
name: analyse-and-import-custom-lineage
description: Use this skill to help users document custom lineage in watsonx.data intelligence using OpenLineage JobEvents for systems without automated scanning capabilities. Use this skill whenever user can provide any of these inputs for this agent to understand and document custom lineage a) user knows how some system, that is not supported for automated lineage scanning by watsonx.data intelligence, works b) user has architecture diagrams, specifications, or technical documentation for some system c) user has source code of transfromations
---

## Core Capabilities
- Interactive lineage information gathering through conversation
- AI-assisted lineage discovery from documentation and code
- OpenLineage JobEvent payload generation
- Lineage visualization and validation

## Core Objective and Principles for This Skill

Objective: Document high-quality data lineage for systems without automated scanning capabilities. Lineage needs to be as precise as possible - no assumptions, no guessing, no invented details. It must be correct enough to be used for regulatory compliance. 

Approach: The skill allows users to process various inputs, identify data lineage entities (datasets and job), data lineage relationships, capture additional context metadata, and generate OpenLineage JobEvent payloads representing all of this information.

KPIs: 
1. Accuracy: Ensure all documented lineage is correct and verifiable, nothing is invented
2. Completeness and granularity: If information is available, document as much detail as possible. Column Lineage whenever possible. But do not invent details if not provided.

Optimizing cost and speed of the process is not a priority. Accuracy and completeness are paramount. Never choose a strategy that will compromise accuracy or completeness.

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

### Required Information For Lineage Documentation

The skill must collect the following information to be able to generate the OpenLineage events: 

**For Source/Target Systems**
- (mandatory) System name, type, host, and port
- (mandatory) Dataset name and type, and names and types of all of it parents (e.g., database, schema for table, directory for file, etc)
- (mandatory for column lineage) Column names 
- (optional) Column types
- (optional) Connection URI

**For Jobs**
- (mandatory) System name, type, host, and port
- (mandatory) Job/process name and type, and names and types of all of it parents (e.g. project for job, etc)
- (mandatory for column lineage) Column mapings capturing the source and corresponding target columns, and the transformation logic applied to create the targets from the sources
- (optional) Job description
- (optional) Processing type (BATCH, STREAMING, etc.)

### Naming Conventions (Apply to All JobEvents)

**Review Official Conventions:**
Make sure to understand and apply naming conventions (assets/openlineage_naming_conventions.md) for individual technologies. This context is needed to know what information to gather for specific technology, and to correctly construct the OpenLineage events.

**Job and Dataset Namespaces:**
- Use known best practices from assets/openlineage_naming_conventions.md
- Where not defined, use common pattern: `technology://host:port`
- Be consistent across related jobs and datasets

**Job Names:**
- Use known best practices for technologies that have them defined at assets/openlineage_naming_conventions.md
- Per each technology, check how many segments the name is expected to have and what is their meaning
- If the job represents a database transformation like a stored procedure or function, follow the defined best practices for the datasets for given technology, and only change the last name segment to the name of the transformation (Example for Oracle stored procedure: `database.schema.storedprocedure`)
- Use qualified names: `project.job`, `directory.script`, `database.schema.storedprocedure.statement`

**Dataset Names:**
- Use known best practices from assets/openlineage_naming_conventions.md
- Per each technology, check how many segments the name is expected to have and what is their meaning
- Use qualified names: `database.schema.table`, `schema.table`, `folder.file`

**Name Construction from Context:**
- Entities like tables and stored procedures might already be referenced by their qualified names
- Use context (e.g., current active schema at the point when a table is created)

### OpenLineage JobEvent Structure - How to Capture the Data Lineage using OpenLineage

OpenLineage JobEvents document static job lineage without execution-specific run information. See the structure of the Job Event in assets/openlineage_payload_template.json. 

**Key Characteristics:**
- NO `run` object (distinguishes JobEvent from RunEvent)
- NO `eventType`(irrelevant for JobEvent)
- Includes `inputs` and `outputs` arrays
- Job facets include documentation and jobType

#### Dataset Facets
The following dataset facets should be included in the payload, for inputs and outputs:

- `SchemaDatasetFacet` (inputs and outputs, provide whenever you have information about columns, reference: assets/openlineage_schema_facet_example.json)
- `DataSourceDatasetFacet` (inputs and outputs, provide always to capture details of the datasource, reference: assets/openlineage_datasource_facet_example.json)
- `HierarchyDatasetFacet` (inputs and outputs, provide always to capture the names and types of dataset parent entities, reference: assets/openlineage_hierarchy_facet_example.json). Common hierarchy levels are below, but always reflect the actual hierarchy based on what you know about the dataset.
  - Relational Databases (3 levels): database → schema → table (Example: `CRMDB` → `public` → `customers`)
  - Cloud Storage (variable levels): bucket → folder → subfolder → file (Example: `my-bucket` → `data` → `2024` → `customers.parquet`)
  - Data Warehouses (3-4 levels): warehouse → database → schema → table (Example: `prod-warehouse` → `analytics` → `public` → `sales`)
  - File Systems (variable levels): volume → directory → subdirectory → file (Example: `/data` → `raw` → `crm` → `customers.csv`)
- `ColumnLineageFacet` (outputs only, provide provide whenever column lineage information is known, reference: assets/openlineage_columnlineage_facet_example.json).  

#### Job Facets

- `DocumentationJobFacet` (provide always to document what the job does, reference: assets/openlineage_job_documentation_facet_example.json) Provide structured content: 
  - Summary: 1-2 sentences describing the job's purpose
  - AI-disclaimer: "This job and related lineage was generated by AI based on <source of information, including specific file and line if relevat>".
- `JobTypeJobFacet` (provide always to capture the type of job, reference: assets/openlineage_job_type_facet_example.json)
- `SourceCodeFacet` (provide always to source code based on which this data lineage was captured, reference: assets/openlineage_job_sourcecode_facet_example.json)

#### Column Lineage Best Practices

Understand difference between direct and indirect lineage. 

**DIRECT lineage** - Source column values flow into the output column (possibly transformed):
- Column calculations/derivations (e.g., price * quantity)
- Aggregation functions (SUM, AVG, COUNT, MIN, MAX) - use subtype AGGREGATION
- Data type conversions and string manipulations
- GROUP BY columns that appear in SELECT - use subtype IDENTITY (the distinct values flow through)
- Column renames or CASE statements
- Use `type` DIRECT for these cases
- Relevant transformation subtypes:
   - `IDENTITY`: Direct copy, no transformation
   - `AGGREGATION`: Data is aggregated using functions like sum or count
   - `TRANSFORMATION`: Calculation or complex logic

**INDIRECT lineage** - Source column influences the result but values don't flow to output:
- WHERE clause filtering conditions (determines which rows are included)
- JOIN conditions (determines how tables are matched)
- HAVING clause conditions (filters aggregated results)
- ORDER BY, PARTITION BY (affects row ordering/grouping but not output values)
- Use `type` INDIRECT for these cases
- Relevant transformation subtypes:
   - `JOIN` - input used in join condition
   - `GROUP_BY` - output is aggregated based on input (e.g. GROUP BY clause)
   - `FILTER` - input used as a filtering condition (e.g. WHERE clause)
   - `SORT` - output is sorted based on input field (e.g. ORDER BY clause)
   - `WINDOW` - output is windowed based on input field
   - `CONDITIONAL` - input value is used in IF, CASE WHEN or COALESCE statements

**Special Case - GROUP BY Columns:**
- Columns in both SELECT and GROUP BY: Use DIRECT/IDENTITY (values flow through as distinct values)
- Columns only in GROUP BY (not in SELECT): Use INDIRECT/GROUP_BY (only influences grouping)

NEVER include two transformations for the same column. If both direct and indirect transformations exist, document only the direct one.
ALWAYS include transformationDescription unless the transformation type is `IDENTITY`
ALWAYS list all inputFields that contribute to output.
ALWAYS provide specific calculations if information is available.

### Error Handling 
- Always request missing required information before proceeding
- Ask for verification when data appears invalid or inconsistent
- Seek clarification when inputs are ambiguous or have multiple interpretations

### Limitations

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

## Workflows

### Workflow 1: User-Directed Lineage Documentation
**When to use:** User knows the lineage structure and can describe it explicitly. They don't have suitable code or documents to analyze. 

<step>
   Retrieve high-level information

   Ask user about 
   - the details of the system they want to document the lineage for (technology name, system name, host, port)
   - what is their goal for the lineage documentation - document the transformations within that system, or document how the system interacts with other systems (cross-system lineage), or both
    - if cross-system lineage is involved, ask about the system details for the related systems as well
   - what is the needed level of detail -  do they need table-level lineage, or column-level lineage
</step>

<step>
  Understand individual transfromations

  Ask for details of specific transformations (according to the common guidelines), their sources, targets, transformation logic. If the user requires column-level lineage, ask for the column names, their data types, and their relationships. 

  If user wants to document only a very high-level lineage, you can even represent the whole system as a single transformation, and focus on the stitching points - inpts and outputs in other systems that this system is reading data from or writing data to.

  Repeat this step for any transformation the user wants to document.
</step>

<step>
   When you collect all the information, proceed with the steps for creating the OpenLineage JSON(s) - section JobEvent Creation Instructions
</step>

<step>
  Ingest events into watsonx.data intelligence

  Follow the steps in section Prepering events for ingestion to watsonx.data intelligence
</step>

### Workflow 2: Analyze Code to Document Custom Lineage
**When to use:** User has code that can be processed to undersatnd the lineage.

<step>
  Code Analysis Patterns 

  Identify the programming language that you are analyzing, and load the relevant lineage guide: references/<programming_language>_lineage_guide.md. Follow the relevant guide. If guide is not available for specific language, extrapolate the principles from the other guides. 
</step>

<step>
  Understand the language structure. The language guide operates with 3 entities 
  - Transformation - the code that moves the data
  - Dataset - the definitions or locations of where data is read from/written to
  - Context - the code that is not a transformation, but needs to be evaluated to correctly interpret the transformation logic or it's source and target datasets
</step>

<step>
  Process the code to construct initial context, store it in a JSON file. Include information about when context is set. If the context configuration is changed later, also include information when that context value is no longer relevant, and store the same information for the new context value. 
  Store and continuously update the context in file context.json. 
</step>

<step>
  Identify transformations  

  - Process each source code file methodically and thoroughly, statement by statement. Even if individual file is large, make sure to process is thoroughly and identify every single transformation. NEVER use large file reading strategies. NEVER generate scripts to try to automate the processing. 
  - Create a list of all transformations first, and store it in a separate file. Uset the template in assets/transfomraiton_analysis_tracker.md 
</step>

<step>
  Process each transformation

  - Proceed to analysing each of these transformation one-by-one
  - Make sure to evaluate relevant context stored in context.json
  - Read and semantically evaluate each transformation independently. NEVER use large file reading strategies. NEVER generate scripts to try to automate the processing. 
  - Follow the steps described in section JobEvent Creation Instructions to create an OpenLineage payload for each relevant transformation 
  - Track the progress in your progress file 
</step>

<step>
  Summarize the results 
  - Include the total number of transformations identified and number of transformations per transformation type
  - Include the total number of OpenLineage events created
</step>

<step>
  Ingest events into watsonx.data intelligence

  Follow the steps in section Prepering events for ingestion to watsonx.data intelligence
</step>

### Workflow 3: Analyze Documents and Diagrams to Document Custom Lineage
**When to use:** User has documentation or diagrams that can be processed to undersatnd the lineage.

<step>
   Retrieve high-level information

   Ask user about 
   - the details of the system they want to document the lineage for (technology name, system name, host, port)
   - what is their goal for the lineage documentation - document the transformations within that system, or document how the system interacts with other systems (cross-system lineage), or both
    - if cross-system lineage is involved, ask about the system details for the related systems as well
</step>

<step>
  Understand inputs

  If user has provided a document or diagram, understand which of the systems describe above they relate to, and what information they contain - whether it is a specification of the system or it's part, architecture diagram of the system, or something else 
</step>

<step>
  Process the inputs to extract lineage information

  **Architecture Diagrams**
  - Look for
    - Boxes/Nodes representing systems (database icons, application boxes, storage systems)
    - Arrows/Lines showing data flow (arrows from source to target, labels indicating data movement)
    - Process/Job boxes (transformation steps, job names, processing descriptions)
  - Extract system names, dataset names, job/process names, flow direction
  - Ignore network connections (unless data flows), user access paths, monitoring/alerting flows, API calls that don't transfer data

  **Text Documentation**
  - Look for formulations like 
    - "Data flows from X to Y"
    - "Reads from [source] and writes to [target]"
    - "Extracts data from [system]"
    - "Loads data into [destination]"
    - "Transforms [field] by [operation]"
    - "Syncs [source] with [target]"
    - "Populates [table] from [source]"
    - Column mapping indicators
      - "Maps [source_col] to [target_col]"
      - "[field] is derived from [source_field]"
      - "Renames [old_name] to [new_name]"
      - "Calculates [field] as [formula]"
  - Ignore general system descriptions without data flows, user interface descriptions, business logic without data operations, historical context
</step>

<step>
  Document each discovered transformation 

  Follow the steps described in section JobEvent Creation Instructions to create an OpenLineage payload for each relevant transformation 
</step>

<step>
  Ingest events into watsonx.data intelligence

  Follow the steps in section Prepering events for ingestion to watsonx.data intelligence
</step>


## JobEvent Creation Instructions
<step>
  Generate one OpenLineage Job Event json per each transofmration. Each Job Event should be captured in a separate JSON document.  
  
  Build the JSON structure following the template stored in file assets/openlineage_payload_template.json.

  Use the following information to replace the placeholders and generate the complete JSON payload:
  - **eventTime**: Generate current timestamp in ISO-8601 format (e.g., `2024-01-15T10:00:00.000Z`)
  - **job.namespace**: Based on the processed inputs, formatted according to the naming conventions
  - **job.name**: Based on the processed inputs, formatted according to the naming conventions
  - **job.facets.documentation**: Generate short summary of what the job does and provide AI disclaimer referencing the source of the information
  - **job.facets.jobType**: Provide information about the Job type
  - **job.facets.sourceCode**: Provide the actual source code based on which the lineage was generated together with pointer to the location of the source code
  - **inputs**: Create array with all input datasets
  - **outputs**: Create array with all output datasets
  - **For datasets**:
    - namespace: Based on the processed inputs, formatted according to the naming conventions
    - name: Based on the processed inputs, formatted according to the naming conventions
    - all relevant facets (schema, hierarchy, dataSource, columnLineage)

  Save the JSON to a file named: `<job-namespace>_<job-name>_jobevent.json`, replace all special characters like slashes and colons by underscores

  ALWAYS create a single JSON file per JobEvent. Never use batches of events.
</step>
<step>
  Validate the Generated JSON

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

  ALWAYS adress any validation failure before proceding further. Never ignore any failer as it will lead to ingestion errors.

  **Content Validation:**
  - All namespaces follow naming conventions from assets/openlineage_naming_conventions.md
  - All dataset names follow naming conventions from assets/openlineage_naming_conventions.md
  - All columnLineage mappings reference valid input fields
  - Column names in columnLineage match schema field names

  - If ALL validations pass: Proceed to Step 6
  - If ANY validation fails: Fix the issues in the JSON files and re-run validation
</step>
<step>
  Ask user for Approval
  Report the captured lineage using the following template: assets/custom_lineage_approval_request.md

  If you produced more than 3 JobEvents, ask user whether they want to review all JobEvents or just several examples. 

  - If user approves, proceed with next step
  - If user requests changes then gather necessary information and iterate the whole process
<step>

## Prepering events for ingestion to watsonx.data intelligence

<step>
  Package the generated JobEvent JSON file(s) into a ZIP file for MDI ingestion.
  Make sure not to include any other files generated during the analysis (MD files and others). 
  Inform user that the ZIP file has been created successfully and validation passed.
</step>