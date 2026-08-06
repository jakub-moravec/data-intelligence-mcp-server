# Copyright [2026] [IBM]
# Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)
# See the LICENSE file in the project root for license information.

"""
Tool for getting detailed information about a workflow glossary artifact.

The tool resolves a business term or data class by name, fetches the latest
and previous draft versions, and returns comparison details including descriptions,
relationships, and data steward names.
"""

from typing import Annotated, Optional, List
from urllib.parse import quote
from pydantic import Field

from app.core.registry import service_registry
from app.services.text_to_query_search.constants import GOVERNANCE_GLOSSARY_PATHS
from app.services.workflow.models.get_artifact_details import (
    ArtifactDetails,
    ArtifactType,
    GetArtifactDetailsRequest,
    GetArtifactDetailsResponse,
    RelationshipSummary,
    VersionDetails,
)
from app.services.workflow.tools.utils import (
    get_artifact_api_endpoint,
    get_artifact_search_endpoint,
    is_draft_metadata,
    extract_artifact_id,
    extract_artifact_name,
    extract_version_id,
    extract_relationships,
    fetch_steward_names,
    resolve_artifact_id_by_name,
)
from app.shared.logging import LOGGER, auto_context
from app.shared.utils.helpers import append_context_to_url
from app.shared.utils.tool_helper_service import tool_helper_service
from app.shared.exceptions.base import ExternalAPIError, ServiceError
from fastmcp.server.context import Context


async def _fetch_version_details(
    artifact_api_endpoint: str,
    artifact_id: str,
    version_id: str,
) -> VersionDetails:
    """Fetch detailed information for a specific version."""
    version_detail_endpoint = f"{artifact_api_endpoint}/{artifact_id}/versions/{version_id}"
    LOGGER.info(f"Fetching version details from: {version_detail_endpoint}")
    
    response = await tool_helper_service.execute_get_request(
        url=f"{tool_helper_service.base_url}{version_detail_endpoint}"
    )
    
    metadata = response.get("metadata", {})
    entity = response.get("entity", {})
    
    # Fetch relationships using the dedicated relationships endpoint
    # e.g., /v3/glossary_terms/{artifact_id}/versions/{version_id}/relationships
    relationships_endpoint = f"{artifact_api_endpoint}/{artifact_id}/versions/{version_id}/relationships"
    LOGGER.info(f"Fetching relationships from: {relationships_endpoint}")
    
    try:
        relationships_response = await tool_helper_service.execute_get_request(
            url=f"{tool_helper_service.base_url}{relationships_endpoint}",
            params={
                "type": "all",
                "limit": 100,
            },
        )
    except Exception as e:
        LOGGER.error("Could not fetch relationships for version %s: %s", version_id, str(e))
        LOGGER.error("Relationships endpoint was: %s", relationships_endpoint)
        relationships_response = {"resources": []}
    
    # Extract steward IDs and fetch names
    steward_ids = metadata.get("steward_ids") or []
    steward_names = await fetch_steward_names(steward_ids)
    
    return VersionDetails(
        version_id=metadata.get("version_id") or response.get("version_id") or version_id,
        state=metadata.get("state") or response.get("state"),
        long_description=entity.get("long_description") or response.get("long_description"),
        short_description=metadata.get("short_description") or response.get("short_description"),
        steward_names=steward_names,
        relationships=[RelationshipSummary(**r) for r in extract_relationships(relationships_response)],
    )


def _format_artifact_url(
    artifact_id: str,
    artifact_type: ArtifactType,
    version_id: Optional[str] = None,
) -> str:
    """Build the governance UI URL for glossary artifacts."""
    artifact_path = GOVERNANCE_GLOSSARY_PATHS[artifact_type]
    path_segments = [
        str(tool_helper_service.ui_base_url),
        "governance",
        artifact_path,
        quote(artifact_id, safe=""),
    ]

    if version_id:
        path_segments.append(quote(version_id, safe=""))

    return append_context_to_url("/".join(path_segments))



def _build_comparison_header(artifact_details: ArtifactDetails) -> List[str]:
    """Build header section for comparison table."""
    header = [
        f"# {artifact_details.name}",
        "",
        f"**Type:** {artifact_details.artifact_type}",
        f"**Artifact ID:** {artifact_details.artifact_id}",
    ]
    
    if artifact_details.url:
        header.append(f"**Link:** [View]({artifact_details.url})")
    if artifact_details.workflow_id:
        header.append(f"**Workflow ID:** {artifact_details.workflow_id}")
    
    header.append("")
    return header


def _build_comparison_rows(artifact_details: ArtifactDetails) -> List[str]:
    """Build table rows for version comparison."""
    latest = artifact_details.latest_version
    previous = artifact_details.previous_version
    
    return [
        "| Field | Latest Version | Previous Version |",
        "| --- | --- | --- |",
        _format_table_row("Version ID", latest.version_id, previous.version_id if previous else None),
        _format_table_row("State", latest.state, previous.state if previous else None),
        _format_table_row("Short Description", latest.short_description, previous.short_description if previous else None),
        _format_table_row("Long Description", latest.long_description, previous.long_description if previous else None),
        _format_table_row("Data Stewards", _format_list(latest.steward_names), _format_list(previous.steward_names) if previous else ""),
        _format_table_row("Relationships", _format_relationships(latest.relationships), _format_relationships(previous.relationships) if previous else ""),
    ]


def _format_table_row(field: str, latest_value: Optional[str], previous_value: Optional[str]) -> str:
    """Format a single table row."""
    return f"| {field} | {latest_value or ''} | {previous_value or ''} |"


def _format_list(items: Optional[List]) -> str:
    """Format a list of items as comma-separated string."""
    if not items:
        return ""
    return ", ".join(str(item) for item in items)


def _format_relationships(rels: List[RelationshipSummary]) -> str:
    """Format relationships as comma-separated string."""
    if not rels:
        return ""
    return ", ".join(f"{r.name} ({r.type})" for r in rels)

def _format_comparison_table(artifact_details: ArtifactDetails) -> str:
    """Format artifact details as a comparison table."""
    header = _build_comparison_header(artifact_details)
    rows = _build_comparison_rows(artifact_details)
    return "\n".join(header + rows)


async def _get_artifact_details(
    request: GetArtifactDetailsRequest,
) -> GetArtifactDetailsResponse:
    """
    Get detailed information about a glossary artifact with version comparison.

    Args:
        request: GetArtifactDetailsRequest containing artifact_name and artifact_type

    Returns:
        GetArtifactDetailsResponse with latest and previous version details

    Raises:
        ToolError: If the artifact cannot be found or the API call fails
    """
    try:
        artifact_api_endpoint = get_artifact_api_endpoint(request.artifact_type)
        artifact_id = await resolve_artifact_id_by_name(
            artifact_name=request.artifact_name,
            artifact_type=request.artifact_type,
        )

        # Fetch and filter draft versions
        draft_versions = await _fetch_draft_versions(artifact_api_endpoint, artifact_id)
        
        # Fetch version details
        latest_version = await _fetch_version_details(
            artifact_api_endpoint,
            artifact_id,
            extract_version_id(draft_versions[0]),
        )
        
        previous_version = await _fetch_previous_version_if_available(
            artifact_api_endpoint,
            artifact_id,
            draft_versions,
        )

        # Build artifact details
        artifact_details = _build_artifact_details(
            request,
            artifact_id,
            latest_version,
            previous_version,
            draft_versions[0].get("metadata", {}),
        )

        formatted_output = None
        if request.format == "table":
            formatted_output = _format_comparison_table(artifact_details)

        return GetArtifactDetailsResponse(
            artifact_details=artifact_details,
            formatted_output=formatted_output,
        )
    except (ServiceError, ExternalAPIError):
        raise
    except Exception as e:
        LOGGER.error("Error fetching artifact details: %s", str(e))
        raise ServiceError(
            f"Failed to fetch artifact details: {str(e)}",
            service="workflow",
            tool="get_artifact_details",
        )


