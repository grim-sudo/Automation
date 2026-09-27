"""
AI-Enhanced command parser using the local Ollama model for intelligent interpretation
"""

import re
from typing import Any

from ..ai.automation_ai import AITaskPlan, OllamaAutomationAI
from ..utils.logger import get_logger
from .command_parser import AdvancedCommandParser, CommandComplexity, ComplexCommand, ParsedStep


class AIEnhancedParser:
    """Command parser enhanced with local Ollama AI for natural language understanding"""

    def __init__(self, model: str | None = None):
        self.logger = get_logger("AIEnhancedParser")
        self.fallback_parser = AdvancedCommandParser()
        self.ai = OllamaAutomationAI(model)

        # Learning and adaptation
        self.user_patterns = {}
        self.command_history = []

    def parse_with_ai(self, command: str, context: dict[str, Any] = None) -> ComplexCommand:
        """Parse command using AI enhancement"""

        # Add to command history for learning
        self.command_history.append(command)
        if len(self.command_history) > 50:  # Keep last 50 commands
            self.command_history = self.command_history[-50:]

        if self.ai.is_ready():
            return self._parse_with_ai(command, context)
        else:
            self.logger.info("Ollama AI not available, using fallback parser")
            return self.fallback_parser.parse_complex_command(command)

    def _parse_with_ai(
        self, command: str, context: dict[str, Any] = None
    ) -> ComplexCommand:
        """Parse command using the local Ollama AI"""

        try:
            # For very long commands, check if AI can handle it
            # If command is very long and complex, use fallback parser directly
            if (
                len(command) > 200
                and self._is_complex_structure(command)
                and not self._looks_like_document_request(command)
            ):
                self.logger.info(
                    "Complex command detected, using fallback parser for better accuracy"
                )
                return self.fallback_parser.parse_complex_command(command)

            # Enhance command understanding with AI
            enhancement = self.ai.enhance_command_understanding(
                command,
                self.command_history[-5:],  # Recent history for context
            )

            enhanced_command = enhancement.get("enhanced_command", command)
            self.logger.info(f"AI enhanced command: {enhanced_command}")

            # Get AI task plan
            ai_plan = self.ai.analyze_automation_request(enhanced_command, context)

            # The model intermittently returns an empty plan (timeout / a
            # malformed JSON body it couldn't parse). One retry recovers most of
            # these; without it a multi-step request silently collapses to the
            # naive fallback, which only catches the first clause (e.g. it made
            # just the "bread" folder and dropped the 15 nested folders + files).
            if not ai_plan.execution_steps:
                self.logger.warning("AI returned empty steps, retrying once")
                ai_plan = self.ai.analyze_automation_request(enhanced_command, context)

            # Check if AI plan has valid steps
            if not ai_plan.execution_steps or len(ai_plan.execution_steps) == 0:
                self.logger.warning("AI returned empty steps, using fallback parser")
                return self.fallback_parser.parse_complex_command(command)

            # Validate AI steps have required fields
            valid_steps = []
            for step in ai_plan.execution_steps:
                if isinstance(step, dict) and step.get("action") and step.get("category"):
                    valid_steps.append(step)
                else:
                    self.logger.warning(f"Invalid AI step: {step}")

            if not valid_steps:
                self.logger.warning("No valid AI steps found, using fallback parser")
                return self.fallback_parser.parse_complex_command(command)

            # Update AI plan with valid steps
            ai_plan.execution_steps = valid_steps

            # Convert AI plan to ComplexCommand format
            complex_command = self._convert_ai_plan_to_complex_command(ai_plan)

            # The model plans a create_file step but rarely inlines a full
            # document body into a JSON param, so "write documentation about X"
            # produced an empty file. Generate the prose for document-type files
            # from the original request before the write handlers run.
            self._fill_document_content(complex_command, command)

            # Optimize workflow if it's complex
            if len(complex_command.steps) > 2:
                try:
                    optimization = self.ai.optimize_workflow(
                        [
                            {
                                "action": step.action,
                                "category": step.category,
                                "params": step.params,
                                "priority": step.priority,
                            }
                            for step in complex_command.steps
                        ]
                    )

                    if optimization and optimization.get("optimized_steps"):
                        complex_command = self._apply_optimizations(complex_command, optimization)

                    # Add optimization info to context
                    if optimization:
                        complex_command.context["ai_optimizations"] = optimization.get(
                            "improvements", []
                        )
                        complex_command.context["parallel_groups"] = optimization.get(
                            "parallel_groups", []
                        )
                except Exception as opt_error:
                    self.logger.warning(f"Workflow optimization skipped due to: {opt_error}")
                    # Continue without optimization - don't fail the entire parse

            return complex_command

        except Exception as e:
            self.logger.error(f"AI parsing failed, using fallback: {e}")
            return self.fallback_parser.parse_complex_command(command)

    # Canonical filesystem action names the adapters + workflow engine
    # implement. The model emits many synonyms; map them to one contract.
    _FS_ACTION_ALIASES = {
        "create_directory": "create_folder",
        "make_directory": "create_folder",
        "create_dir": "create_folder",
        "make_dir": "create_folder",
        "mkdir": "create_folder",
        "new_folder": "create_folder",
        "create_plaintext_file": "create_file",
        "create_plain_text_file": "create_file",
        "create_text_file": "create_file",
        "create_txt_file": "create_file",
        "create_file_with_content": "create_file",
        "write_file": "create_file",
        "write_text_file": "create_file",
        "save_file": "create_file",
        "new_file": "create_file",
        "touch": "create_file",
    }

    # Batch actions the model emits for "N folders" / "a file in each": one
    # step carrying many items. The adapters only implement the singular
    # create_folder / create_file, so these must be fanned out.
    _FS_BATCH_FOLDER_ACTIONS = {
        "create_directories",
        "create_folders",
        "make_directories",
        "create_dirs",
    }
    _FS_BATCH_FILE_ACTIONS = {
        "create_files",
        "write_files",
        "create_text_files",
    }

    def _expand_step(
        self, action: str, category: str, params: dict[str, Any]
    ) -> list[tuple[str, dict[str, Any]]]:
        """Fan a batch filesystem step out into canonical single-item steps.

        The model emits ``create_directories`` (many names under one parent) and
        ``create_files`` (a list of ``{path, content}``); only the singular
        ``create_folder`` / ``create_file`` are implemented downstream. Expanding
        here means both the single-step engine and the workflow engine receive
        units they can actually execute. Non-batch steps return a one-element
        list, so the caller always iterates uniformly.
        """
        params = dict(params or {})
        if category == "filesystem":
            if action in self._FS_BATCH_FOLDER_ACTIONS:
                parent = (
                    params.get("parent_directory")
                    or params.get("parent")
                    or params.get("location")
                    or "."
                )
                names = (
                    params.get("directory_names")
                    or params.get("names")
                    or params.get("folders")
                    or []
                )
                expanded = [
                    self._normalize_step(
                        "create_folder", category, {"name": str(n), "location": parent}
                    )
                    for n in names
                ]
                if expanded:
                    return expanded
            if action in self._FS_BATCH_FILE_ACTIONS:
                files = params.get("files") or []
                expanded = [
                    self._normalize_step("create_file", category, dict(f))
                    for f in files
                    if isinstance(f, dict)
                ]
                if expanded:
                    return expanded
        return [self._normalize_step(action, category, params)]

    def _normalize_step(
        self, action: str, category: str, params: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """Map a model-emitted step onto the canonical action + param contract.

        Only filesystem file/folder creation is normalised — the layer that was
        silently failing when the model said "create_directory" or supplied a
        ``path`` where the adapter wanted ``name`` + ``location``. Other
        categories pass through untouched.
        """
        if category != "filesystem":
            return action, params

        action = self._FS_ACTION_ALIASES.get(action, action)
        params = dict(params or {})

        # Reconcile path <-> name/location so every consumer finds what it reads:
        # the OS adapter wants name + location, _handle_write_file wants path.
        if action in ("create_file", "create_folder"):
            path = params.get("path") or params.get("file_path")
            if path and not params.get("name"):
                import os as _os

                params["name"] = _os.path.basename(path.rstrip("/"))
                parent = _os.path.dirname(path.rstrip("/"))
                if parent and not params.get("location"):
                    params["location"] = parent
            elif params.get("name") and not path:
                import os as _os

                loc = params.get("location") or "."
                params["path"] = _os.path.join(loc, params["name"])

        return action, params

    # File extensions whose "create" means "write prose", not code. Content for
    # these is generated from the request when the plan leaves it empty.
    _DOC_EXTENSIONS = (".md", ".markdown", ".txt", ".rst", ".text")

    def _fill_document_content(self, command: ComplexCommand, request: str) -> None:
        """Generate body text for document-file steps the plan left empty.

        The model reliably plans *where* a document goes but seldom inlines its
        full body into a JSON param, so document requests wrote empty files.
        For each filesystem create step targeting a document extension with no
        meaningful content, generate the prose from the original request. Best
        effort: on any failure the step keeps its (empty) content and the file
        is still created.
        """
        if not self.ai.is_ready():
            return
        for step in command.steps:
            if step.category != "filesystem" or step.action not in ("create_file", "write_file"):
                continue
            params = step.params or {}
            if (params.get("content") or "").strip():
                continue
            name = params.get("name") or params.get("path") or params.get("file_path") or ""
            if not name.lower().endswith(self._DOC_EXTENSIONS):
                continue
            content = self.ai.generate_document(request, filename=name)
            if content:
                params["content"] = content
                step.params = params
                self.logger.info(f"Generated {len(content)} chars of content for {name}")

    def _convert_ai_plan_to_complex_command(self, ai_plan: AITaskPlan) -> ComplexCommand:
        """Convert AI task plan to ComplexCommand format"""

        # Convert AI steps to ParsedStep objects with validation
        steps = []
        invalid_actions_detected = False
        priority = 0

        for ai_step in ai_plan.execution_steps:
            action = ai_step.get("action", "unknown")
            category = ai_step.get("category", "unknown")
            params = ai_step.get("params", {}) or {}
            deps = ai_step.get("dependencies", [])
            conditions = ai_step.get("conditions")

            # The model freely invents synonymous action names, mixes param
            # shapes (path vs name/location), and packs many items into one
            # batch step. Normalise + fan out to the canonical contract the
            # adapters and workflow engine implement, so a request never dies on
            # "Unknown filesystem action: create_directory".
            expanded = self._expand_step(action, category, params)
            # A batch step fans out into many; the model's index-based
            # dependencies no longer line up, and these filesystem ops create
            # their parents on demand — so drop deps when one step became many.
            fanned_out = len(expanded) > 1

            for norm_action, norm_params in expanded:
                # Check if action and category look suspicious (likely AI hallucination)
                # Common indicators: made-up action names, wrong category mappings
                if self._is_invalid_action(norm_action, category):
                    self.logger.warning(f"AI generated invalid action: {category}:{norm_action}")
                    invalid_actions_detected = True
                    continue

                priority += 1
                steps.append(
                    ParsedStep(
                        action=norm_action,
                        category=category,
                        params=norm_params,
                        dependencies=[] if fanned_out else deps,
                        conditions=conditions,
                        priority=priority,
                    )
                )

        # If AI generated invalid actions, use fallback parser instead
        if invalid_actions_detected or len(steps) == 0:
            self.logger.warning("AI generated invalid actions, using fallback parser")
            return self.fallback_parser.parse_complex_command(ai_plan.original_request)

        # Determine complexity from the final step count (after batch fan-out,
        # not the raw plan count — 3 model steps can become 31 real steps).
        if len(steps) <= 1:
            complexity = CommandComplexity.SIMPLE
        elif len(steps) <= 3:
            complexity = CommandComplexity.COMPOUND
        else:
            complexity = CommandComplexity.WORKFLOW

        # Calculate estimated duration
        estimated_duration = sum(step.get("estimated_time", 5) for step in ai_plan.execution_steps)

        return ComplexCommand(
            original_command=ai_plan.original_request,
            complexity=complexity,
            steps=steps,
            context={},  # Empty context since context_analysis doesn't exist
            estimated_duration=estimated_duration,
        )

    def _is_invalid_action(self, action: str, category: str) -> bool:
        """Check if an action/category pair looks invalid or AI-hallucinated"""

        # Known valid categories
        valid_categories = {
            "filesystem",
            "process",
            "gui",
            "network",
            "system",
            "project_generator",
            "package_manager",
            "devops",
            "web_automation",
            "universal_automation",
            "installer",
            "git",
            "editor",
            "backup",
            "development",
            "code_generator",
            "code_modification",
            "data_generator",
        }

        # Check if category is valid
        if category not in valid_categories:
            return True

        # Known invalid actions (AI hallucinations)
        hallucinated_actions = {
            "search_wikipedia",
            "extract_article_content",
            "search_google",
            "browse_web",
            "navigate_to",
            "click_link",
            "find_element",
            "scrape_data",
            "get_html",
            "parse_html",
        }

        if action in hallucinated_actions:
            return True

        # Check for common patterns of invalid actions
        # GUI category should not have web-related actions
        return bool(
            category == "gui"
            and any(
                keyword in action
                for keyword in ["search", "extract", "scrape", "wikipedia", "web", "article"]
            )
        )

    def _apply_optimizations(
        self, complex_command: ComplexCommand, optimization: dict[str, Any]
    ) -> ComplexCommand:
        """Apply AI optimizations to the complex command"""

        optimized_steps = optimization.get("optimized_steps", [])
        if not optimized_steps:
            return complex_command

        # Update steps with optimizations. These come straight from the model,
        # so they carry the same synonym/batch/param-shape problems as a raw
        # plan — run them through the same expansion+normalization boundary,
        # otherwise an "optimized" plan reintroduces Unknown filesystem actions.
        new_steps = []
        priority = 0
        for opt_step in optimized_steps:
            action = opt_step.get("action", "unknown")
            category = opt_step.get("category", "unknown")
            params = opt_step.get("params", {}) or {}
            deps = opt_step.get("dependencies", [])
            expanded = self._expand_step(action, category, params)
            fanned_out = len(expanded) > 1
            for norm_action, norm_params in expanded:
                priority += 1
                new_steps.append(
                    ParsedStep(
                        action=norm_action,
                        category=category,
                        params=norm_params,
                        dependencies=[] if fanned_out else deps,
                        priority=priority,
                    )
                )

        # Update estimated duration if provided
        if "estimated_duration" in optimization:
            complex_command.estimated_duration = optimization["estimated_duration"]

        complex_command.steps = new_steps

        # Add optimization info to context
        complex_command.context["ai_optimizations"] = optimization.get("improvements", [])
        complex_command.context["parallel_groups"] = optimization.get("parallel_groups", [])

        return complex_command

    def get_smart_suggestions(self, context: dict[str, Any] = None) -> list[str]:
        """Get AI-powered smart suggestions"""

        if not self.ai.is_ready():
            return [
                "Start Ollama to enable AI suggestions",
                "Try 'examples' for command ideas",
                "Use 'help' to see available commands",
            ]

        # Build context from command history and current state
        suggestion_context = context or {}
        suggestion_context["recent_commands"] = self.command_history[-10:]
        suggestion_context["user_patterns"] = self.user_patterns

        return self.ai.generate_smart_suggestions(suggestion_context)

    def analyze_command_intent(self, command: str) -> dict[str, Any]:
        """Analyze command intent using AI"""

        if not self.ai.is_ready():
            return {
                "intent": "Basic parsing only",
                "confidence": 0.1,
                "suggestions": ["Start Ollama for better analysis"],
            }

        try:
            ai_plan = self.ai.analyze_automation_request(command)

            return {
                "intent": ai_plan.interpreted_intent,
                "confidence": ai_plan.confidence_score,
                "risks": ai_plan.risk_assessment,
                "optimizations": ai_plan.optimization_suggestions,
                "steps_count": len(ai_plan.execution_steps),
            }

        except Exception as e:
            self.logger.error(f"Intent analysis failed: {e}")
            return {"intent": "Analysis failed", "confidence": 0.0, "error": str(e)}

    def handle_execution_error(self, error_info: dict[str, Any]) -> dict[str, Any]:
        """Get AI suggestions for handling execution errors"""

        if not self.ai.is_ready():
            return {"suggestions": ["Check logs and try again"], "confidence": 0.1}

        return self.ai.suggest_error_resolution(error_info)

    def learn_from_execution(self, command: str, result: dict[str, Any]):
        """Learn from command execution results"""

        # Update user patterns based on successful executions
        if result.get("success"):
            # Extract patterns from successful commands
            if "create" in command.lower():
                self.user_patterns["prefers_creation"] = (
                    self.user_patterns.get("prefers_creation", 0) + 1
                )

            if "project" in command.lower():
                self.user_patterns["works_with_projects"] = (
                    self.user_patterns.get("works_with_projects", 0) + 1
                )

            # Track complexity preferences
            complexity = result.get("complexity", "simple")
            pattern_key = f"uses_{complexity}_commands"
            self.user_patterns[pattern_key] = self.user_patterns.get(pattern_key, 0) + 1

    # A single "create/write a document with <prose>" request. The prose often
    # contains its own "and"s ("ham and pineapple", "temperature and time"),
    # which must not be mistaken for multiple file operations.
    _DOC_REQUEST_RE = re.compile(
        r"\b(create|write|make|generate|save|produce)\b.{0,40}?"
        r"(file|document|doc|readme|guide|notes?|report|manual|"
        r"\.md|\.markdown|\.txt|\.rst|\.text)",
        re.IGNORECASE,
    )

    def _looks_like_document_request(self, command: str) -> bool:
        """True when the command is one document-write, not multi-file work.

        The >200-char complexity heuristic routes to the regex fallback, which
        mangles a single ``create file /path/x.md with <long prose>`` into a
        bogus nested path. Document requests plan cleanly as one ``create_file``
        step under the AI parser, so keep them there. Genuine multi-file work
        (two or more document targets) still falls through to normal routing.
        """
        if not self._DOC_REQUEST_RE.search(command):
            return False
        targets = len(re.findall(r"\.(?:md|markdown|txt|rst|text)\b", command, re.IGNORECASE))
        return targets <= 1

    def _is_complex_structure(self, command: str) -> bool:
        """Detect if command has complex nested structure"""
        import re
        # Check for loop/nesting indicators
        nested_patterns = [
            r"in\s+(?:that|those|each|every)",
            r"and\s+in\s+",
            r"inside\s+(?:each|every|that)",
            r"\d+\s+folders?.*\d+\s+folders?",
            r"table \d+ to table \d+",
        ]

        for pattern in nested_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True

        # Check for multiple action conjunctions
        actions = command.lower().count(" and ")
        return actions >= 3

    def get_ai_status(self) -> dict[str, Any]:
        """Get AI integration status"""
        return self.ai.get_ai_status()

    def set_model(self, model_name: str) -> bool:
        """Switch the active Ollama model."""
        try:
            return self.ai.set_model(model_name)
        except Exception as e:
            self.logger.error(f"Failed to set model: {e}")
            return False
