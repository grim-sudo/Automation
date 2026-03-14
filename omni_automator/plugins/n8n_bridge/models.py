"""
Pydantic v2 models for the n8n REST API.

All objects match the n8n API v1 data shapes so they can be validated
directly from API responses.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "N8nConfig",
    "N8nNode",
    "N8nConnection",
    "N8nWorkflow",
    "N8nWorkflowList",
    "N8nExecutionResult",
    "N8nWebhookPayload",
]


class N8nConfig(BaseModel):
    """Connection settings for an n8n instance.

    Attributes:
        url:     Base URL (e.g. ``http://localhost:5678``).
        api_key: n8n REST API key (X-N8N-API-KEY header).
        timeout: HTTP timeout in seconds.
    """

    url: str = "http://localhost:5678"
    api_key: str = ""
    timeout: int = 30


class N8nNode(BaseModel):
    """A single node in an n8n workflow graph.

    Attributes:
        id:         Node UUID assigned by n8n.
        name:       Display name shown in the editor.
        type:       Full n8n node type string (e.g. ``n8n-nodes-base.webhook``).
        type_version: Node type version (usually 1 or 2).
        position:   [x, y] canvas coordinates.
        parameters: Node-specific configuration dict.
        credentials: Credential bindings (service name → credential id).
    """

    id: str = ""
    name: str = ""
    type: str = ""
    type_version: float = Field(default=1.0, alias="typeVersion")
    position: list[float] = Field(default_factory=lambda: [0.0, 300.0])
    parameters: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class N8nConnection(BaseModel):
    """Directed edge between two nodes.

    Attributes:
        node:  Target node name.
        type:  Connection type (usually ``"main"``).
        index: Output index on the source node.
    """

    node: str
    type: str = "main"
    index: int = 0


class N8nWorkflow(BaseModel):
    """A complete n8n workflow.

    Attributes:
        id:          Workflow UUID (empty before creation).
        name:        Workflow display name.
        active:      Whether the workflow is active (trigger-eligible).
        nodes:       List of workflow nodes.
        connections: Adjacency map ``{source_node: {output_type: [[connection, …], …]}}``
        settings:    Optional workflow-level settings.
        tags:        Tag labels for organisation.
    """

    id: str = ""
    name: str = "Untitled Workflow"
    active: bool = False
    nodes: list[N8nNode] = Field(default_factory=list)
    connections: dict[str, Any] = Field(default_factory=dict)
    settings: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class N8nWorkflowList(BaseModel):
    """Paginated list of workflows returned by ``GET /api/v1/workflows``.

    Attributes:
        data:        List of workflow objects.
        next_cursor: Cursor for the next page (empty if last page).
    """

    data: list[N8nWorkflow] = Field(default_factory=list)
    next_cursor: str = Field(default="", alias="nextCursor")

    model_config = {"populate_by_name": True}


class N8nExecutionResult(BaseModel):
    """Result of a single workflow execution.

    Attributes:
        id:         Execution UUID.
        status:     One of ``waiting | running | success | error | canceled``.
        finished:   Whether execution has completed.
        workflow_id: Parent workflow UUID.
        data:       Raw execution data payload.
        error:      Error message if status is ``error``.
        started_at: ISO-8601 timestamp of execution start.
        stopped_at: ISO-8601 timestamp of execution end.
    """

    id: str = ""
    status: str = "unknown"
    finished: bool = False
    workflow_id: str = Field(default="", alias="workflowId")
    data: dict[str, Any] = Field(default_factory=dict)
    error: str = ""
    started_at: str = Field(default="", alias="startedAt")
    stopped_at: str = Field(default="", alias="stoppedAt")

    model_config = {"populate_by_name": True}


class N8nWebhookPayload(BaseModel):
    """Payload sent to or received from an n8n webhook node.

    Attributes:
        data:    Arbitrary data body.
        headers: HTTP headers dict.
    """

    data: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
