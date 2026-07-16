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