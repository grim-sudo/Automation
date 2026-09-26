"""
GUI/TUI-facing gateway over :class:`WorkflowManager`.

The raw :class:`WorkflowManager` speaks in Pydantic models and the full n8n
REST surface. UI surfaces only need a handful of operations and prefer plain
dicts they can drop straight into widgets. This gateway is that thin, stable
seam — it owns the model→dict shaping so the GUI never imports n8n internals.

All methods stay ``async`` so callers keep driving them on their existing
background event loop.
"""

from __future__ import annotations

from typing import Any

from .models import N8nConfig, N8nNode, N8nWorkflow
from .workflow_manager import WorkflowManager

__all__ = ["N8nGateway"]


class N8nGateway:
    """Async, dict-returning facade over the n8n REST client.

    Args:
        url:     Base URL of the n8n instance.
        api_key: n8n REST API key (``X-N8N-API-KEY``).
    """

    def __init__(self, url: str, api_key: str) -> None:
        self._manager = WorkflowManager(N8nConfig(url=url, api_key=api_key))

    @staticmethod
    def _trigger_of(wf: N8nWorkflow) -> str:
        """Best-effort human label for a workflow's trigger node."""
        for node in wf.nodes:
            ntype = (node.type or "").lower()
            if "trigger" in ntype or "webhook" in ntype or "cron" in ntype:
                return node.name or node.type.split(".")[-1]
        return "manual"

    def _to_dict(self, wf: N8nWorkflow) -> dict[str, Any]:
        return {
            "id": wf.id or "",
            "name": wf.name,
            "active": wf.active,
            "trigger": self._trigger_of(wf),
            "executionCount": 0,  # n8n list endpoint omits counts; filled on demand
        }

    async def list_workflows(self) -> list[dict[str, Any]]:
        """Return all workflows as GUI-friendly dicts."""
        return [self._to_dict(wf) for wf in await self._manager.list_workflows()]

    async def trigger_workflow(self, workflow_id: str) -> str:
        """Run a workflow on demand; return a short status string."""
        result = await self._manager.execute_workflow(workflow_id)
        status = result.status or ("finished" if result.finished else "started")
        if result.error:
            return f"{status}: {result.error}"
        return f"Execution {result.id or '—'} — {status}"

    async def create_workflow(self, name: str, description: str = "") -> dict[str, Any]:
        """Create an empty, inactive workflow with a manual trigger node.

        n8n rejects workflows with zero nodes, so we seed a single manual
        trigger. ``description`` is stored as a tag for now (n8n has no
        first-class description field on the workflow object).
        """
        node = N8nNode(
            name="When clicking 'Execute'",
            type="n8n-nodes-base.manualTrigger",
            type_version=1,
            position=[260.0, 300.0],
        )
        workflow = N8nWorkflow(name=name, nodes=[node])
        if description:
            workflow.settings = {"description": description}
        created = await self._manager.create_workflow(workflow)
        return self._to_dict(created)
