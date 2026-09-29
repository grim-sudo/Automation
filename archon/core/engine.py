"""
Core automation engine that orchestrates all automation operations
"""

import os
import platform
import re
import time
from datetime import datetime
from typing import Any

from loguru import logger

from ..capabilities import build_registry_from_plugin_manager
from ..os_adapters.adapter_factory import OSAdapterFactory
from ..parsers.ai_parser import AIEnhancedParser
from ..parsers.command_parser import AdvancedCommandParser, CommandComplexity
from ..security.permission_manager import PermissionManager
from ..utils.codegen import generate_fibonacci_code, generate_prime_number_code
from ..utils.file_resolver import resolve_file_with_disambiguation
from ..utils.logger import setup_logger
from ..workflow.engine import WorkflowEngine
from .plugin_manager import PluginManager


class Archon:
    """Main automation engine that coordinates all operations"""

    def __init__(self, config: dict[str, Any] | None = None):
        """Initialize the automation engine"""
        try:
            self.config = config or {}
            self.logger = setup_logger("Archon")

            # Validate configuration
            self._validate_config()

            # Initialize core components with error handling
            self.os_adapter = OSAdapterFactory.create_adapter()
            self.command_parser = AdvancedCommandParser()
            self.advanced_parser = AdvancedCommandParser()

            # Initialize AI parser (local Ollama backend; no API key required)
            self.ai_parser = AIEnhancedParser()
            self.plugin_manager = PluginManager()
            # Optional category -> plugin name aliases for backward compatibility
            self.plugin_aliases = {
                "devops": "devops_generator",
                "project": "project_generator",
                "web": "web_automation",
                "folder_ops": "folder_operations",
            }
            self.permission_manager = PermissionManager()
            self.workflow_engine = WorkflowEngine(self)

            # Capability registry: the execution router.  Every loaded plugin is
            # exposed through the capability surface (name -> actions -> risk) and
            # `_execute_parsed_command` resolves + dispatches actions through it.
            # PluginManager remains the loader/lifecycle owner.
            self.capability_registry = build_registry_from_plugin_manager(
                self.plugin_manager,
                permission_manager=self.permission_manager,
            )

            # Execution state
            self.is_running = False
            self.execution_history = []
            # Sandbox mode removed: always run in normal mode
            self.sandbox_mode = False

            self.logger.info(f"Archon initialized on {platform.system()} {platform.release()}")

        except Exception as e:
            if hasattr(self, "logger"):
                self.logger.error(f"Failed to initialize Archon: {e}")
            else:
                logger.error(f"Critical error during initialization: {e}")
            raise

    def _validate_config(self):
        """Validate configuration parameters"""
        if not isinstance(self.config, dict):
            raise ValueError("Configuration must be a dictionary")

        # Validate sandbox mode
        if "sandbox_mode" in self.config:
            if not isinstance(self.config["sandbox_mode"], bool):
                raise ValueError("sandbox_mode must be a boolean")

        # Validate continue_on_error
        if "continue_on_error" in self.config:
            if not isinstance(self.config["continue_on_error"], bool):
                raise ValueError("continue_on_error must be a boolean")

    def _is_dangerous_command(self, command: str) -> bool:
        """Check if command contains potentially dangerous operations.

        Delegates to the security policy layer (single source of truth).
        """
        return self.permission_manager.is_dangerous_command(command)

    def _is_too_complex_for_ai(self, command: str) -> bool:
        """Check if command is too complex for AI parsing (likely to cause JSON errors)"""
        import re

        # Very long commands with nested loops tend to break AI JSON parsing
        if len(command) > 200:
            # Check for nested/loop structures
            nested_patterns = [
                r"in\s+(?:that|those|each|every)",
                r"and\s+in\s+",
                r"inside\s+(?:each|every)",
                r"\d+\s+folders?.*\d+\s+folders?",
                r"table \d+ to table \d+",
            ]

            for pattern in nested_patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return True

            # Multiple action conjunctions also indicate complexity
            actions = command.lower().count(" and ")
            if actions >= 3:
                return True

        return False

    def _normalize_screenshot_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Normalize various filename/path keys into a consistent `path` key for screenshots."""
        if not isinstance(params, dict):
            return params

        filename_keys = [
            "filename",
            "file",
            "path",
            "dest",
            "destination",
            "save_to",
            "output",
            "save_path",
            "target",
        ]
        for k in filename_keys:
            if k in params and params.get(k):
                # prefer an explicit 'path' key for downstream plugins
                params["path"] = params.get(k)
                break

        # Also accept nested context
        if "workflow_context" in params and isinstance(params["workflow_context"], dict):
            wc = params["workflow_context"]
            for k in filename_keys:
                if k in wc and wc.get(k) and not params.get("path"):
                    params["path"] = wc.get(k)
                    break

        return params

    def execute(self, command: str, **kwargs) -> dict[str, Any]:
        """Execute an automation command (simple or complex)"""
        start = time.monotonic()
        try:
            # Input validation
            if not command or not isinstance(command, str):
                raise ValueError("Command must be a non-empty string")

            command = command.strip()
            if not command:
                raise ValueError("Command cannot be empty or whitespace only")

            # Security check for potentially dangerous commands
            if self._is_dangerous_command(command) and not self.sandbox_mode:
                self.logger.warning(f"Potentially dangerous command detected: {command}")

            self.logger.info(f"Executing command: {command}")

            # Custom-OS / distro build is a first-class capability that the
            # parser/plugin router can't express as a single action. Detect the
            # intent up front and route to the real build pipeline so the same
            # chat/run entry point reaches the OS builder.
            distro_result = self._maybe_build_distro(command)
            if distro_result is not None:
                self._log_execution(
                    command, {"action": "build_distro", "category": "distro_builder"},
                    distro_result, success=distro_result.get("success", False),
                    duration=time.monotonic() - start,
                )
                ok = distro_result.get("success", False)
                payload = {
                    "success": ok,
                    "result": distro_result,
                    "command": command,
                    "complexity": "workflow",
                    "route": "distro_builder.build_distro",
                    "timestamp": datetime.now().isoformat(),
                }
                if not ok:
                    # Surface the builder's message at the top level so chat/CLI
                    # renders the real reason (e.g. "needs root") instead of
                    # "Unknown error".
                    payload["error"] = distro_result.get("message", "Distro build failed")
                    payload["fallback_message"] = distro_result.get("message", "")
                return payload

            # "Add more info / expand / make more detailed" on an existing file is
            # really read → AI-enhance → write. The AI planner tends to emit a
            # fragile 3-step plan (read_file → invented generate_enhanced_content →
            # create_file) that no execution path can satisfy. Detect the intent up
            # front and run it as one real step instead.
            enhance_result = self._maybe_enhance_document(command)
            if enhance_result is not None:
                self._log_execution(
                    command, {"action": "enhance_file", "category": "filesystem"},
                    enhance_result, success=enhance_result.get("success", False),
                    duration=time.monotonic() - start,
                )
                ok = enhance_result.get("success", False)
                payload = {
                    "success": ok,
                    "result": enhance_result,
                    "command": command,
                    "complexity": "simple",
                    "route": "filesystem.enhance_file",
                    "timestamp": datetime.now().isoformat(),
                }
                if not ok:
                    payload["error"] = enhance_result.get("error", "Document enhancement failed")
                return payload

            # Check if command is too complex for AI (very long with nested structures)
            # Use fallback parser directly for these cases
            if self._is_too_complex_for_ai(command):
                self.logger.info("Command is too complex for AI, using advanced parser directly")
                complex_command = self.advanced_parser.parse_complex_command(command)
            # Use AI-enhanced parsing if available, otherwise fall back to advanced parsing
            elif self.ai_parser.get_ai_status()["available"]:
                self.logger.info("Using AI-enhanced command parsing")
                complex_command = self.ai_parser.parse_with_ai(
                    command, self._get_execution_context()
                )
            else:
                self.logger.info("Using advanced command parsing (AI not available)")
                complex_command = self.advanced_parser.parse_complex_command(command)

            if complex_command.complexity == CommandComplexity.SIMPLE:
                # Prefer the step the (AI or advanced) parser already produced.
                # Re-parsing the raw command with the naive command_parser threw
                # away the AI's correct routing — so "create a document about X"
                # (a valid create_file/filesystem step) collapsed to unknown/
                # unknown and every non-trivial task failed. Only fall back to a
                # fresh parse when no step is available.
                if complex_command.steps:
                    step = complex_command.steps[0]
                    parsed_command = {
                        "action": step.action,
                        "category": step.category,
                        "params": step.params or {},
                    }
                else:
                    parsed_command = self.command_parser.parse(command)

                # Check permissions
                if not self.permission_manager.check_permission(parsed_command):
                    raise PermissionError(f"Permission denied for command: {command}")

                # Execute the command
                result = self._execute_parsed_command(parsed_command, **kwargs)

                # Log execution
                self._log_execution(
                    command, parsed_command, result,
                    success=True, duration=time.monotonic() - start,
                )

                return {
                    "success": True,
                    "result": result,
                    "command": command,
                    "complexity": "simple",
                    "route": (
                        f"{parsed_command.get('category', 'unknown')}."
                        f"{parsed_command.get('action', 'unknown')}"
                    ),
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                # Execute complex workflow
                self.logger.info(
                    f"Executing complex workflow with {len(complex_command.steps)} steps"
                )

                # Check permissions for all steps
                for step in complex_command.steps:
                    step_command = {
                        "action": step.action,
                        "category": step.category,
                        "params": step.params,
                    }
                    if not self.permission_manager.check_permission(step_command):
                        raise PermissionError(f"Permission denied for step: {step.action}")

                # Execute workflow
                workflow_result = self.workflow_engine.execute_workflow(complex_command)

                # Log execution
                self._log_execution(
                    command, complex_command, workflow_result,
                    success=workflow_result["success"], duration=time.monotonic() - start,
                )

                return {
                    "success": workflow_result["success"],
                    "result": workflow_result,
                    "command": command,
                    "complexity": complex_command.complexity.value,
                    "route": " → ".join(
                        f"{s.category}.{s.action}" for s in complex_command.steps[:6]
                    ) or "workflow",
                    "steps_completed": workflow_result.get("completed_steps", 0),
                    "total_steps": workflow_result.get("total_steps", 0),
                    "execution_time": workflow_result.get("total_execution_time", 0),
                    "timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Error executing command '{command}': {error_msg}")

            # Record the failure in the audit trail too, so history reflects it.
            self._log_execution(
                command, {"error": error_msg}, {"error": error_msg},
                success=False, duration=time.monotonic() - start,
            )

            # Provide helpful fallback messages for specific errors
            fallback_msg = self._get_fallback_error_message(command, error_msg, type(e).__name__)

            # Get AI suggestions for error resolution if available
            error_suggestions = []
            if self.ai_parser.get_ai_status()["available"]:
                try:
                    error_info = {
                        "command": command,
                        "error": error_msg,
                        "error_type": type(e).__name__,
                        "context": self._get_execution_context(),
                    }
                    ai_resolution = self.ai_parser.handle_execution_error(error_info)
                    error_suggestions = ai_resolution.get("suggestions", [])
                except Exception as ai_error:
                    self.logger.warning(f"AI error resolution failed: {ai_error}")

            return {
                "success": False,
                "error": error_msg,
                "fallback_message": fallback_msg,
                "command": command,
                "ai_suggestions": error_suggestions,
                "timestamp": datetime.now().isoformat(),
            }

    def _execute_parsed_command(self, parsed_command: dict[str, Any], **kwargs) -> Any:
        """Execute a parsed command using appropriate adapter/plugin"""
        action = parsed_command.get("action")
        category = parsed_command.get("category")
        params = parsed_command.get("params", {})
        # An unrecognised command parses to unknown/unknown. Fail with a clear,
        # honest message instead of trying to dispatch a plugin literally named
        # "unknown" (which produced the misleading "Plugin 'unknown' not found").
        if not action or action == "unknown" or category == "unknown":
            raise ValueError(
                f"Could not interpret '{parsed_command.get('params', {}).get('raw_command', action)}' "
                "as a known action. Rephrase it, or ask a question (starting with what/how/why) "
                "to get a conversational answer instead."
            )
        # Prefer a capability that advertises this action (registry is the router)
        try:
            candidates = self.capability_registry.route(action)
            if candidates:
                preferred = next(
                    (c for c in candidates if c in self.capability_registry), candidates[0]
                )
                params_with_ctx = self._normalize_screenshot_params(dict(params or {}))
                return self.capability_registry.dispatch(preferred, action, params_with_ctx)
        except Exception:
            # If capability dispatch fails, fall back to adapters
            pass

        # Route to appropriate handler
        if category == "filesystem":
            # Read an existing document, expand it with the AI, and write it back.
            if action in ("enhance_file", "enhance_document", "expand_file", "expand_document"):
                return self._handle_enhance_file(params)
            # The AI parser emits file-content writes as create_file/write_file
            # with a `path` + `content`, but the OS filesystem adapters only
            # understand create_file(name, location). Bridge that contract here
            # so "create a document about X" actually writes the file instead of
            # silently returning False.
            file_write_actions = {
                "write_file", "create_text_file", "save_file",
                "write_to_file", "save_to_document",
            }
            wants_content = "content" in (params or {})
            has_path = bool((params or {}).get("path") or (params or {}).get("file_path"))
            if action in file_write_actions or (
                action == "create_file" and (wants_content or has_path) and not params.get("name")
            ):
                return self._handle_write_file(params)
            return self.os_adapter.filesystem.execute(action, params)
        elif category == "process":
            return self.os_adapter.process.execute(action, params)
        elif category == "gui":
            # Prefer web_automation plugin when it supports the requested GUI/browser alias
            try:
                if hasattr(self, "plugin_manager") and "web_automation" in getattr(
                    self.plugin_manager, "plugins", {}
                ):
                    plugin = self.plugin_manager.plugins["web_automation"]
                    try:
                        caps = plugin.get_capabilities()
                    except Exception:
                        caps = []

                    if action in caps:
                        params_with_ctx = dict(params or {})
                        params_with_ctx = self._normalize_screenshot_params(params_with_ctx)
                        return self.capability_registry.dispatch(
                            "web_automation", action, params_with_ctx
                        )
            except Exception:
                # Fall back to OS GUI adapter on any plugin error
                pass

            return self.os_adapter.gui.execute(action, params)
        elif category == "system":
            return self.os_adapter.system.execute(action, params)
        elif category == "network":
            return self.os_adapter.network.execute(action, params)
        elif category == "code_modification":
            # Handle code modification actions
            if action == "modify_file":
                return self._handle_modify_file(params)
            elif action == "read_file":
                return self._handle_read_file(params)
            elif action == "write_file":
                return self._handle_write_file(params)
        else:
            # Prefer plugin registered under the category name if present
            if category in self.capability_registry:
                try:
                    params_with_ctx = dict(params or {})
                    return self.capability_registry.dispatch(category, action, params_with_ctx)
                except Exception as e:
                    self.logger.warning(f"Plugin '{category}' failed: {e}")

            # Capability-based dispatch: find a capability that advertises the action
            try:
                candidates = self.capability_registry.route(action)
                if candidates:
                    preferred = next(
                        (c for c in candidates if c in self.capability_registry), candidates[0]
                    )
                    self.logger.info(
                        f"Dispatching action '{action}' to plugin '{preferred}' by capability"
                    )
                    params_with_ctx = self._normalize_screenshot_params(dict(params or {}))
                    return self.capability_registry.dispatch(preferred, action, params_with_ctx)
            except Exception as e:
                self.logger.debug(f"Capability-based plugin dispatch failed: {e}")

            # Final fallback: attempt plugin by category name (legacy behavior)
            params_with_ctx = dict(params or {})
            params_with_ctx = self._normalize_screenshot_params(params_with_ctx)
            # If category is an alias for a real plugin name, use it
            plugin_name = category
            if hasattr(self, "plugin_aliases") and category in self.plugin_aliases:
                plugin_name = self.plugin_aliases[category]
            return self.capability_registry.dispatch(plugin_name, action, params_with_ctx)

    def _log_execution(
        self,
        original_command: str,
        parsed_command: dict[str, Any],
        result: Any,
        success: bool = True,
        duration: float | None = None,
    ):
        """Log command execution for audit trail"""
        execution_record = {
            "timestamp": datetime.now().isoformat(),
            "original_command": original_command,
            "parsed_command": parsed_command,
            "result_summary": str(result)[:200] if result else None,
            "success": success,
            "duration": duration,
            "user": os.getenv("USERNAME", "unknown"),
            "platform": platform.system(),
        }

        self.execution_history.append(execution_record)

        # Keep only last 1000 executions in memory
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]

    def batch_execute(self, commands: list[str]) -> list[dict[str, Any]]:
        """Execute multiple commands in sequence"""
        results = []
        for command in commands:
            result = self.execute(command)
            results.append(result)

            # Stop on first failure unless configured otherwise
            if not result["success"] and not self.config.get("continue_on_error", False):
                break

        return results

    def get_capabilities(self) -> dict[str, list[str]]:
        """Get list of all available capabilities"""
        capabilities = {
            "filesystem": self.os_adapter.filesystem.get_capabilities(),
            "process": self.os_adapter.process.get_capabilities(),
            "gui": self.os_adapter.gui.get_capabilities(),
            "system": self.os_adapter.system.get_capabilities(),
            "network": self.os_adapter.network.get_capabilities(),
            "plugins": self.plugin_manager.get_available_plugins(),
        }

        return capabilities

    def describe_capabilities(self) -> dict[str, dict[str, Any]]:
        """Return capability metadata (name -> actions/risk) from the registry.

        Additive discovery surface backed by :class:`CapabilityRegistry`; does
        not affect command dispatch.
        """
        return self.capability_registry.describe()

    def get_execution_history(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent execution history"""
        return self.execution_history[-limit:]

    def get_workflow_status(self) -> dict[str, Any]:
        """Get current workflow execution status"""
        return self.workflow_engine.get_workflow_status()

    def analyze_command_complexity(self, command: str) -> dict[str, Any]:
        """Analyze command complexity without executing"""
        complex_command = self.advanced_parser.parse_complex_command(command)

        return {
            "original_command": command,
            "complexity": complex_command.complexity.value,
            "estimated_steps": len(complex_command.steps),
            "estimated_duration": complex_command.estimated_duration,
            "context": complex_command.context,
            "steps_preview": [
                {"action": step.action, "category": step.category, "priority": step.priority}
                for step in complex_command.steps
            ],
        }

    def _get_execution_context(self) -> dict[str, Any]:
        """Get current execution context for AI analysis"""
        return {
            "platform": platform.system(),
            "recent_commands": [
                record["original_command"] for record in self.execution_history[-5:]
            ],
            "available_capabilities": list(self.get_capabilities().keys()),
            "current_directory": os.getcwd(),
            "user": os.getenv("USERNAME", "unknown"),
        }

    def get_ai_suggestions(self) -> list[str]:
        """Get AI-powered smart suggestions"""
        if self.ai_parser.get_ai_status()["available"]:
            return self.ai_parser.get_smart_suggestions(self._get_execution_context())
        else:
            return [
                "Start the local Ollama server for AI-powered suggestions",
                "Try 'examples' for command ideas",
                "Use 'help' to see available commands",
            ]

    def analyze_command_with_ai(self, command: str) -> dict[str, Any]:
        """Analyze command using AI without executing"""
        if self.ai_parser.get_ai_status()["available"]:
            return self.ai_parser.analyze_command_intent(command)
        else:
            return {
                "intent": "AI analysis not available",
                "confidence": 0.0,
                "suggestions": ["Start the local Ollama server to enable AI analysis"],
                "complexity": "unknown",
            }

    # Leading tokens that mark a message as conversational rather than an
    # automation command. Questions and greetings get an AI answer; everything
    # else is treated as an action to execute (this tool is automation-first).
    _CONVERSATIONAL_STARTS = frozenset({
        "what", "what's", "whats", "why", "how", "who", "when", "where", "which",
        "can", "could", "would", "should", "do", "does", "did", "is", "are", "am",
        "tell", "explain", "describe", "help", "hi", "hello", "hey", "thanks",
        "thank", "may",
    })

    def _is_conversational(self, message: str) -> bool:
        """Heuristic: does the user want an answer rather than an action?

        ponytail: keyword heuristic, not intent classification. Ceiling —
        declarative non-questions ("the build failed") fall through to
        execution. Upgrade path: ask the AI to classify when it's loaded.
        """
        text = message.strip().lower()
        if not text:
            return False
        if text.endswith("?"):
            return True
        first = text.split()[0].rstrip(",.:")
        return first in self._CONVERSATIONAL_STARTS

    def chat(self, message: str, history: list[dict[str, str]] | None = None) -> dict[str, Any]:
        """Seamless entry point for chat surfaces (chatbot, GUI, TUI).

        Routes a message to either a conversational AI reply or real command
        execution, so the same input box handles "what can you build?" and
        "create a python project called scraper" without the caller guessing.

        Returns a dict with a ``kind`` of ``"conversation"`` or ``"automation"``.
        Conversation results carry a ``reply`` string; automation results carry
        the full :meth:`execute` payload.
        """
        if not message or not message.strip():
            return {"kind": "conversation", "success": False, "reply": "Say something first."}

        if self._is_conversational(message):
            ai = getattr(self.ai_parser, "ai", None)
            if ai is not None and ai.is_available:
                reply = ai.converse(message, history)
            else:
                reply = (
                    "AI is not available — start the local Ollama server "
                    "('ollama serve') and pull the model. I can still run "
                    "automation commands like 'create a python project called "
                    "scraper' or 'take a screenshot'."
                )
            return {"kind": "conversation", "success": True, "reply": reply}

        result = self.execute(message)
        result["kind"] = "automation"
        return result

    # ── n8n workflow automation ─────────────────────────────────────────────

    @property
    def n8n(self) -> Any:
        """Lazily-built n8n gateway (GUI/TUI-friendly, dict-returning).

        Built from configured n8n settings (``N8N_URL`` / ``N8N_API_KEY`` or the
        settings file). The gateway is always available; a missing/unreachable
        n8n server surfaces as an error when its methods are awaited, which the
        UI renders as a connection hint rather than a crash.
        """
        gw = getattr(self, "_n8n_gateway", None)
        if gw is None:
            from ..plugins.n8n_bridge.gateway import N8nGateway

            url = os.getenv("N8N_URL", "")
            key = os.getenv("N8N_API_KEY", "")
            if not url or not key:
                # Fall back to the settings file if env vars are unset.
                try:
                    from ..config import get_settings

                    s = get_settings()
                    url = url or s.n8n.url
                    key = key or s.n8n.api_key
                except Exception:
                    url = url or "http://localhost:5678"
            gw = N8nGateway(url=url or "http://localhost:5678", api_key=key)
            self._n8n_gateway = gw
        return gw

    # ── Custom distro building ──────────────────────────────────────────────

    def _maybe_build_distro(self, command: str) -> dict[str, Any] | None:
        """Route a natural-language OS/distro build request to the real pipeline.

        Returns a structured result dict when ``command`` is a distro-build
        request, or ``None`` when it is not (so normal parsing continues).

        The build itself needs root and is long-running; the pipeline preflights
        the root check and returns an honest "needs root" result rather than
        raising, which we surface unchanged.
        """
        try:
            from ..nlp.semantic_engine import IntentType, get_semantic_nlp

            analysis = get_semantic_nlp().analyze(command)
            if analysis.intent is not IntentType.BUILD_DISTRO:
                return None
        except Exception as exc:
            self.logger.debug(f"distro intent check skipped: {exc}")
            return None

        self.logger.info(f"Routing to OS builder (build_distro): {command}")

        # Preflight: the pipeline (pacstrap/debootstrap, kernel compile, xorriso)
        # needs root and is long-running + network/disk heavy. If we're not root,
        # try to escalate through the privilege input layer — prompt once for the
        # sudo password, validate it, and run the whole build inside that session
        # so each privileged sub-command goes through `sudo -S`. If escalation is
        # impossible or declined, fail fast with an honest message instead of
        # grinding for minutes before hitting a privilege error mid-build.
        from ..security.privilege import PrivilegeError, get_escalator

        escalator = get_escalator()
        try:
            with escalator.session("distro build"):
                return self._run_distro_build(command)
        except PrivilegeError as exc:
            return {"success": False, "message": str(exc), "iso_path": None}

    # "output directory /data", "output dir ~/isos", "output to ./build", or a
    # trailing "... in /data" — capture the path token that follows.
    _OUTPUT_DIR_RE = re.compile(
        r"\boutput\s+(?:directory|dir|folder|to|into|at)?\s*"
        r"(?P<path>~?/[^\s,;]+|\./[^\s,;]+)",
        re.IGNORECASE,
    )

    def _extract_output_dir(self, command: str) -> str | None:
        """Pull an output directory path out of a natural-language build request.

        Returns the path string when the user named one, else ``None`` so the
        caller falls back to configured defaults. Only absolute (``/``, ``~/``)
        or explicit relative (``./``) paths are honored to avoid grabbing stray
        words like "output the iso".
        """
        match = self._OUTPUT_DIR_RE.search(command)
        return match.group("path") if match else None

    def _run_distro_build(self, command: str) -> dict[str, Any]:
        """Run the real OS-build pipeline (root or an active sudo session)."""
        try:
            import asyncio
            from pathlib import Path

            from ..distro_builder.build_pipeline import build_from_nl

            # Honor an output directory named in the request (e.g. "output
            # directory /data for the iso"); otherwise fall back to config.
            output_dir = self._extract_output_dir(command)
            if output_dir is None:
                try:
                    from ..config import get_settings

                    output_dir = get_settings().distro_builder.output_dir
                except Exception:
                    output_dir = "./distro_output"

            out = Path(output_dir).expanduser().resolve()
            result = asyncio.run(build_from_nl(command, out))
            success = bool(getattr(result, "success", False))
            iso_path = getattr(result, "iso_path", None)
            error_message = getattr(result, "error_message", None)
            log_path = getattr(result, "log_path", None)
            if success:
                message = f"ISO built: {iso_path}"
            else:
                # A failed build must never read like a success ("ISO built:
                # None"). Surface the real reason, or point at the log.
                message = error_message or f"Distro build failed. See log: {log_path}"
            return {
                "success": success,
                "message": message,
                "iso_path": iso_path,
                "log_path": log_path,
                "build_time_seconds": getattr(result, "build_time_seconds", None),
            }
        except PermissionError as exc:
            # Root preflight can surface as PermissionError depending on stage.
            return {"success": False, "message": str(exc), "iso_path": None}
        except Exception as exc:
            self.logger.error(f"OS builder failed: {exc}")
            return {"success": False, "message": f"Build error: {exc}", "iso_path": None}

    # Intent phrases that mean "expand/enrich an existing document" rather than
    # "create a new one". Broad modification verbs (append/update/rewrite) are
    # safe here only because routing *also* requires the named path to resolve
    # to an EXISTING document (see _resolve_document_path); a "create a file"
    # request names a file that does not exist yet, so it never routes here.
    _ENHANCE_HINTS = (
        "add more information",
        "add more info",
        "add more detail",
        "add more content",
        "add information",
        "add detail",
        "add content",
        "add a section",
        "add sections",
        "additional section",
        "more detailed",
        "more detail to",
        "make it more detailed",
        "make it detailed",
        "make it longer",
        "expand on",
        "expand the",
        "expand this",
        "extend the",
        "extend this",
        "elaborate on",
        "elaborate the",
        "flesh out",
        "enrich the",
        "enhance the",
        "improve the detail",
        "add to the existing",
        "update the",
        "revise the",
        "rewrite the",
        "append",
    )

    # File token: an absolute/relative path or a bare name ending in a document
    # extension. Used to pull the target out of a free-form enhance request.
    _PATH_TOKEN_RE = re.compile(r"(?:(?:~|\.{0,2})/[^\s'\"]+|[^\s'\"/]+\.[A-Za-z0-9]{1,6})")

    def _maybe_enhance_document(self, command: str) -> dict[str, Any] | None:
        """Route an "expand this existing file" request to a single enhance step.

        Returns a result dict when ``command`` clearly asks to enrich an existing
        document (an enhance phrase *and* a token that resolves to a real file),
        or ``None`` so normal parsing continues. Requiring the path to exist keeps
        this from hijacking ordinary "create a file" requests, which name files
        that do not exist yet.
        """
        lowered = command.lower()
        if not any(hint in lowered for hint in self._ENHANCE_HINTS):
            return None

        target: str | None = None
        for token in self._PATH_TOKEN_RE.findall(command):
            resolved = self._resolve_document_path(token)
            if resolved is not None:
                target = resolved
                break
        if target is None:
            return None

        self.logger.info(f"Routing to document enhancer (enhance_file): {target}")
        return self._handle_enhance_file({"file_path": target, "instruction": command})

    # Text-like extensions the enhancer is willing to read and rewrite.
    _ENHANCE_EXTENSIONS = (".md", ".markdown", ".txt", ".rst", ".text")

    def _resolve_document_path(self, path: str) -> str | None:
        """Resolve a user token to a concrete document file, or ``None``.

        Accepts a direct file path, or a directory that contains exactly one
        document file (the common "the markdown file at /data/test" case where
        the user names the folder). Ambiguous or non-document targets return
        ``None`` so the caller can fall back to normal parsing.
        """
        candidate = os.path.expanduser(path)
        if os.path.isfile(candidate):
            return candidate
        if os.path.isdir(candidate):
            docs = [
                os.path.join(candidate, f)
                for f in sorted(os.listdir(candidate))
                if f.lower().endswith(self._ENHANCE_EXTENSIONS)
                and os.path.isfile(os.path.join(candidate, f))
            ]
            if len(docs) == 1:
                return docs[0]
        return None

    def _handle_enhance_file(self, params: dict[str, Any]) -> dict[str, Any]:
        """Read a document, expand it with the AI, and write the result back.

        One self-contained step: it never relies on cross-step placeholder
        handoff (which the workflow engine does not perform). Fails honestly
        rather than overwriting the file with empty or partial content.
        """
        raw_path = params.get("file_path") or params.get("path")
        instruction = (
            params.get("instruction")
            or params.get("request")
            or params.get("content")
            or "Add more information and make it more detailed."
        )
        if not raw_path:
            return {"success": False, "error": "file_path parameter required"}

        file_path = self._resolve_document_path(raw_path)
        if file_path is None:
            return {
                "success": False,
                "error": (
                    f"No single document found at '{raw_path}'. Point me at a "
                    "specific text/markdown file to expand."
                ),
            }

        read = self._handle_read_file({"file_path": file_path})
        if not read.get("success"):
            return read
        original = read.get("content", "")

        ai = getattr(self.ai_parser, "ai", None)
        if ai is None or not getattr(ai, "is_available", False):
            return {
                "success": False,
                "error": "AI backend unavailable — cannot enhance the document.",
                "file_path": file_path,
            }

        enhanced = ai.enhance_document(
            original, instruction, filename=os.path.basename(file_path)
        )
        if not enhanced or not enhanced.strip():
            return {
                "success": False,
                "error": "The AI returned no content; the file was left unchanged.",
                "file_path": file_path,
            }

        result = self._handle_write_file({"file_path": file_path, "content": enhanced})
        if result.get("success"):
            result["message"] = (
                f"Expanded {file_path}: {read.get('size', len(original))} → "
                f"{len(enhanced)} chars."
            )
        return result

    _DISTRO_BASE_MAP = {
        "arch linux": "arch",
        "arch": "arch",
        "debian": "debian",
        "ubuntu": "debian",
        "alpine": "unix",
        "fedora": "debian",
    }

    def _gui_config_to_profile(self, config: dict[str, Any]) -> Any:
        """Map the GUI distro-wizard config into a :class:`DistroProfile`."""
        from ..distro_builder.models import DistroProfile

        base = self._DISTRO_BASE_MAP.get(str(config.get("base", "")).lower(), "debian")

        # App bundles arrive as strings that may pack several packages ("nmap wireshark").
        packages: list[str] = []
        for entry in config.get("apps", []) or []:
            packages.extend(str(entry).split())
        if config.get("hardening"):
            packages.extend(["nftables", "apparmor", "auditd"])

        return DistroProfile(
            name=f"archon-{config.get('distro_type', 'custom')}".lower(),
            base=base,
            packages=packages,
            hostname=str(config.get("hostname") or "archon"),
        )

    async def build_distro(self, config: dict[str, Any]) -> dict[str, Any]:
        """Build a custom Linux ISO from the GUI wizard config.

        Runs the real :func:`archon.distro_builder.build_pipeline.build_distro`
        pipeline. This is a privileged, long-running operation (needs root and
        significant disk); we preflight the root check and return a structured
        result dict instead of raising so UI surfaces can render it cleanly.

        Returns:
            ``{"success": bool, "message": str, "iso_path": str|None,
               "log_path": str, "build_time_seconds": float}``.
        """
        from pathlib import Path

        # Preflight: the pipeline (pacstrap/debootstrap, xorriso, kernel build)
        # cannot work without root. Fail fast with a clear, honest message.
        try:
            from ..security.path_validator import PathValidator

            PathValidator.check_root_required("distro build")
        except PermissionError as exc:
            return {"success": False, "message": str(exc), "iso_path": None}
        except Exception:
            pass  # Non-fatal on platforms without the check.

        try:
            from ..config import get_settings

            settings = get_settings()
            work_dir = settings.distro_builder.work_dir
            jobs = settings.distro_builder.default_jobs or (os.cpu_count() or 4)
            output_dir = settings.distro_builder.output_dir
        except Exception:
            work_dir = "/tmp/archon_distro_build"
            output_dir = "./distro_output"
            jobs = os.cpu_count() or 4

        try:
            from ..distro_builder.build_pipeline import build_distro as _build

            profile = self._gui_config_to_profile(config)
            out = Path(output_dir).expanduser().resolve()
            out.mkdir(parents=True, exist_ok=True)
            Path(work_dir).expanduser().mkdir(parents=True, exist_ok=True)

            result = await _build(profile, out, jobs=jobs)
            if result.success:
                return {
                    "success": True,
                    "message": f"ISO built: {result.iso_path}",
                    "iso_path": result.iso_path,
                    "log_path": result.log_path,
                    "build_time_seconds": result.build_time_seconds,
                }
            return {
                "success": False,
                "message": "Build failed — see build log for details.",
                "iso_path": None,
                "log_path": result.log_path,
            }
        except Exception as exc:
            self.logger.error(f"build_distro failed: {exc}")
            return {"success": False, "message": f"Build error: {exc}", "iso_path": None}

    def get_ai_status(self) -> dict[str, Any]:
        """Get AI integration status"""
        return self.ai_parser.get_ai_status()

    def switch_ai_model(self, model_name: str) -> bool:
        """Switch the active local Ollama model by name."""
        try:
            if self.ai_parser.set_model(model_name):
                self.logger.info(f"Switched AI model to: {model_name}")
                return True
            self.logger.warning(f"Failed to switch AI model: {model_name}")
            return False
        except Exception as e:
            self.logger.error(f"switch_ai_model failed: {e}")
            return False

    def enable_sandbox_mode(self):
        """Sandbox mode support removed - no-op"""
        self.logger.warning(
            "Sandbox mode support has been removed; enable_sandbox_mode() is a no-op"
        )

    def disable_sandbox_mode(self):
        """Sandbox mode support removed - no-op"""
        self.logger.warning(
            "Sandbox mode support has been removed; disable_sandbox_mode() is a no-op"
        )

    def shutdown(self):
        """Clean shutdown of the automation engine"""
        self.logger.info("Shutting down Archon")
        self.is_running = False
        self.plugin_manager.shutdown()
        self.os_adapter.cleanup()

    def _get_fallback_error_message(self, command: str, error: str, error_type: str) -> str:
        """Generate helpful fallback error message based on error type"""
        import re

        # Check for common error patterns
        if "unknown" in error.lower() and "action" in error.lower():
            return (
                "⚠️ Command complexity too high: The command contains multiple nested levels that "
                "exceed current parsing capabilities.\n"
                "Suggestion: Break the command into simpler steps or use fewer nesting levels.\n"
                "Example: Instead of 3+ nested 'in each' statements, use 2 levels maximum."
            )

        # Check for multi-level nesting in command
        nested_count = len(re.findall(r"in\s+(?:each|every)", command, re.IGNORECASE))
        if nested_count >= 3:
            return (
                f"⚠️ Command has {nested_count} nesting levels: The parser supports up to 2-3 levels of nesting.\n"
                "Your command structure:\n"
                "  • Level 1: in that / and in that\n"
                "  • Level 2: in each [type] make/create\n"
                "  • Level 3: in each of the [plural]\n"
                "Suggestion: Simplify by removing one or more nesting levels or running multiple commands."
            )

        # Check for unsupported patterns
        if "registry" in command.lower() or "index" in command.lower():
            if error_type == "NotImplementedError":
                return "⚠️ Registry/Index generation: This feature requires additional setup.\nTry using a simpler command."

        # Generic helpful message
        return (
            "⚠️ Command parsing failed: The command structure may not be fully supported.\n"
            "Supported patterns:\n"
            "  • Simple creation: 'create X folder'\n"
            "  • Single nesting: 'make A B C folders and in each make D E F folders'\n"
            "  • Double nesting: Add 'and in each of the [plural] create [items]'\n"
            "Please verify your command syntax or try a simpler approach."
        )

    def _resolve_file_with_disambiguation(self, file_name: str) -> str | None:
        """Resolve a file name to its full path (shared implementation)."""
        return resolve_file_with_disambiguation(file_name)

    def _handle_read_file(self, params: dict[str, Any]) -> dict[str, Any]:
        """Read file contents"""
        try:
            file_path = params.get("file_path") or params.get("path")
            if not file_path:
                raise ValueError("file_path parameter required")

            # Resolve relative paths from Desktop with duplicate detection
            if not os.path.isabs(file_path):
                resolved_path = self._resolve_file_with_disambiguation(file_path)
                if not resolved_path:
                    return {"success": False, "error": f"File not found: {file_path}"}
                file_path = resolved_path
            elif not os.path.exists(file_path):
                # Check if there are duplicate files
                file_name = os.path.basename(file_path)
                resolved_path = self._resolve_file_with_disambiguation(file_name)
                if resolved_path:
                    file_path = resolved_path
                else:
                    return {"success": False, "error": f"File not found: {file_path}"}

            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            return {
                "success": True,
                "file_path": file_path,
                "content": content,
                "size": len(content),
                "lines": len(content.split("\n")),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "file_path": params.get("file_path")}

    def _handle_write_file(self, params: dict[str, Any]) -> dict[str, Any]:
        """Write content to file"""
        try:
            file_path = params.get("file_path") or params.get("path")
            content = params.get("content", "")

            if not file_path:
                raise ValueError("file_path parameter required")

            # Honest failure over silent empty file: this is the content-write
            # path (scrape/generate → save). If the upstream step produced
            # nothing, report a real error instead of a 0-byte file that looks
            # like success. Unresolved handoff placeholders count as no content.
            stripped = content.strip() if isinstance(content, str) else content
            placeholder = isinstance(content, str) and content.strip() in (
                "{{extracted_content}}",
                "{{content}}",
            )
            if not stripped or placeholder:
                return {
                    "success": False,
                    "error": (
                        "No content to write — the upstream step produced no "
                        "data, so the file was not created. (Refusing to write "
                        "an empty file and report success.)"
                    ),
                    "file_path": file_path,
                }

            # Resolve relative paths from Desktop with duplicate detection
            if not os.path.isabs(file_path):
                resolved_path = self._resolve_file_with_disambiguation(file_path)
                if not resolved_path:
                    # If not found, default to CWD
                    file_path = os.path.join(os.getcwd(), file_path)
                else:
                    file_path = resolved_path
            elif not os.path.exists(file_path):
                # Check if there are duplicate files
                file_name = os.path.basename(file_path)
                resolved_path = self._resolve_file_with_disambiguation(file_name)
                if resolved_path:
                    file_path = resolved_path

            # Create directories if needed
            os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "success": True,
                "file_path": file_path,
                "size": len(content),
                "lines": len(content.split("\n")),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "file_path": params.get("file_path")}

    def _handle_modify_file(self, params: dict[str, Any]) -> dict[str, Any]:
        """Modify file by replacing old implementation with new one"""
        try:
            file_path = params.get("file_path") or params.get("path")
            old_code = params.get("old_code")
            new_code = params.get("new_code")
            intent = params.get("intent", "")

            if not file_path:
                raise ValueError("file_path parameter required")

            # Resolve relative paths from Desktop with duplicate detection
            if not os.path.isabs(file_path):
                resolved_path = self._resolve_file_with_disambiguation(file_path)
                if not resolved_path:
                    return {
                        "success": False,
                        "error": f"File not found: {file_path}",
                        "file_path": file_path,
                    }
                file_path = resolved_path
            elif not os.path.exists(file_path):
                # Check if there are duplicate files
                file_name = os.path.basename(file_path)
                resolved_path = self._resolve_file_with_disambiguation(file_name)
                if resolved_path:
                    file_path = resolved_path
                else:
                    return {
                        "success": False,
                        "error": f"File not found: {file_path}",
                        "file_path": file_path,
                    }

            # Read the file
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            # If specific old/new code provided, do direct replacement
            if old_code and new_code:
                if old_code not in content:
                    raise ValueError(f"Could not find code to replace in {file_path}")
                modified_content = content.replace(old_code, new_code)
            else:
                # Auto-generate replacement based on intent
                modified_content = self._generate_code_replacement(content, intent)

            # Write back
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(modified_content)

            return {"success": True, "file_path": file_path, "action": "modified", "intent": intent}
        except Exception as e:
            return {"success": False, "error": str(e), "file_path": params.get("file_path")}

    def _generate_code_replacement(self, current_content: str, intent: str) -> str:
        """Generate code replacement based on intent"""
        intent_lower = intent.lower()

        # Prime number detection
        if "prime" in intent_lower and "fibonacci" in current_content.lower():
            return self._generate_prime_number_code()

        # Fibonacci from other code
        if "fibonacci" in intent_lower:
            return self._generate_fibonacci_code()

        # Default: return unchanged
        return current_content

    def _generate_prime_number_code(self) -> str:
        """Generate prime number identifier code (shared implementation)."""
        return generate_prime_number_code()

    def _generate_fibonacci_code(self) -> str:
        """Generate fibonacci series code (shared implementation)."""
        return generate_fibonacci_code()
