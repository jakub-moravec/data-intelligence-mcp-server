# Copyright [2026] [IBM]
# Licensed under the Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)
# See the LICENSE file in the project root for license information.

"""Shared Field description strings for metadata import job control models."""

# ── Request field descriptions ────────────────────────────────────────────────

DESC_PROJECT_NAME = "The name or ID of the project containing the metadata import."

DESC_METADATA_IMPORT_NAME = "The name or ID of the metadata import asset."

DESC_ACTION = (
    "The action to perform on the job run. "
    "Use 'pause' to temporarily pause a running or queued job, "
    "'resume' to continue a paused job, "
    "or 'cancel' to permanently stop a job (cannot be undone)."
)

DESC_JOB_RUN_ID = (
    "Optional specific job run ID to act on. "
    "If not provided, the latest eligible job run will be used."
)

# ── Response field descriptions ───────────────────────────────────────────────

DESC_METADATA_IMPORT_ID = "The unique identifier of the metadata import asset."

DESC_METADATA_IMPORT_NAME_RESPONSE = "The name of the metadata import asset."

DESC_JOB_ID = "The unique identifier of the metadata import job."

DESC_JOB_RUN_ID_RESPONSE = "The unique identifier of the job run."

DESC_METADATA_IMPORT_JOB_RUN_UI_URL = "The URL to view the job run in the UI."
