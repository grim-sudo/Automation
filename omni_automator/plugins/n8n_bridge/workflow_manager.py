"""
Async HTTP client wrapping the n8n REST API v1.

All methods are async and use httpx.AsyncClient.
Authentication uses the X-N8N-API-KEY header.
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from .models import N8nConfig, N8nExecutionResult, N8nWorkflow

__all__ = ["WorkflowManager"]


class WorkflowManager:
    """Async wrapper around the n8n /api/v1 REST endpoints.

    Args:
        config: N8nConfig with url and api_key.
    """

    def __init__(self, config: N8nConfig) -> None:
        self._config = config

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._config.url.rstrip("/") + "/api/v1",
            headers={"X-N8N-API-KEY": self._config.api_key, "Content-Type": "application/json"},
            timeout=float(self._config.timeout),
        )

    # ── Workflow CRUD ─────────────────────────────────────────────────────────

    async def list_workflows(self) -> list[N8nWorkflow]:
        """List all workflows on the n8n instance.

        Returns:
            List of N8nWorkflow objects.

        Raises:
            httpx.HTTPError: On network or API error.
        """
        async with self._client() as client:
            resp = await client.get("/workflows")
            resp.raise_for_status()
            data = resp.json()
        raw_list = data if isinstance(data, list) else data.get("data", [])
        return [N8nWorkflow.model_validate(w) for w in raw_list]

    async def get_workflow(self, workflow_id: str) -> N8nWorkflow:
        """Fetch a single workflow by ID.

        Args:
            workflow_id: Workflow UUID.

        Returns:
            N8nWorkflow.

        Raises:
            httpx.HTTPError: On network or API error.
        """
        async with self._client() as client:
            resp = await client.get(f"/workflows/{workflow_id}")
            resp.raise_for_status()
            return N8nWorkflow.model_validate(resp.json())

    async def create_workflow(self, workflow: N8nWorkflow) -> N8nWorkflow:
        """Create a new workflow.

        Args:
            workflow: N8nWorkflow to create (id should be empty).

        Returns:
            Created N8nWorkflow with server-assigned id.

        Raises:
            httpx.HTTPError: On network or API error.
        """
        # n8n API: 'active' and 'tags' are read-only at creation time
        payload = workflow.model_dump(by_alias=True, exclude_none=True, exclude={"active", "tags"})
        async with self._client() as client:
            resp = await client.post("/workflows", json=payload)
            resp.raise_for_status()
            return N8nWorkflow.model_validate(resp.json())

    async def update_workflow(self, workflow_id: str, workflow: N8nWorkflow) -> N8nWorkflow:
        """Update an existing workflow.

        Args:
            workflow_id: UUID of the workflow to update.
            workflow:    Updated N8nWorkflow data.

        Returns:
            Updated N8nWorkflow.

        Raises:
            httpx.HTTPError: On network or API error.
        """
        payload = workflow.model_dump(by_alias=True, exclude_none=True)
        async with self._client() as client:
            resp = await client.put(f"/workflows/{workflow_id}", json=payload)
            resp.raise_for_status()
            return N8nWorkflow.model_validate(resp.json())

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow.

        Args:
            workflow_id: UUID of the workflow to delete.

        Returns:
            True on success.

        Raises:
            httpx.HTTPError: On network or API error.
        """
        async with self._client() as client:
            resp = await client.delete(f"/workflows/{workflow_id}")
            resp.raise_for_status()
        return True

    async def activate_workflow(self, workflow_id: str) -> bool:
        """Activate a workflow (enable its trigger).

        Args:
            workflow_id: Workflow UUID.

        Returns:
            True on success.

        Raises:
            httpx.HTTPError: On network or API error.
        """
        async with self._client() as client:
            resp = await client.patch(f"/workflows/{workflow_id}/activate")
            resp.raise_for_status()
        logger.info("Activated workflow {}", workflow_id)
        return True

    async def deactivate_workflow(self, workflow_id: str) -> bool:
        """Deactivate a workflow.

        Args:
            workflow_id: Workflow UUID.

        Returns:
            True on success.

        Raises:
            httpx.HTTPError: On network or API error.
        """
        async with self._client() as client:
            resp = await client.patch(f"/workflows/{workflow_id}/deactivate")
            resp.raise_for_status()
        logger.info("Deactivated workflow {}", workflow_id)
        return True

    # ── Execution ─────────────────────────────────────────────────────────────

    async def execute_workflow(
        self, workflow_id: str, payload: dict[str, Any] | None = None
    ) -> N8nExecutionResult:
        """Trigger an on-demand execution of a workflow.

        Args:
            workflow_id: Workflow UUID.
            payload:     Optional data dict to pass as the execution body.

        Returns:
            N8nExecutionResult with the execution id and status.

        Raises:
            httpx.HTTPError: On network or API error.
        """
        body: dict[str, Any] = {"workflowData": {"id": workflow_id}}
        if payload:
            body["runData"] = payload
        async with self._client() as client:
            resp = await client.post(f"/workflows/{workflow_id}/run", json=body)
            resp.raise_for_status()
            return N8nExecutionResult.model_validate(resp.json())

    async def get_executions(self, workflow_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve recent executions for a workflow.

        Args:
            workflow_id: Workflow UUID.
            limit:       Maximum number of executions to return.

        Returns:
            List of raw execution dicts as returned by the n8n API.

        Raises:
            httpx.HTTPError: On network or API error.
        """
        async with self._client() as client:
            resp = await client.get(
                "/executions",
                params={"workflowId": workflow_id, "limit": limit},
            )
            resp.raise_for_status()
            data = resp.json()
        return data if isinstance(data, list) else data.get("data", [])
