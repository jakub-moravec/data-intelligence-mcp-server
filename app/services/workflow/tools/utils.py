# Copyright [2026] [IBM]
# Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)
# See the LICENSE file in the project root for license information.

# This file has been modified with the assistance of IBM Bob AI tool

"""
Utility functions for workflow tools.

This module provides shared utility functions for querying glossary artifacts
(data classes and business terms) from the workflow service.
"""

from typing import Any, Dict, List, Literal
from app.services.workflow.models.artifact import Artifact, BusinessTerm, DataClass
from app.shared.logging import LOGGER
from app.shared.utils.tool_helper_service import tool_helper_service
from app.services.constants import SEARCH_PATH, GLOSSARY_ARTIFACT_TYPES_ENDPOINT
from fastmcp.exceptions import ToolError

ZERO_MINUTES = "+00:00"
ELICITATION_WATERMARK = 10


def _create_artifact_from_item(item: dict, artifact_type: str):
    """
    Create appropriate artifact object based on artifact type.
    
    Args:
        item: Dictionary containing artifact data
        artifact_type: Type of artifact ('glossary_term' or 'data_class')
        
    Returns:
        BusinessTerm, DataClass, or Artifact object
    """
    from app.services.workflow.models.artifact import Artifact, BusinessTerm, DataClass
    
    common_fields = {
        'name': item.get("name"),
        'description': item.get('long_description') or item.get('description'),
        'artifact_id': item.get("artifact_id"),
        'modified_by': item.get("modified_by"),
        'state': item.get("draft_mode") or item.get("state"),
        'created_at': item.get("created_at"),
        'updated_at': item.get("updated_at"),
        'workflow_id': item.get("workflow_id"),
        'artifact_type': artifact_type,
        'version_id': item.get("version_id")  # Include version_id if available
    }
    
    if artifact_type == 'glossary_term':
        return BusinessTerm(**common_fields)
    elif artifact_type == 'data_class':
        return DataClass(**common_fields)
    else:
        return Artifact(**common_fields)


def validate_search_params(search_term: str, artifact_type: str, max_results: int) -> None:
    """
    Validate search parameters for querying artifacts.
    
    Args:
        search_term: Search term to validate
        artifact_type: Artifact type to validate
        max_results: Maximum results to validate
        
    Raises:
        ValueError: If any parameter is invalid
    """
    if not search_term or not search_term.strip():
        raise ValueError("search_term cannot be empty or whitespace only")
    
    valid_artifact_types = ['glossary_term', 'data_class']
    if artifact_type not in valid_artifact_types:
        raise ValueError(f"artifact_type must be one of {valid_artifact_types}, got '{artifact_type}'")
    
    if max_results <= 0:
        raise ValueError(f"max_results must be positive, got {max_results}")
    
    if max_results > 100:
        LOGGER.warning(f"max_results ({max_results}) exceeds recommended limit of 100")


async def _query_artifact_in_draft_by_term(search_term: str, artifact_type: str, max_results: int) -> List[Artifact]:
    """
    Query the glossary API for artifacts in draft mode.

    Args:
        search_term: str: search_term in name or description
        artifact_type: str: artifact type string like 'data_class' or 'glossary_term'
        max_results: int: Maximum number of artifacts to return

    Returns:
        List[Artifact]: List of glossary artifact objects in draft state only
        
    Raises:
        ValueError: If search parameters are invalid
    """
    # Validate input parameters
    validate_search_params(search_term, artifact_type, max_results)
    
    fetch_limit = max_results * 3
    params = {"sub_string": search_term, "limit": fetch_limit}
    try:
        response = await tool_helper_service.execute_get_request(
            url=f"{tool_helper_service.base_url}{GLOSSARY_ARTIFACT_TYPES_ENDPOINT}/{artifact_type}",
            params=params
        )
    except Exception as e:
        LOGGER.error(f"Failed to fetch artifacts for {artifact_type} with search term '{search_term}': {str(e)}")
        return []

    # Handle None response or missing resources
    if response is None:
        LOGGER.warning(f"Received None response for artifact_type={artifact_type}")
        return []

    artifacts = []
    item_list = response.get('resources', [])
    if item_list is None:
        LOGGER.warning(f"Received None resources for artifact_type={artifact_type}")
        return []

    for item in item_list:
        # Only include artifacts that are in draft state
        # Draft artifacts have workflow_id or draft_mode=True or state="DRAFT"
        is_draft = (
            item.get("workflow_id") is not None or
            item.get("draft_mode") is True or
            (item.get("state") and item.get("state").upper() == "DRAFT")
        )
        
        if is_draft:
            artifact_obj = _create_artifact_from_item(item, artifact_type)
            artifacts.append(artifact_obj)
            
            # Stop once we have enough draft artifacts
            if len(artifacts) >= max_results:
                break

    return artifacts[:max_results]


