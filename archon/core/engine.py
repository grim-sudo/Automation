"""
Core automation engine that orchestrates all automation operations
"""

import os
import platform
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

            # Initialize AI parser with fallback
            api_key = None
            if config:
                api_key = config.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY")
            else:
                api_key = os.getenv("OPENROUTER_API_KEY")

            self.ai_parser = AIEnhancedParser(api_key)
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
                # Use simple parsing for basic commands
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
                "Set OPENROUTER_API_KEY environment variable for AI-powered suggestions",
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
                "suggestions": ["Enable AI by setting OPENROUTER_API_KEY environment variable"],
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
            ai = getattr(self.ai_parser, "openrouter_ai", None)
            if ai is not None and ai.is_available:
                reply = ai.converse(message, history)
            else:
                reply = (
                    "AI is not configured, so I can't chat freely yet — set "
                    "OPENROUTER_API_KEY in your .env. I can still run automation "
                    "commands like 'create a python project called scraper' or "
                    "'take a screenshot'."
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

    def set_openrouter_api_key(self, api_key: str) -> bool:
        """Set OpenRouter API key for AI features"""
        success = self.ai_parser.set_api_key(api_key)
        if success:
            self.logger.info("OpenRouter AI enabled successfully")
        else:
            self.logger.error("Failed to enable OpenRouter AI")
        return success

    def switch_ai_model(self, model_name: str) -> bool:
        """Switch the active AI model by name."""
        try:
            ai_manager = getattr(self, "ai_manager", None)
            if ai_manager is None:
                from ..ai.model_manager import get_ai_manager

                ai_manager = get_ai_manager()
                self.ai_manager = ai_manager
            if ai_manager.switch_model(model_name):
                self.logger.info(f"Switched AI model to: {model_name}")
                return True
            self.logger.warning(f"AI model not found: {model_name}")
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
