"""
n8n bridge plugin for OmniAutomator.

Provides natural-language creation, management, and triggering of n8n
workflows through the n8n REST API v1.

Sub-modules
-----------
models          — Pydantic v2 models for n8n API objects.
workflow_manager — Async CRUD client for n8n /api/v1/workflows.
node_registry   — Service-name → n8n-node-type mapping.
node_builder    — Build workflow graphs from structured or NL intent.
trigger_engine  — Execution polling and webhook listener.
"""

from .models import (
    N8nConfig,
    N8nConnection,
    N8nExecutionResult,
    N8nNode,
    N8nWebhookPayload,
    N8nWorkflow,
    N8nWorkflowList,
)
from .node_builder import (
    add_error_handler,
    build_linear_workflow,
    build_trigger_action_workflow,
    parse_nl_to_steps,
)
from .node_registry import NODE_REGISTRY, get_node_type
from .trigger_engine import (
    poll_execution_status,
    schedule_workflow,
    setup_webhook_listener,
)
from .workflow_manager import WorkflowManager

__all__ = [
    # models
    "N8nConfig",
    "N8nConnection",
    "N8nExecutionResult",
    "N8nNode",
    "N8nWebhookPayload",
    "N8nWorkflow",
    "N8nWorkflowList",
    # workflow manager
    "WorkflowManager",
    # node registry
    "NODE_REGISTRY",
    "get_node_type",
    # node builder
    "build_linear_workflow",
    "build_trigger_action_workflow",
    "parse_nl_to_steps",
    "add_error_handler",
    # trigger engine
    "poll_execution_status",
    "setup_webhook_listener",
    "schedule_workflow",
]
