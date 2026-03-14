"""
Registry mapping human-readable service names to n8n node type strings.

Provides ``get_node_type(service)`` for resolving NL service mentions.
"""

from __future__ import annotations

__all__ = ["NODE_REGISTRY", "get_node_type"]

NODE_REGISTRY: dict[str, str] = {
    "email": "n8n-nodes-base.emailReadImap",
    "gmail": "n8n-nodes-base.gmail",
    "slack": "n8n-nodes-base.slack",
    "github": "n8n-nodes-base.github",
    "jira": "n8n-nodes-base.jira",
    "http": "n8n-nodes-base.httpRequest",
    "webhook": "n8n-nodes-base.webhook",
    "cron": "n8n-nodes-base.scheduleTrigger",
    "schedule": "n8n-nodes-base.scheduleTrigger",
    "postgres": "n8n-nodes-base.postgres",
    "postgresql": "n8n-nodes-base.postgres",
    "mysql": "n8n-nodes-base.mySql",
    "redis": "n8n-nodes-base.redis",
    "s3": "n8n-nodes-base.awsS3",
    "aws_s3": "n8n-nodes-base.awsS3",
    "discord": "n8n-nodes-base.discord",
    "telegram": "n8n-nodes-base.telegram",
    "notion": "n8n-nodes-base.notion",
    "airtable": "n8n-nodes-base.airtable",
    "google_sheets": "n8n-nodes-base.googleSheets",
    "sheets": "n8n-nodes-base.googleSheets",
    "code": "n8n-nodes-base.code",
    "if": "n8n-nodes-base.if",
    "switch": "n8n-nodes-base.switch",
    "merge": "n8n-nodes-base.merge",
    "set": "n8n-nodes-base.set",
    "twitter": "n8n-nodes-base.twitter",
    "hubspot": "n8n-nodes-base.hubspot",
    "salesforce": "n8n-nodes-base.salesforce",
    "trello": "n8n-nodes-base.trello",
    "asana": "n8n-nodes-base.asana",
}

# Aliases for trigger-type services
_TRIGGER_TYPES = {"webhook", "cron", "schedule", "github"}


def get_node_type(service: str) -> str | None:
    """Return the n8n node type string for *service*, or ``None`` if unknown.

    Performs case-insensitive lookup with normalisation (spaces → underscores).

    Args:
        service: Human-readable service name (e.g. ``"google_sheets"`` or ``"Gmail"``).

    Returns:
        Full n8n node type string, or ``None`` if not in the registry.
    """
    normalised = service.lower().strip().replace(" ", "_").replace("-", "_")
    return NODE_REGISTRY.get(normalised)


def is_trigger(service: str) -> bool:
    """Return True if the service should be used as a workflow trigger node.

    Args:
        service: Service name.

    Returns:
        Boolean.
    """
    return service.lower().strip().replace(" ", "_") in _TRIGGER_TYPES