async def _query_artifacts_by_term(search_term: str, artifact_type: str, max_results: int) -> List[Artifact]:
    """
    Use the global search API for artifacts.

    Args:
        search_term: str: search_term in name or description
        artifact_type: str: artifact type string like 'data_class' or 'glossary_term'
        max_results: int: Maximum number of artifacts to return

    Returns:
        List[Artifact]: List of glossary artifact objects
        
    Raises:
        ValueError: If search parameters are invalid
    """
    # Validate input parameters
    validate_search_params(search_term, artifact_type, max_results)
    
    query_string = f"(metadata.name:{search_term}~1 OR metadata.description:{search_term}~1) AND metadata.artifact_type:{artifact_type}"
    payload = {
        "from": 0,
        "size": max_results,
        "_source": ["*"],
        "query": {"query_string": {"query": query_string}}
    }

    params = {}

    try:
        response = await tool_helper_service.execute_post_request(
            url=f"{tool_helper_service.base_url}{SEARCH_PATH}",
            params={**params, "tenant_scope": True},
            json=payload
        )

        # Schema: { "size": 3, "rows": [ { "last_updated_at": 1763108155799, "metadata": { "name": "Spanish Fiscal Identification Number", ...
        artifact_objs = []
        item_list = response.get('rows', [])

        for artifact in item_list:
            metadata = artifact.get("metadata", {})
            entity = artifact.get("entity", {})
            LOGGER.debug(f"Processing entity: {entity}")
            artifacts = entity.get("artifacts", {})
            
            # Prepare item dict for artifact creation
            item = {
                'name': metadata.get("name"),
                'description': metadata.get("description"),
                'artifact_id': artifacts.get("artifact_id"),
                'modified_by': metadata.get("modified_by"),
                'state': entity.get("state"),
                'created_at': metadata.get("created_at"),
            }
            
            artifact_obj = _create_artifact_from_item(item, artifact_type)
            artifact_objs.append(artifact_obj)

        return artifact_objs

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        LOGGER.error("Error querying glossary artifacts: %s", str(e))
        # Re-raise exceptions so callers can handle them appropriately
        raise ToolError(f"Failed to query glossary artifacts: {str(e)}")


# Helper functions for artifact details
from typing import Optional
from app.services.constants import (
    GLOSSARY_BUSINESS_TERMS_ENDPOINT,
    GLOSSARY_DATA_CLASS_ENDPOINT,
)
from app.services.tool_utils import get_user_info_from_iam_id


def get_artifact_api_endpoint(artifact_type: str) -> str:
    """Return the dedicated details API endpoint for the requested artifact type."""
    if artifact_type == "glossary_term":
        return GLOSSARY_BUSINESS_TERMS_ENDPOINT
    if artifact_type == "data_class":
        return GLOSSARY_DATA_CLASS_ENDPOINT
    raise ToolError(
        f"Unsupported artifact_type '{artifact_type}'. "
        "Must be one of: 'glossary_term', 'data_class'."
    )


def get_artifact_search_endpoint(artifact_type: str) -> str:
    """Return the governance artifact types endpoint for resolving artifact names."""
    return f"{GLOSSARY_ARTIFACT_TYPES_ENDPOINT}/{artifact_type}"


def is_draft_metadata(metadata: dict, response: Optional[dict] = None) -> bool:
    """Check draft state across the metadata shapes returned by glossary APIs."""
    response = response or {}
    state = metadata.get("state") or response.get("state")
    draft_mode = metadata.get("draft_mode") or response.get("draft_mode")
    return (
        (isinstance(state, str) and state.upper() == "DRAFT")
        or metadata.get("workflow_id") is not None
        or response.get("workflow_id") is not None
        or draft_mode is True
        or (isinstance(draft_mode, str) and draft_mode.casefold() == "draft")
    )


def extract_artifact_id(item: dict) -> Optional[str]:
    """Extract artifact_id from the response shapes used by glossary APIs."""
    metadata = item.get("metadata", {})
    entity = item.get("entity", {})
    artifacts = entity.get("artifacts", {}) if isinstance(entity, dict) else {}
    return (
        metadata.get("artifact_id")
        or item.get("artifact_id")
        or artifacts.get("artifact_id")
    )


def extract_artifact_name(item: dict) -> Optional[str]:
    """Extract artifact name from the response shapes used by glossary APIs."""
    metadata = item.get("metadata", {})
    return metadata.get("name") or item.get("name")


def extract_version_id(version: dict) -> Optional[str]:
    """Extract version_id from a version list response item."""
    metadata = version.get("metadata", {})
    return (
        metadata.get("version_id")
        or version.get("version_id")
        or metadata.get("global_id")
    )


