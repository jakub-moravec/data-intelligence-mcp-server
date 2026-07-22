#!/usr/bin/env python3
"""
OpenLineage JobEvent Validator

This script validates OpenLineage JobEvent JSON files against the specification
requirements before ingestion into watsonx.data intelligence.

Usage:
    python validate_jobevent.py <jobevent_file.json>
    python validate_jobevent.py <directory_with_json_files>

The script performs comprehensive validation including:
- JSON syntax validation
- JobEvent structure validation
- Namespace and naming convention validation
- Facet validation
- Column lineage validation
- Schema compliance checks

Exit codes:
    0 - All validations passed
    1 - One or more validations failed
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any
import re


class ValidationResult:
    """Stores the result of a single validation check."""
    
    def __init__(self, check_name: str, passed: bool, message: str = ""):
        self.check_name = check_name
        self.passed = passed
        self.message = message
    
    def __str__(self):
        status = "✓ OK" if self.passed else "✗ FAIL"
        msg = f" - {self.message}" if self.message else ""
        return f"[{status}] {self.check_name}{msg}"


class JobEventValidator:
    """Validates OpenLineage JobEvent JSON files."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.data = None
        self.results: List[ValidationResult] = []
        self.expected_producer = "https://github.com/IBM/data-intelligence-mcp-server"
    
    def validate(self) -> bool:
        """
        Run all validation checks.
        
        Returns:
            bool: True if all validations passed, False otherwise
        """
        print(f"\n{'='*80}")
        print(f"Validating: {self.file_path}")
        print(f"{'='*80}\n")
        
        # Load and parse JSON
        if not self._load_json():
            return False
        
        # Run all validation checks
        self._validate_json_syntax()
        self._validate_structure()
        self._validate_content()
        self._validate_facets()
        self._validate_namespaces()
        self._validate_column_lineage()
        
        # Print results
        self._print_results()
        
        # Return overall status
        return all(result.passed for result in self.results)
    
    def _load_json(self) -> bool:
        """Load and parse the JSON file."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.results.append(ValidationResult(
                "JSON Loading",
                True,
                "File loaded successfully"
            ))
            return True
        except json.JSONDecodeError as e:
            self.results.append(ValidationResult(
                "JSON Syntax",
                False,
                f"Invalid JSON syntax: {str(e)}"
            ))
            return False
        except FileNotFoundError:
            self.results.append(ValidationResult(
                "File Access",
                False,
                f"File not found: {self.file_path}"
            ))
            return False
        except Exception as e:
            self.results.append(ValidationResult(
                "File Loading",
                False,
                f"Error loading file: {str(e)}"
            ))
            return False
    
    def _validate_json_syntax(self):
        """Validate JSON syntax requirements."""
        if self.data is None:
            return
        
        # Check for common JSON issues
        json_str = json.dumps(self.data)
        
        # Check for trailing commas (would have been caught in parsing, but good to note)
        self.results.append(ValidationResult(
            "JSON Syntax - No Trailing Commas",
            True,
            "Valid JSON structure"
        ))
        
        # Check all brackets are closed (validated by successful parsing)
        self.results.append(ValidationResult(
            "JSON Syntax - Brackets Closed",
            True,
            "All brackets and braces properly closed"
        ))
    
    def _validate_structure(self):
        """Validate JobEvent structure requirements."""
        if self.data is None:
            return
        
        # Check required fields
        self._check_field_exists("eventTime", "Required field 'eventTime'")
        self._check_field_exists("job", "Required field 'job'")
        self._check_field_exists("producer", "Required field 'producer'")
        
        # Check job object structure
        if "job" in self.data:
            job = self.data["job"]
            self._check_field_exists("namespace", "Required field 'job.namespace'", job)
            self._check_field_exists("name", "Required field 'job.name'", job)
        
        # Critical: NO "run" object should be present
        has_run = "run" in self.data
        self.results.append(ValidationResult(
            "Structure - No 'run' Object",
            not has_run,
            "CRITICAL: 'run' object found (JobEvent must not have 'run' object)" if has_run 
            else "Correctly excludes 'run' object"
        ))
        
        # Critical: NO "eventType" should be present
        has_event_type = "eventType" in self.data
        self.results.append(ValidationResult(
            "Structure - No 'eventType' Field",
            not has_event_type,
            "'eventType' found (irrelevant for JobEvent)" if has_event_type 
            else "Correctly excludes 'eventType'"
        ))
        
        # Check for inputs and outputs arrays
        self._check_field_type("inputs", list, "Field 'inputs' should be an array")
        self._check_field_type("outputs", list, "Field 'outputs' should be an array")
    
    def _validate_content(self):
        """Validate content requirements."""
        if self.data is None:
            return
        
        # Validate eventTime format (ISO-8601)
        if "eventTime" in self.data:
            event_time = self.data["eventTime"]
            is_valid_iso = self._is_valid_iso8601(event_time)
            self.results.append(ValidationResult(
                "Content - eventTime ISO-8601 Format",
                is_valid_iso,
                f"Valid ISO-8601 timestamp" if is_valid_iso 
                else f"Invalid ISO-8601 format: {event_time}"
            ))
        
        # Validate producer value
        if "producer" in self.data:
            producer = self.data["producer"]
            is_correct = producer == self.expected_producer
            self.results.append(ValidationResult(
                "Content - Producer Value",
                is_correct,
                f"Correct producer URL" if is_correct 
                else f"Expected '{self.expected_producer}', got '{producer}'"
            ))
        
        # Validate schema fields in datasets
        self._validate_dataset_schemas("inputs")
        self._validate_dataset_schemas("outputs")
    
    def _validate_facets(self):
        """Validate facet requirements."""
        if self.data is None:
            return
        
        # Validate job facets
        if "job" in self.data and "facets" in self.data["job"]:
            self._validate_facet_structure(self.data["job"]["facets"], "job")
        
        # Validate dataset facets
        for dataset_type in ["inputs", "outputs"]:
            if dataset_type in self.data:
                for idx, dataset in enumerate(self.data[dataset_type]):
                    if "facets" in dataset:
                        self._validate_facet_structure(
                            dataset["facets"], 
                            f"{dataset_type}[{idx}]"
                        )
                    
                    # Check for required dataset facets
                    self._check_required_dataset_facets(dataset, dataset_type, idx)
    
    def _validate_facet_structure(self, facets: Dict, location: str):
        """Validate that facets have required _producer and _schemaURL fields."""
        for facet_name, facet_data in facets.items():
            if not isinstance(facet_data, dict):
                continue
            
            # Check _producer
            if "_producer" in facet_data:
                producer = facet_data["_producer"]
                is_correct = producer == self.expected_producer
                self.results.append(ValidationResult(
                    f"Facet - {location}.{facet_name}._producer",
                    is_correct,
                    f"Correct producer" if is_correct 
                    else f"Expected '{self.expected_producer}', got '{producer}'"
                ))
            else:
                self.results.append(ValidationResult(
                    f"Facet - {location}.{facet_name}._producer",
                    False,
                    "Missing _producer field"
                ))
            
            # Check _schemaURL
            has_schema_url = "_schemaURL" in facet_data
            self.results.append(ValidationResult(
                f"Facet - {location}.{facet_name}._schemaURL",
                has_schema_url,
                "Has _schemaURL" if has_schema_url else "Missing _schemaURL field"
            ))
    
    def _check_required_dataset_facets(self, dataset: Dict, dataset_type: str, idx: int):
        """Check for required dataset facets."""
        facets = dataset.get("facets", {})
        dataset_name = dataset.get("name", f"{dataset_type}[{idx}]")
        
        # Check for schema facet
        has_schema = "schema" in facets
        self.results.append(ValidationResult(
            f"Dataset Facet - {dataset_name} - schema",
            has_schema,
            "Has schema facet" if has_schema else "Missing schema facet (recommended)"
        ))
        
        # Check for dataSource facet
        has_datasource = "dataSource" in facets
        self.results.append(ValidationResult(
            f"Dataset Facet - {dataset_name} - dataSource",
            has_datasource,
            "Has dataSource facet" if has_datasource else "Missing dataSource facet (recommended)"
        ))
        
        # Check for hierarchy facet
        has_hierarchy = "hierarchy" in facets
        self.results.append(ValidationResult(
            f"Dataset Facet - {dataset_name} - hierarchy",
            has_hierarchy,
            "Has hierarchy facet" if has_hierarchy else "Missing hierarchy facet (recommended)"
        ))
        
        # Validate hierarchy structure if present
        if has_hierarchy:
            hierarchy_facet = facets["hierarchy"]
            
            # Check for nested "hierarchy" key (required structure)
            if "hierarchy" not in hierarchy_facet:
                self.results.append(ValidationResult(
                    f"Dataset Facet - {dataset_name} - hierarchy structure",
                    False,
                    "Hierarchy facet missing nested 'hierarchy' key"
                ))
            elif not isinstance(hierarchy_facet["hierarchy"], list):
                self.results.append(ValidationResult(
                    f"Dataset Facet - {dataset_name} - hierarchy structure",
                    False,
                    "Nested 'hierarchy' must be a list"
                ))
            else:
                hierarchy_list = hierarchy_facet["hierarchy"]
                all_valid = True
                
                for idx, entry in enumerate(hierarchy_list):
                    has_type = "type" in entry
                    has_name = "name" in entry
                    
                    if not has_type or not has_name:
                        self.results.append(ValidationResult(
                            f"Dataset Facet - {dataset_name} - hierarchy[{idx}]",
                            False,
                            f"Hierarchy entry missing required 'type' or 'name' field"
                        ))
                        all_valid = False
                        break
                
                if all_valid:
                    self.results.append(ValidationResult(
                        f"Dataset Facet - {dataset_name} - hierarchy structure",
                        True,
                        f"All {len(hierarchy_list)} hierarchy entries valid (each has 'type' and 'name')"
                    ))
        
        # Check for columnLineage facet (outputs only)
        if dataset_type == "outputs":
            has_column_lineage = "columnLineage" in facets
            # This is optional, so we just note it
            if has_column_lineage:
                self.results.append(ValidationResult(
                    f"Dataset Facet - {dataset_name} - columnLineage",
                    True,
                    "Has columnLineage facet"
                ))
    
    def _validate_namespaces(self):
        """Validate namespace format conventions."""
        if self.data is None:
            return
        
        # Validate job namespace
        if "job" in self.data:
            job = self.data["job"]
            if "namespace" in job:
                namespace = job["namespace"]
                is_valid = self._is_valid_namespace_format(namespace)
                self.results.append(ValidationResult(
                    "Namespace - job.namespace Format",
                    is_valid,
                    f"Valid format: {namespace}" if is_valid 
                    else f"Should follow 'technology://host:port' pattern: {namespace}"
                ))
        
        # Validate dataset namespaces
        for dataset_type in ["inputs", "outputs"]:
            if dataset_type in self.data:
                for idx, dataset in enumerate(self.data[dataset_type]):
                    if "namespace" in dataset:
                        namespace = dataset["namespace"]
                        is_valid = self._is_valid_namespace_format(namespace)
                        dataset_name = dataset.get("name", f"{dataset_type}[{idx}]")
                        self.results.append(ValidationResult(
                            f"Namespace - {dataset_name}",
                            is_valid,
                            f"Valid format: {namespace}" if is_valid 
                            else f"Should follow 'technology://host:port' pattern: {namespace}"
                        ))
    
    def _validate_column_lineage(self):
        """Validate column lineage mappings."""
        if self.data is None or "outputs" not in self.data:
            return
        
        # Collect all input column names
        input_columns = set()
        if "inputs" in self.data:
            for input_dataset in self.data["inputs"]:
                if "facets" in input_dataset and "schema" in input_dataset["facets"]:
                    schema = input_dataset["facets"]["schema"]
                    if "fields" in schema:
                        for field in schema["fields"]:
                            if "name" in field:
                                input_columns.add(field["name"])
        
        # Validate column lineage in outputs
        for idx, output in enumerate(self.data["outputs"]):
            output_name = output.get("name", f"outputs[{idx}]")
            
            # Get output schema columns
            output_columns = set()
            if "facets" in output and "schema" in output["facets"]:
                schema = output["facets"]["schema"]
                if "fields" in schema:
                    for field in schema["fields"]:
                        if "name" in field:
                            output_columns.add(field["name"])
            
            # Check columnLineage if present
            if "facets" in output and "columnLineage" in output["facets"]:
                lineage = output["facets"]["columnLineage"]
                if "fields" in lineage:
                    for col_name, col_lineage in lineage["fields"].items():
                        # Check if column exists in output schema
                        if col_name not in output_columns:
                            self.results.append(ValidationResult(
                                f"Column Lineage - {output_name}.{col_name}",
                                False,
                                f"Column '{col_name}' in columnLineage not found in schema"
                            ))
                        
                        # Check if input fields are valid
                        if "inputFields" in col_lineage:
                            for input_field in col_lineage["inputFields"]:
                                if "field" in input_field:
                                    field_name = input_field["field"]
                                    # Extract just the column name (after last dot)
                                    col_only = field_name.split(".")[-1]
                                    if col_only not in input_columns:
                                        self.results.append(ValidationResult(
                                            f"Column Lineage - {output_name}.{col_name} Input",
                                            False,
                                            f"Input field '{field_name}' not found in input schemas"
                                        ))
    
    def _validate_dataset_schemas(self, dataset_type: str):
        """Validate schema fields in datasets."""
        if self.data is None or dataset_type not in self.data:
            return
        
        for idx, dataset in enumerate(self.data[dataset_type]):
            dataset_name = dataset.get("name", f"{dataset_type}[{idx}]")
            
            if "facets" in dataset and "schema" in dataset["facets"]:
                schema = dataset["facets"]["schema"]
                if "fields" in schema:
                    for field_idx, field in enumerate(schema["fields"]):
                        # Check that field has name
                        has_name = "name" in field
                        if not has_name:
                            self.results.append(ValidationResult(
                                f"Schema - {dataset_name}.fields[{field_idx}]",
                                False,
                                "Field missing 'name' attribute"
                            ))
                        else:
                            # Type and description are optional
                            field_name = field["name"]
                            has_type = "type" in field
                            has_desc = "description" in field
                            
                            details = []
                            if has_type:
                                details.append(f"type: {field['type']}")
                            if has_desc:
                                details.append("has description")
                            
                            detail_str = f" ({', '.join(details)})" if details else ""
                            self.results.append(ValidationResult(
                                f"Schema - {dataset_name}.{field_name}",
                                True,
                                f"Valid field{detail_str}"
                            ))
    
    def _check_field_exists(self, field_name: str, check_name: str, obj: Dict = None):
        """Check if a field exists in the data."""
        if obj is None:
            obj = self.data if self.data is not None else {}
        
        exists = field_name in obj
        self.results.append(ValidationResult(
            check_name,
            exists,
            f"Field present" if exists else f"Field '{field_name}' missing"
        ))
    
    def _check_field_type(self, field_name: str, expected_type: type, check_name: str):
        """Check if a field has the expected type."""
        if self.data is None or field_name not in self.data:
            return
        
        is_correct_type = isinstance(self.data[field_name], expected_type)
        self.results.append(ValidationResult(
            check_name,
            is_correct_type,
            f"Correct type: {expected_type.__name__}" if is_correct_type
            else f"Expected {expected_type.__name__}, got {type(self.data[field_name]).__name__}"
        ))
    
    def _is_valid_iso8601(self, timestamp: str) -> bool:
        """Check if timestamp is valid ISO-8601 format."""
        try:
            # Try parsing with various ISO-8601 formats
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return True
        except (ValueError, AttributeError):
            return False
    
    def _is_valid_namespace_format(self, namespace: str) -> bool:
        """
        Check if namespace follows the expected format.
        Expected: technology://host:port or similar URI format
        """
        # Basic check for URI-like format
        # Pattern: scheme://authority or just a simple identifier
        pattern = r'^[a-zA-Z][a-zA-Z0-9+.-]*://.*$|^[a-zA-Z][a-zA-Z0-9_-]*$'
        return bool(re.match(pattern, namespace))
    
    def _print_results(self):
        """Print validation results in a formatted way."""
        print("\nValidation Results:")
        print("-" * 80)
        
        passed_count = 0
        failed_count = 0
        
        for result in self.results:
            print(result)
            if result.passed:
                passed_count += 1
            else:
                failed_count += 1
        
        print("-" * 80)
        print(f"\nSummary: {passed_count} passed, {failed_count} failed")
        
        if failed_count == 0:
            print("\n✓ All validations passed! JobEvent is ready for ingestion.")
        else:
            print(f"\n✗ {failed_count} validation(s) failed. Please fix the issues before ingestion.")


def validate_file(file_path: str) -> bool:
    """Validate a single JobEvent file."""
    validator = JobEventValidator(file_path)
    return validator.validate()


def validate_directory(directory: str) -> Tuple[int, int]:
    """
    Validate all JSON files in a directory.
    
    Returns:
        Tuple of (passed_count, failed_count)
    """
    json_files = list(Path(directory).glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {directory}")
        return 0, 0
    
    print(f"Found {len(json_files)} JSON file(s) to validate\n")
    
    passed = 0
    failed = 0
    
    for json_file in json_files:
        if validate_file(str(json_file)):
            passed += 1
        else:
            failed += 1
    
    return passed, failed


def main():
    """Main entry point for the validator."""
    if len(sys.argv) != 2:
        print("Usage: python validate_jobevent.py <jobevent_file.json|directory>")
        print("\nValidates OpenLineage JobEvent JSON files before ingestion.")
        sys.exit(1)
    
    path = sys.argv[1]
    
    if not os.path.exists(path):
        print(f"Error: Path not found: {path}")
        sys.exit(1)
    
    if os.path.isfile(path):
        # Validate single file
        success = validate_file(path)
        sys.exit(0 if success else 1)
    
    elif os.path.isdir(path):
        # Validate all JSON files in directory
        passed, failed = validate_directory(path)
        
        print(f"\n{'='*80}")
        print(f"Overall Summary: {passed} file(s) passed, {failed} file(s) failed")
        print(f"{'='*80}")
        
        sys.exit(0 if failed == 0 else 1)
    
    else:
        print(f"Error: Invalid path: {path}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob
