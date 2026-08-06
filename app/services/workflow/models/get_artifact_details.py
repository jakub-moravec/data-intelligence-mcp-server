# Copyright [2026] [IBM]
# Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)
# See the LICENSE file in the project root for license information.


"""
Models for getting detailed information about glossary artifacts.

This module contains request and response models for retrieving comprehensive
details about a specific glossary artifact (business term or data class).
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, Literal, Optional, List

from app.shared.models import BaseResponseModel

ArtifactType = Literal["glossary_term", "data_class"]


class GetArtifactDetailsRequest(BaseModel):
    """Request model for getting artifact details."""

    artifact_name: str = Field(..., description="The artifact name to retrieve details for")
    artifact_type: ArtifactType = Field(
        ...,
        description="Type of artifact: 'glossary_term' or 'data_class'"
    )
    format: str = Field(
        "table",
        description="Output format: 'table' for formatted output, 'json' for structured data"
    )


class RelationshipSummary(BaseModel):
    """Summary of a single relationship."""
    
    name: str = Field(..., description="Name of the related artifact")
    type: str = Field(..., description="Type of relationship")


class VersionDetails(BaseModel):
    """Details for a specific version of an artifact."""
    
    version_id: Optional[str] = Field(None, description="Version ID")
    state: Optional[str] = Field(None, description="Version state (e.g., DRAFT, PUBLISHED)")
    long_description: Optional[str] = Field(None, description="Long description")
    short_description: Optional[str] = Field(None, description="Short description")
    steward_names: Optional[List[str]] = Field(None, description="List of data steward names")
    relationships: List[RelationshipSummary] = Field(
        default_factory=list,
        description="List of relationships for this version"
    )


class ArtifactDetails(BaseModel):
    """Detailed information about a glossary artifact with version comparison."""

    artifact_id: str = Field(..., description="Artifact ID")
    name: str = Field(..., description="Artifact name")
    artifact_type: ArtifactType = Field(..., description="Type of artifact")
    url: Optional[str] = Field(None, description="Formatted URL to view artifact in the UI")
    
    # Version details
    latest_version: VersionDetails = Field(..., description="Latest version details")
    previous_version: Optional[VersionDetails] = Field(
        None,
        description="Previous version details for comparison"
    )
    
    # Workflow metadata
    workflow_id: Optional[str] = Field(None, description="Workflow ID for draft artifacts")
    workflow_state: Optional[str] = Field(None, description="Workflow state")


class GetArtifactDetailsResponse(BaseResponseModel):
    """Response model for getting artifact details."""

    artifact_details: ArtifactDetails = Field(
        ...,
        description="Available details about the artifact"
    )
    formatted_output: Optional[str] = Field(
        None,
        description="Formatted table output when format='table'"
    )

# Made with Bob
