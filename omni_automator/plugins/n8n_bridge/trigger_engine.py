"""
Trigger and polling engine for n8n workflow executions.

Provides:
  * Execution status polling (with configurable interval).
  * Lightweight aiohttp webhook listener for receiving n8n callbacks.
  * Helper to update a workflow's cron trigger expression.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from loguru import logger

from .models import N8nConfig, N8nExecutionResult, N8nWorkflow
from .workflow_manager import WorkflowManager

__all__ = [
    "poll_execution_status",
    "setup_webhook_listener",
    "schedule_workflow",
]

_DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes max poll


async def poll_execution_status(
    workflow_id: str,
    execution_id: str,
    config: N8nConfig,
    interval: int = 5,
    timeout: int = _DEFAULT_TIMEOUT_SECONDS,
) -> N8nExecutionResult:
    """Poll n8n until *execution_id* reaches a terminal state.

    Args:
        workflow_id:  Workflow UUID (used to scope API calls).
        execution_id: Execution UUID to track.
        config:       N8nConfig with connection details.
        interval:     Polling interval in seconds.
        timeout:      Maximum seconds to wait before raising TimeoutError.

    Returns:
        N8nExecutionResult when status is ``success``, ``error``, or ``canceled``.

    Raises:
        asyncio.TimeoutError: If *timeout* is exceeded.
        httpx.HTTPError:      On API failure.
    """
    import httpx

    terminal_states = {"success", "error", "canceled", "crashed"}
    elapsed = 0

    async with httpx.AsyncClient(
        base_url=config.url.rstrip("/") + "/api/v1",
        headers={"X-N8N-API-KEY": config.api_key},
        timeout=float(config.timeout),
    ) as client:
        while elapsed < timeout:
            resp = await client.get(f"/executions/{execution_id}")
            resp.raise_for_status()
            result = N8nExecutionResult.model_validate(resp.json())
            logger.debug("Execution {} status={} elapsed={}s", execution_id, result.status, elapsed)

            if result.status.lower() in terminal_states:
                return result

            await asyncio.sleep(interval)
            elapsed += interval

    raise asyncio.TimeoutError(
        f"Execution {execution_id} did not complete within {timeout} seconds."
    )


async def setup_webhook_listener(
    port: int,
    path: str,
    callback: Callable[[dict[str, Any]], None],
) -> None:
    """Spin up a lightweight aiohttp server to receive n8n webhook callbacks.

    The server listens on ``http://0.0.0.0:{port}{path}`` (POST) and calls
    *callback* with the parsed JSON body.  Runs until cancelled.

    Args:
        port:     TCP port to bind.
        path:     URL path (e.g. ``"/webhook"``).
        callback: Async or sync callable receiving the JSON body dict.

    Raises:
        ImportError: If ``aiohttp`` is not installed.
    """
    try:
        from aiohttp import web
    except ImportError as exc:
        raise ImportError(
            "aiohttp is required for setup_webhook_listener. Install with: pip install aiohttp"
        ) from exc

    async def _handler(request: web.Request) -> web.Response:
        try:
            body: dict[str, Any] = await request.json()
        except Exception:
            body = {}
        logger.debug("Webhook received on {}: {}", path, body)
        if asyncio.iscoroutinefunction(callback):
            await callback(body)
        else:
            callback(body)
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_post(path, _handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Webhook listener started at http://0.0.0.0:{}{}", port, path)

    # Keep running until the coroutine is cancelled
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Webhook listener stopped.")
        await runner.cleanup()


async def schedule_workflow(
    workflow_id: str,
    cron_expression: str,
    config: N8nConfig,
) -> bool:
    """Update the first cron/schedule trigger node in *workflow_id*.

    Fetches the workflow, searches for a ``scheduleTrigger`` node, updates
    its ``rule`` parameter to *cron_expression*, then PUTs the workflow back.

    Args:
        workflow_id:     Workflow UUID.
        cron_expression: Standard cron expression (e.g. ``"0 9 * * *"``).
        config:          N8nConfig for the n8n instance.

    Returns:
        True if update succeeded, False if no trigger node was found.

    Raises:
        httpx.HTTPError: On API failure.
    """
    manager = WorkflowManager(config)
    workflow: N8nWorkflow = await manager.get_workflow(workflow_id)

    updated = False
    for node in workflow.nodes:
        if "scheduleTrigger" in node.type or "cron" in node.type.lower():
            node.parameters["rule"] = {
                "interval": [{"field": "cronExpression", "expression": cron_expression}]
            }
            node.parameters["cronExpression"] = cron_expression
            updated = True
            logger.info("Updated cron trigger in node '{}' to '{}'", node.name, cron_expression)
            break

    if not updated:
        logger.warning("No schedule/cron trigger node found in workflow {}", workflow_id)
        return False

    await manager.update_workflow(workflow_id, workflow)
    return True