async def _fetch_draft_versions(artifact_api_endpoint: str, artifact_id: str) -> list:
    """Fetch and filter draft versions for an artifact."""
    versions_list_endpoint = f"{artifact_api_endpoint}/{artifact_id}/versions"
    versions_response = await tool_helper_service.execute_get_request(
        url=f"{tool_helper_service.base_url}{versions_list_endpoint}",
        params={
            "status": "DRAFT",
            "limit": 10,
        },
    )

    versions = (
        versions_response.get("resources", [])
        or versions_response.get("versions", [])
    )
    if not versions:
        raise ServiceError(
            f"No versions found for artifact {artifact_id}",
            service="workflow",
            tool="get_artifact_details",
            remediation_steps=(
                "Verify the artifact_id is correct. "
                "Use list_draft_artifacts to retrieve valid artifact IDs."
            ),
        )

    # Find draft versions
    draft_versions = [
        version for version in versions
        if is_draft_metadata(version.get("metadata", {}), version)
    ]

    if not draft_versions:
        raise ServiceError(
            f"No draft versions found for artifact {artifact_id}. "
            "This tool only retrieves details for draft artifacts.",
            service="workflow",
            tool="get_artifact_details",
            remediation_steps=(
                "Confirm the artifact has a DRAFT state. "
                "Use list_draft_artifacts to find artifacts currently in draft."
            ),
        )

    # Validate latest version ID
    latest_version_id = extract_version_id(draft_versions[0])
    if not latest_version_id:
        raise ServiceError(
            "Could not extract version_id from latest draft version",
            service="workflow",
            tool="get_artifact_details",
        )
    
    return draft_versions


async def _fetch_previous_version_if_available(
    artifact_api_endpoint: str,
    artifact_id: str,
    draft_versions: list,
) -> Optional[VersionDetails]:
    """Fetch previous version details if available."""
    if len(draft_versions) <= 1:
        return None
    
    previous_version_id = extract_version_id(draft_versions[1])
    if not previous_version_id:
        return None
    
    try:
        return await _fetch_version_details(
            artifact_api_endpoint,
            artifact_id,
            previous_version_id,
        )
    except Exception as e:
        LOGGER.warning(
            "Could not fetch previous version details for artifact_id=%s: %s",
            artifact_id,
            str(e)
        )
        return None


def _build_artifact_details(
    request: GetArtifactDetailsRequest,
    artifact_id: str,
    latest_version: VersionDetails,
    previous_version: Optional[VersionDetails],
    latest_metadata: dict,
) -> ArtifactDetails:
    """Build ArtifactDetails object from components."""
    return ArtifactDetails(
        artifact_id=artifact_id,
        name=request.artifact_name,
        artifact_type=request.artifact_type,
        url=_format_artifact_url(
            artifact_id,
            request.artifact_type,
            latest_version.version_id,
        ),
        latest_version=latest_version,
        previous_version=previous_version,
        workflow_id=latest_metadata.get("workflow_id"),
        workflow_state=latest_metadata.get("workflow_state"),
    )


get_artifact_details_description = """
Get detailed information about a specific workflow glossary artifact (business term or data class).

**When to use this tool:**
- When you need to review draft artifact details before approval
- When comparing changes between the latest and previous draft versions
- When you need to see relationships, stewards, and descriptions for a draft artifact

**Example:**
To get details for a draft business term named "Customer ID":
- artifact_name: "Customer ID"
- artifact_type: "glossary_term"
- format: "table"

**Returns:**
A GetArtifactDetailsResponse containing:
- artifact_details: Structured data with latest and previous version information
- formatted_output: Markdown table comparing versions (when format="table")

The comparison includes short/long descriptions, relationships, data steward names,
version IDs, states, and a formatted UI URL for both versions.
"""


@service_registry.tool(
    name="get_artifact_details",
    annotations={
        "readOnlyHint": True,
        "title": "Get Detailed Information About Draft Workflow Glossary Artifacts"
    },
    description=get_artifact_details_description,
    tags={"workflow", "glossary", "artifacts", "governance"},
    meta={"version": "2.0", "service": "glossary"},
)
@auto_context
async def get_artifact_details(
    artifact_name: Annotated[str, Field(description="The name of the business term or data class to retrieve details for")],
    artifact_type: Annotated[ArtifactType, Field(description="Type of artifact: 'glossary_term' for business terms or 'data_class' for data classes")],
    format: Annotated[str, Field(description="Output format: 'table' for markdown comparison table or 'json' for structured data only")] = "table",
    ctx: Context = None,
) -> GetArtifactDetailsResponse:
    """
    Get detailed information about a glossary artifact with version comparison.

    Args:
        artifact_name: The artifact name to retrieve details for
        artifact_type: Type of artifact ('glossary_term' or 'data_class')
        format: Output format ('table' for formatted output, 'json' for structured data)
        ctx: Optional MCP Context

    Returns:
        GetArtifactDetailsResponse with latest and previous version details
    """
    request = GetArtifactDetailsRequest(
        artifact_name=artifact_name,
        artifact_type=artifact_type,
        format=format,
    )
    return await _get_artifact_details(request)

# Made with Bob