def extract_relationships(relationships_response: dict) -> List[Dict]:
    """
    Extract and format relationships from the API response.
    
    The API response structure:
    - Top level keys are relationship types (e.g., 'is_a_type_of_terms', 'parent_category')
    - Each relationship type contains a 'resources' array
    - Each resource has 'entity.parent_name' for the name and 'entity.relationship_type' for the type
    
    Returns:
        List of relationship dictionaries with 'name' and 'type' keys
    """
    relationships = []
    
    for key, value in relationships_response.items():
        if key == "custom_relationships":
            relationships.extend(_extract_custom_relationships(value))
        else:
            relationships.extend(_extract_standard_relationships(key, value))
    
    return relationships


def _extract_custom_relationships(custom_rels_value) -> List[Dict]:
    """Extract custom relationships from the response."""
    relationships = []
    custom_rels = custom_rels_value if isinstance(custom_rels_value, list) else []
    
    for custom_rel in custom_rels:
        if isinstance(custom_rel, dict):
            name = custom_rel.get("name", "Unknown")
            relationships.append({"name": name, "type": "custom"})
    
    return relationships


def _extract_standard_relationships(key: str, value) -> List[Dict]:
    """Extract standard relationships from a relationship type key."""
    relationships = []
    
    if not isinstance(value, dict):
        return relationships
    
    resources = value.get("resources", [])
    
    for item in resources:
        if not isinstance(item, dict):
            continue
        
        relationship = _extract_relationship_from_item(item, key)
        if relationship:
            relationships.append(relationship)
    
    return relationships


def _extract_relationship_from_item(item: dict, default_type: str) -> Optional[Dict]:
    """Extract a single relationship from a resource item."""
    entity = item.get("entity", {})
    metadata = item.get("metadata", {})
    
    # Extract name from multiple possible sources
    name = _get_relationship_name(entity, metadata)
    if not name:
        return None
    
    # Extract type from entity or use default
    rel_type = _get_relationship_type(entity, default_type)
    
    return {"name": name, "type": rel_type}


def _get_relationship_name(entity: dict, metadata: dict) -> Optional[str]:
    """Get relationship name from entity or metadata."""
    if isinstance(entity, dict):
        parent_name = entity.get("parent_name")
        if parent_name:
            return parent_name
        entity_name = entity.get("name")
        if entity_name:
            return entity_name
    
    if isinstance(metadata, dict):
        metadata_name = metadata.get("name")
        if metadata_name:
            return metadata_name
    
    return None


def _get_relationship_type(entity: dict, default_type: str) -> str:
    """Get relationship type from entity or use default."""
    if isinstance(entity, dict):
        entity_rel_type = entity.get("relationship_type")
        if entity_rel_type:
            return entity_rel_type
    
    return default_type


async def fetch_steward_names(steward_ids: Optional[List[str]]) -> List[str]:
    """Fetch steward names from steward IDs using the user profiles API."""
    if not steward_ids:
        return []
    
    steward_names = []
    for steward_id in steward_ids:
        try:
            # Use the existing utility function to fetch user display name
            name = await get_user_info_from_iam_id(steward_id, "name")
            steward_names.append(name)
        except Exception as e:
            LOGGER.warning(f"Could not fetch steward name for ID {steward_id}: {str(e)}")
            steward_names.append(steward_id)  # Fallback to ID if name fetch fails
    
    return steward_names


async def resolve_artifact_id_by_name(
    artifact_name: str,
    artifact_type: str,
) -> str:
    """Resolve an artifact name to an artifact ID using governance artifact types."""
    response = await tool_helper_service.execute_get_request(
        url=f"{tool_helper_service.base_url}{get_artifact_search_endpoint(artifact_type)}",
        params={
            "starts_with": artifact_name,
            "limit": 10,
        },
    )

    resources = response.get("resources", [])
    if not resources:
        raise ToolError(
            f"Could not find {artifact_type} artifact with name '{artifact_name}'"
        )

    exact_matches = [
        item
        for item in resources
        if (extract_artifact_name(item) or "").casefold() == artifact_name.casefold()
    ]

    if len(exact_matches) == 1:
        selected_artifact = exact_matches[0]
    elif len(resources) == 1:
        selected_artifact = resources[0]
    else:
        candidate_names = [
            name for name in (extract_artifact_name(item) for item in resources)
            if name
        ]
        raise ToolError(
            f"Found multiple {artifact_type} artifacts matching '{artifact_name}'. "
            f"Please use a more specific name. Candidates: {', '.join(candidate_names[:10])}"
        )

    artifact_id = extract_artifact_id(selected_artifact)
    if not artifact_id:
        raise ToolError(
            f"Could not resolve artifact_id for {artifact_type} artifact '{artifact_name}'"
        )

    return artifact_id
