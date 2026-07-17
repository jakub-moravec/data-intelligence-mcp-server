# SAS Data Lineage Analysis Guide

## What is considered Context

Statements that set execution environment but don't move data. Context affects how subsequent data movements are interpreted.

## Context-Setting Statements

- `LIBNAME` - Library definitions
- `%LET` - Macro variables  
- `FILENAME` - File references
- `OPTIONS` - System settings
- `%INCLUDE` - Code includes
- `%MACRO` - Macro definitions

## Context Storage

```json
context = {
    "libraries": {
        "MYLIB": [
            {"line": 1, "value": "/data/mylib"},
            {"line": 150, "value": "/data/elsewhere/mylib"}
        ]
    },
    "macro_vars": {
        "data_path": [
            {"line": 2, "value": "/data/input"},
            {"line": 152, "value": "/data/elsewhere/input2"}
        ]
    },
    "filerefs": {"INDATA": [
            {"line": 3, "value": "/data/file.csv"},
            {"line": 155, "value": "/data/external/filex.csv"},
            {"line": 159, "value": "/data/2/filez.csv"}
        ]
    }
}
```

## Context handling Workflow

1. **Initialize** - Scan file start for initial context
2. **Process line-by-line**:
   - If context statement → Update context, increment version
   - If data movement → Resolve references using current context
3. **Resolve** - Replace `&var`, `libref.table`, `fileref` with actual values

- **Don't assume static context** - Always check for changes
- **Version context** - Track changes by referencing line numbers
- **Resolve all references** - Use context before generating lineage
- **Analyze %INCLUDE files** - They may contain critical context
- **Document context version** - Reference in lineage metadata

## What is Considered a Transformation

In SAS, a **transformation** is any operation that reads data from one or more sources and writes it to a destination, potentially modifying the data in the process. SAS uses DATA steps and PROC steps for data manipulation.

### SAS Statements That Move Data (Transformations)

**DATA Step Statements:**
- `DATA` - Creates new dataset(s)
- `SET` - Reads observations from one or more datasets
- `MERGE` - Combines observations from multiple datasets
- `UPDATE` - Updates master dataset with transaction dataset
- `MODIFY` - Updates dataset in place
- `APPEND` - Adds observations to existing dataset (via PROC APPEND)
- `OUTPUT` - Writes current observation to output dataset
- `INFILE` - Reads data from external file
- `FILE` - Writes data to external file
- `PUT` - Writes formatted data to file or log

**PROC SQL Statements:**
- `CREATE TABLE` - Creates new table from query
- `INSERT INTO` - Inserts rows into table
- `UPDATE` - Modifies existing rows
- `DELETE` - Removes rows from table
- `SELECT INTO` - Creates macro variables or datasets from query

**PROC Steps That Create Output:**
- `PROC SORT` (with `OUT=`) - Sorts and creates new dataset
- `PROC MEANS/SUMMARY` (with `OUTPUT OUT=`) - Creates summary statistics dataset
- `PROC FREQ` (with `OUT=`) - Creates frequency table dataset
- `PROC TRANSPOSE` - Reshapes dataset
- `PROC APPEND` - Appends datasets
- `PROC DATASETS` (COPY, CHANGE, RENAME) - Manages datasets
- `PROC COPY` - Copies datasets between libraries
- `PROC IMPORT` - Imports external data files
- `PROC EXPORT` - Exports data to external files
- `PROC REPORT` (with `OUT=`) - Creates report dataset
- `PROC TABULATE` (with `OUT=`) - Creates tabular summary dataset
- `PROC UNIVARIATE` (with `OUTPUT OUT=`) - Creates statistics dataset
- `PROC CONTENTS` (with `OUT=`) - Creates metadata dataset
- `PROC COMPARE` (with `OUT=`) - Creates comparison results dataset
- `PROC RANK` (with `OUT=`) - Creates ranked dataset
- `PROC STANDARD` (with `OUT=`) - Creates standardized dataset
- `PROC CORR` (with `OUTP=`) - Creates correlation matrix dataset
- `PROC REG` (with `OUTEST=`) - Creates parameter estimates dataset
- `PROC LOGISTIC` (with `OUTEST=`) - Creates model estimates dataset
- `PROC GLIMMIX/MIXED` (with `OUTEST=`) - Creates model output dataset

**Data Access Statements:**
- `LIBNAME` - Defines library connection (when used to read/write data)
- `FILENAME` - Defines file reference (when used to read/write data)
- Database pass-through statements (CONNECT, EXECUTE, DISCONNECT)

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