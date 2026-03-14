"""
Build n8n workflow JSON graphs from structured or natural language intent.

The builder takes a list of ``{"service": name, "config": {...}}`` step
dicts and converts them into a fully wired N8nWorkflow with correct
positions and connections.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from loguru import logger

from .models import N8nConnection, N8nNode, N8nWorkflow
from .node_registry import NODE_REGISTRY, get_node_type, is_trigger

__all__ = [
    "build_linear_workflow",
    "build_trigger_action_workflow",
    "parse_nl_to_steps",
    "add_error_handler",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_node(service: str, config: dict[str, Any], index: int) -> N8nNode:
    """Create a positioned N8nNode from a service name and config.

    Args:
        service: Service name (resolved via NODE_REGISTRY).
        config:  Free-form parameters dict merged into node.parameters.
        index:   Sequential index used to calculate canvas position.

    Returns:
        N8nNode instance.
    """
    node_type = get_node_type(service) or "n8n-nodes-base.code"
    return N8nNode(
        id=str(uuid.uuid4()),
        name=service.capitalize().replace("_", " "),
        type=node_type,
        **{"typeVersion": 1},
        position=[float(index * 200), 300.0],
        parameters=dict(config),
    )


def _connect_linear(nodes: list[N8nNode]) -> dict[str, Any]:
    """Wire nodes in linear order: node[0] → node[1] → … → node[n-1].

    Args:
        nodes: Ordered list of workflow nodes.

    Returns:
        n8n connections dict.
    """
    connections: dict[str, Any] = {}
    for i in range(len(nodes) - 1):
        src = nodes[i].name
        dst = nodes[i + 1].name
        connections[src] = {
            "main": [[{"node": dst, "type": "main", "index": 0}]]
        }
    return connections


# ---------------------------------------------------------------------------
# Public builders
# ---------------------------------------------------------------------------

def build_linear_workflow(name: str, steps: list[dict[str, Any]]) -> N8nWorkflow:
    """Build a linear workflow from an ordered list of steps.

    Args:
        name:  Human-readable workflow name.
        steps: List of dicts with keys ``service`` (required) and ``config``
               (optional dict).  Example: ``[{"service": "webhook"}, {"service": "slack",
               "config": {"channel": "#alerts"}}]``.

    Returns:
        Fully wired N8nWorkflow ready to POST to the n8n API.
    """
    nodes: list[N8nNode] = []
    for i, step in enumerate(steps):
        service = step.get("service", "code")
        config = step.get("config", {})
        nodes.append(_make_node(service, config, i))

    return N8nWorkflow(
        name=name,
        nodes=nodes,
        connections=_connect_linear(nodes),
    )


def build_trigger_action_workflow(
    name: str,
    trigger: dict[str, Any],
    actions: list[dict[str, Any]],
) -> N8nWorkflow:
    """Build a trigger + N action workflow.

    Args:
        name:    Workflow name.
        trigger: Single trigger step dict (``{"service": "webhook", "config": {}}``)
        actions: List of action step dicts.

    Returns:
        N8nWorkflow.
    """
    all_steps = [trigger] + actions
    return build_linear_workflow(name=name, steps=all_steps)


def parse_nl_to_steps(nl_command: str) -> list[dict[str, Any]]:
    """Extract workflow steps from a natural language description.

    Patterns handled:
    * ``when {service} push/event, send/post to {service}``
    * ``every day at 9am, fetch {service} and save to {service}``
    * ``on {service}, transform data and post to {service}``
    * Any mention of a known service name triggers inclusion.

    Args:
        nl_command: Natural language workflow description.

    Returns:
        List of step dicts with ``service`` and ``config`` keys.

    Raises:
        Nothing — returns ``[]`` when no services can be detected.
    """
    text = nl_command.lower()
    steps: list[dict[str, Any]] = []
    seen: set[str] = set()

    # ── Phase 1: detect explicit trigger phrasing ─────────────────────────────
    # "when X" / "on X" / "every …"
    trigger_match = re.search(
        r"\b(?:when|on)\s+([\w\s]+?)(?:\s+(?:push|event|trigger|fires|occurs|is received))?\s*[,;]",
        text,
    )
    if trigger_match:
        trigger_svc = trigger_match.group(1).strip().replace(" ", "_")
        # check if in registry; fall back to "webhook"
        if get_node_type(trigger_svc):
            steps.append({"service": trigger_svc, "config": {}})
            seen.add(trigger_svc)
        else:
            steps.append({"service": "webhook", "config": {}})
            seen.add("webhook")

    cron_match = re.search(r"\bevery\s+(day|hour|week|minute|\d+\s*(?:min(?:ute)?s?))\b", text)
    if cron_match and "cron" not in seen:
        expr = _parse_cron_hint(cron_match.group(1))
        steps.append({"service": "cron", "config": {"rule": expr}})
        seen.add("cron")

    # ── Phase 2: detect remaining services by name ─────────────────────────────
    for svc_key in NODE_REGISTRY:
        pattern = svc_key.replace("_", r"[\s_-]?")
        if re.search(r"\b" + pattern + r"\b", text) and svc_key not in seen:
            is_trig = is_trigger(svc_key) and not steps  # only first for trigger pos
            steps.append({"service": svc_key, "config": {}})
            seen.add(svc_key)

    # ── Phase 3: fallback – single webhook trigger if nothing identified ───────
    if not steps:
        logger.warning("parse_nl_to_steps: could not identify services in: {!r}", nl_command)
        steps = [{"service": "webhook", "config": {}}, {"service": "code", "config": {}}]

    return steps


def _parse_cron_hint(hint: str) -> str:
    """Convert a rough time description to a cron expression.

    Args:
        hint: Text like ``"day"``, ``"hour"``, ``"5 minutes"`` etc.

    Returns:
        Cron expression string.
    """
    hint = hint.strip().lower()
    if "day" in hint:
        return "0 9 * * *"         # 9 am daily
    if "hour" in hint:
        return "0 * * * *"         # top of every hour
    if "week" in hint:
        return "0 9 * * 1"         # Monday 9 am
    m = re.search(r"(\d+)\s*min", hint)
    if m:
        return f"*/{m.group(1)} * * * *"
    return "0 * * * *"             # fallback: hourly


def add_error_handler(workflow: N8nWorkflow, error_webhook_url: str = "") -> N8nWorkflow:
    """Append an error-handler node to *workflow*.

    The error node posts to *error_webhook_url* (or a mock endpoint if
    not configured).  It is connected to the last regular node.

    Args:
        workflow:          Workflow to augment.
        error_webhook_url: URL to POST error payloads to.

    Returns:
        Modified N8nWorkflow (mutated in-place and returned).
    """
    last_index = len(workflow.nodes)
    error_node = N8nNode(
        id=str(uuid.uuid4()),
        name="Error Handler",
        type="n8n-nodes-base.httpRequest",
        **{"typeVersion": 1},
        position=[float(last_index * 200), 500.0],
        parameters={
            "method": "POST",
            "url": error_webhook_url or "https://httpbin.org/post",
            "sendBody": True,
            "bodyParameters": {"parameters": [{"name": "error", "value": "={{ $json.error }}"}]},
        },
    )
    workflow.nodes.append(error_node)

    # Wire last regular node's error output to the error handler
    if workflow.nodes[:-1]:
        last_regular = workflow.nodes[-2].name
        if last_regular not in workflow.connections:
            workflow.connections[last_regular] = {}
        workflow.connections[last_regular]["error"] = [
            [{"node": "Error Handler", "type": "main", "index": 0}]
        ]

    return workflow
