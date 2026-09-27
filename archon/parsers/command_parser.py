"""
Advanced command parser for complex, multi-step natural language commands
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class CommandComplexity(Enum):
    SIMPLE = "simple"  # Single action
    COMPOUND = "compound"  # Multiple related actions
    WORKFLOW = "workflow"  # Complex multi-step process
    CONDITIONAL = "conditional"  # If-then logic


@dataclass
class ParsedStep:
    """A single step in a complex command"""

    action: str
    category: str
    params: dict[str, Any]
    dependencies: list[int] | None = None  # Indices of steps this depends on
    conditions: list[str] | None = None  # Conditions for execution
    priority: int = 0  # Execution priority


@dataclass
class ComplexCommand:
    """A complex command broken down into executable steps"""

    original_command: str
    complexity: CommandComplexity
    steps: list[ParsedStep]
    context: dict[str, Any]
    estimated_duration: int = 0  # Seconds


class AdvancedCommandParser:
    """Advanced parser for complex natural language commands"""

    def __init__(self):
        self.workflow_patterns = self._load_workflow_patterns()
        self.action_keywords = self._load_action_keywords()
        self.context_keywords = self._load_context_keywords()
        self.conjunction_words = ["and", "then", "after", "next", "also", "plus", "followed by"]
        self.conditional_words = ["if", "when", "unless", "after", "before", "while"]
        # Map logical categories to actual plugin names where applicable
        self.plugin_category_map = {
            "devops": "devops_generator",
            "project_generator": "project_generator",
            "web": "web_automation",
            "folder_ops": "folder_operations",
            "universal": "universal_automation",
            "package_manager": "universal_automation",
        }

    def parse_complex_command(self, command: str) -> ComplexCommand:
        """Parse a complex natural language command into executable steps"""

        # Clean and normalize the command
        normalized_command = self._normalize_command(command)

        # Determine complexity
        complexity = self._determine_complexity(normalized_command)

        # Extract context and intent
        context = self._extract_context(normalized_command)

        # Break down into steps based on complexity
        if complexity == CommandComplexity.SIMPLE:
            steps = self._parse_simple_command(normalized_command)
        elif complexity == CommandComplexity.COMPOUND:
            steps = self._parse_compound_command(normalized_command)
        elif complexity == CommandComplexity.WORKFLOW:
            steps = self._parse_workflow_command(normalized_command, context)
        else:  # CONDITIONAL
            steps = self._parse_conditional_command(normalized_command)

        # Estimate duration
        duration = self._estimate_duration(steps)

        # Remap logical categories to concrete plugin names when appropriate
        try:
            for s in steps:
                if hasattr(self, "plugin_category_map") and s.category in self.plugin_category_map:
                    s.category = self.plugin_category_map[s.category]
            # Normalize screenshot parameter keys so downstream engine/plugins see a consistent `path` key
            for s in steps:
                if s.action in ("take_screenshot", "screenshot", "save_screenshot"):
                    params = s.params or {}
                    candidate_keys = [
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
                    for k in candidate_keys:
                        if k in params and params.get(k):
                            params["path"] = params.get(k)
                            break
                    s.params = params

            # Normalize install/uninstall intents: prefer explicit uninstall when user mentions uninstall/remove
            uninstall_keywords = [
                "uninstall",
                "remove",
                "delete",
                "uninstalling",
                "remove program",
                "remove app",
                "remove application",
            ]
            install_keywords = ["install", "setup", "installing", "install program", "install app"]
            try:
                if any(k in normalized_command for k in uninstall_keywords):
                    for s in steps:
                        act = (s.action or "").lower()
                        if "install" in act or act in (
                            "install_package",
                            "install_software",
                            "execute_installer",
                            "download_and_install",
                        ):
                            s.action = "uninstall_software"
                            s.category = "package_manager"
                elif any(k in normalized_command for k in install_keywords):
                    for s in steps:
                        act = (s.action or "").lower()
                        if "uninstall" in act or act in ("uninstall_software",):
                            s.action = "install_software"
                            s.category = "package_manager"
            except Exception:
                pass

            # Map common package/app names to platform package IDs to reduce ambiguity
            try:
                package_name_map = {
                    "vlc": "vlc",
                    "video lan vlc": "vlc",
                    "vscode": "code",
                    "visual studio code": "code",
                    "google chrome": "google-chrome",
                    "chrome": "google-chrome",
                    "firefox": "firefox",
                    "git": "git",
                    "nodejs": "nodejs",
                    "node.js": "nodejs",
                    "python": "python",
                    "python3": "python",
                    "neovim": "neovim",
                    "vim": "vim",
                    "htop": "htop",
                    "wget": "wget",
                    "curl": "curl",
                    "docker": "docker",
                    "steam": "steam",
                    "discord": "discord",
                }

                for s in steps:
                    act_low = (s.action or "").lower()
                    if act_low in (
                        "install_software",
                        "uninstall_software",
                        "install_package",
                        "uninstall_package",
                    ):
                        params = s.params or {}
                        software = (
                            params.get("software") or params.get("package") or params.get("name")
                        )
                        if not software:
                            # Find any known package name mentioned in the command
                            for name, pkg_id in package_name_map.items():
                                if name in normalized_command:
                                    params["software"] = pkg_id
                                    params["software_name"] = name
                                    s.params = params
                                    break
                        else:
                            # Normalize provided software string to an ID if possible
                            sw_lower = str(software).lower()
                            for name, pkg_id in package_name_map.items():
                                if name in sw_lower:
                                    params["software"] = pkg_id
                                    params["software_name"] = software
                                    s.params = params
                                    break
            except Exception:
                pass
        except Exception:
            # Non-fatal: if remapping fails, return steps as-is
            pass

        # If parser produced no explicit install/uninstall steps but the user command
        # clearly requests installation or removal, synthesize a package_manager step
        try:
            has_installation_steps = any(
                (s.action or "").lower()
                in (
                    "install_software",
                    "uninstall_software",
                    "install_package",
                    "uninstall_package",
                )
                for s in steps
            )

            if not has_installation_steps:
                uninstall_kw = ["uninstall", "remove", "delete"]
                install_kw = ["install", "setup"]
                package_name_map = {
                    "vlc": "vlc",
                    "vscode": "code",
                    "visual studio code": "code",
                    "google chrome": "google-chrome",
                    "chrome": "google-chrome",
                    "firefox": "firefox",
                    "git": "git",
                    "nodejs": "nodejs",
                    "python": "python",
                    "neovim": "neovim",
                    "vim": "vim",
                    "docker": "docker",
                    "htop": "htop",
                    "steam": "steam",
                    "discord": "discord",
                }

                if any(k in normalized_command for k in uninstall_kw):
                    for name, pkg in package_name_map.items():
                        if name in normalized_command:
                            steps.append(
                                ParsedStep(
                                    action="uninstall_software",
                                    category="package_manager",
                                    params={"software": pkg, "software_name": name},
                                )
                            )
                            break
                elif any(k in normalized_command for k in install_kw):
                    for name, pkg in package_name_map.items():
                        if name in normalized_command:
                            steps.append(
                                ParsedStep(
                                    action="install_software",
                                    category="package_manager",
                                    params={"software": pkg, "software_name": name},
                                )
                            )
                            break
        except Exception:
            pass

        return ComplexCommand(
            original_command=command,
            complexity=complexity,
            steps=steps,
            context=context,
            estimated_duration=duration,
        )

    def _normalize_command(self, command: str) -> str:
        """Normalize command text for better parsing"""
        # Convert to lowercase
        normalized = command.lower().strip()

        # Replace common variations
        replacements = {
            " & ": " and ",
            " + ": " and ",
            "vs code": "vscode",
            "visual studio code": "vscode",
            "notepad++": "notepadplusplus",
            "web browser": "browser",
            "internet browser": "browser",
        }

        for old, new in replacements.items():
            normalized = normalized.replace(old, new)

        # Spell correction for common mistyped action verbs (whole-word only)
        spell_corrections = {
            r"\bcrete\b": "create",
            r"\bcreat\b": "create",
            r"\bcrate\b": "create",
            r"\bcreaet\b": "create",
            r"\bdeelte\b": "delete",
            r"\bdelet\b": "delete",
            r"\bmovee\b": "move",
            r"\bmve\b": "move",
            r"\brname\b": "rename",
            r"\brenme\b": "rename",
            r"\binstal\b": "install",
            r"\binstll\b": "install",
            r"\bdownlad\b": "download",
            r"\bdownlaod\b": "download",
            r"\bdowload\b": "download",
        }
        for pattern, replacement in spell_corrections.items():
            normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

        return normalized

    def _determine_complexity(self, command: str) -> CommandComplexity:
        """Determine the complexity level of the command"""

        # Check for specific workflow patterns first
        workflow_indicators = [
            "data analysis",
            "web scraping",
            "development environment",
            "machine learning",
            "full stack",
            "complete setup",
        ]

        if any(indicator in command for indicator in workflow_indicators):
            return CommandComplexity.WORKFLOW

        # Check for data science stack
        data_science_tools = ["pandas", "matplotlib", "seaborn", "jupyter", "numpy"]
        data_science_count = sum(1 for tool in data_science_tools if tool in command)
        if data_science_count >= 3:
            return CommandComplexity.WORKFLOW

        # Check for bulk/nested operations (multiple folders, naming ranges, etc.)
        bulk_indicators = [
            r"\d+\s+folders?",  # e.g., "100 folders"
            r"naming\s+from",  # e.g., "naming from test2"
            r"from\s+\w+\s+to\s+\w+",  # e.g., "from test2 to test100"
            r"among\s+(?:those|the)",  # e.g., "among those test folders"
        ]
        bulk_count = sum(
            1 for pattern in bulk_indicators if re.search(pattern, command, re.IGNORECASE)
        )
        if bulk_count >= 2:
            return CommandComplexity.WORKFLOW

        # Single-action commands should be SIMPLE, even if they have prepositions like "to", "in", "on"
        simple_actions = ["copy", "move", "delete", "create folder", "create file", "rename"]
        if any(action in command for action in simple_actions):
            # SIMPLE only when there are no bulk indicators AND no conjunctions
            has_conjunction = any(
                re.search(r"\b" + re.escape(word) + r"\b", command, re.IGNORECASE)
                for word in self.conjunction_words
            )
            if bulk_count == 0 and not has_conjunction:
                return CommandComplexity.SIMPLE

        # Count conjunctions and conditional words
        conjunction_count = sum(
            1
            for word in self.conjunction_words
            if re.search(r"\b" + word + r"\b", command, re.IGNORECASE)
        )
        conditional_count = sum(
            1
            for word in self.conditional_words
            if re.search(r"\b" + word + r"\b", command, re.IGNORECASE)
        )

        # Count distinct action verbs
        action_count = sum(1 for keyword in self.action_keywords if keyword in command)

        # Determine complexity
        if conditional_count > 0:
            return CommandComplexity.CONDITIONAL
        elif conjunction_count >= 2 or action_count >= 3 or bulk_count > 0:
            return CommandComplexity.WORKFLOW
        elif conjunction_count >= 1 or action_count >= 2:
            return CommandComplexity.COMPOUND
        else:
            return CommandComplexity.SIMPLE

    def _extract_context(self, command: str) -> dict[str, Any]:
        """Extract context information from the command"""
        context = {
            "programming_languages": [],
            "tools": [],
            "file_types": [],
            "locations": [],
            "technologies": [],
        }

        # Programming languages
        languages = [
            "python",
            "javascript",
            "java",
            "c++",
            "c#",
            "php",
            "ruby",
            "go",
            "rust",
            "swift",
        ]
        for lang in languages:
            if lang in command:
                context["programming_languages"].append(lang)

        # Development tools
        tools = ["vscode", "git", "npm", "pip", "docker", "nodejs", "react", "angular", "vue"]
        for tool in tools:
            if tool in command:
                context["tools"].append(tool)

        # File types
        file_types = [".py", ".js", ".html", ".css", ".json", ".xml", ".csv", ".txt", ".md"]
        for ft in file_types:
            if ft in command:
                context["file_types"].append(ft)

        # Common locations
        locations = ["desktop", "documents", "downloads", "home", "project", "workspace"]
        for loc in locations:
            if loc in command:
                context["locations"].append(loc)

        return context

    def _parse_workflow_command(self, command: str, context: dict[str, Any]) -> list[ParsedStep]:
        """Parse complex workflow commands"""
        steps = []

        # Check for "inside/inside each" nested structures first (most specific)
        if "inside" in command.lower() and self._has_loop_construct(command):
            inside_steps = self._parse_inside_nested_structure(command, context)
            if inside_steps:
                return inside_steps

        # Check for loop/iteration constructs (NEW - more versatile)
        if self._has_loop_construct(command):
            return self._parse_loop_command(command, context)

        # Check for nested operations
        if self._has_nested_operations(command):
            return self._parse_nested_command(command, context)

        # Check for document creation + web scraping workflows
        if ("extract" in command or "scrape" in command) and any(
            doc_word in command
            for doc_word in [
                "word",
                "document",
                "docx",
                "powerpoint",
                "ppt",
                "excel",
                "xlsx",
                "spreadsheet",
            ]
        ):
            steps.extend(self._create_web_to_document_workflow(command, context))
        # Check for common workflow patterns
        elif "web scraping" in command or "scrape" in command:
            steps.extend(self._create_web_scraping_workflow(command, context))
        elif "development environment" in command or "dev environment" in command:
            steps.extend(self._create_dev_environment_workflow(command, context))
        elif "data analysis" in command or (
            "pandas" in command and ("matplotlib" in command or "seaborn" in command)
        ):
            steps.extend(self._create_data_analysis_workflow(command, context))
        elif "backup" in command and ("download" in command or "install" in command):
            steps.extend(self._create_backup_and_install_workflow(command, context))
        elif "project" in command and any(
            lang in command for lang in context["programming_languages"]
        ):
            steps.extend(self._create_project_setup_workflow(command, context))
        else:
            # Generic workflow parsing
            steps.extend(self._parse_generic_workflow(command))

        return steps

    def _create_web_to_document_workflow(
        self, command: str, context: dict[str, Any]
    ) -> list[ParsedStep]:
        """Create workflow for web extraction followed by document creation"""
        steps = []

        # Step 1: Open browser if requested
        if "open browser" in command or "browser" in command:
            steps.append(
                ParsedStep(
                    action="open_browser",
                    category="web_automation",
                    params={"headless": False},
                    priority=1,
                )
            )

        # Step 2: Navigate to website/search
        if "wikipedia" in command or "search" in command:
            # Extract search query
            search_match = re.search(
                r'search (?:for |on )?["\']?([^"\']+?)["\']?(?:\s+on\s+|\s+in\s+|$)',
                command,
                re.IGNORECASE,
            )
            if search_match:
                query = search_match.group(1).strip()
                if "wikipedia" in command:
                    url = f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}"
                    steps.append(
                        ParsedStep(
                            action="extract_article",
                            category="web_automation",
                            params={"url": url},
                            priority=2,
                            dependencies=[len(steps) - 1] if steps else [],
                        )
                    )
                else:
                    steps.append(
                        ParsedStep(
                            action="search_and_extract",
                            category="web_automation",
                            params={"query": query},
                            priority=2,
                            dependencies=[len(steps) - 1] if steps else [],
                        )
                    )
        elif "extract" in command or "scrape" in command:
            # Extract from URL
            url_match = re.search(r"https?://[^\s]+", command)
            if url_match:
                steps.append(
                    ParsedStep(
                        action="extract_article",
                        category="web_automation",
                        params={"url": url_match.group(0)},
                        priority=2,
                        dependencies=[len(steps) - 1] if steps else [],
                    )
                )

        # Step 3: Create document(s)
        doc_type = None
        filename = None
        folder = None

        # Detect document type
        if "word" in command or "docx" in command or "document" in command:
            doc_type = "word"
            filename_match = re.search(
                r'(?:named|called|name)\s+["\']?([^"\'\.]+\.docx|[^"\'\.]+)["\']?',
                command,
                re.IGNORECASE,
            )
            if filename_match:
                filename = filename_match.group(1)
                if not filename.endswith(".docx"):
                    filename += ".docx"
        elif "powerpoint" in command or "ppt" in command or "presentation" in command:
            doc_type = "powerpoint"
            filename_match = re.search(
                r'(?:named|called|name)\s+["\']?([^"\'\.]+\.pptx|[^"\'\.]+)["\']?',
                command,
                re.IGNORECASE,
            )
            if filename_match:
                filename = filename_match.group(1)
                if not filename.endswith(".pptx"):
                    filename += ".pptx"
        elif "excel" in command or "xlsx" in command or "spreadsheet" in command:
            doc_type = "excel"
            filename_match = re.search(
                r'(?:named|called|name)\s+["\']?([^"\'\.]+\.xlsx|[^"\'\.]+)["\']?',
                command,
                re.IGNORECASE,
            )
            if filename_match:
                filename = filename_match.group(1)
                if not filename.endswith(".xlsx"):
                    filename += ".xlsx"

        # Extract folder/location
        # Match folder name but stop before location indicators like "on Desktop"
        folder_match = re.search(
            r'(?:in|to)\s+(?:folder|directory)\s+["\']?([^"\']+?)["\']?\s+(?:on|at|in)\s+(?:the\s+)?desktop',
            command,
            re.IGNORECASE,
        )
        if folder_match:
            folder = f"Desktop/{folder_match.group(1).strip()}"
        else:
            # Try without location - just folder name
            folder_match = re.search(
                r'(?:in|to)\s+(?:folder|directory)\s+["\']?([^"\']+)["\']?', command, re.IGNORECASE
            )
            if folder_match:
                folder_name = folder_match.group(1).strip()
                # Check if Desktop is mentioned separately in the command
                if "desktop" in command.lower() and "desktop" not in folder_name.lower():
                    folder = f"Desktop/{folder_name}"
                else:
                    folder = folder_name
            elif "desktop" in command.lower():
                folder = "Desktop"

        # Create document step
        if doc_type:
            action_map = {
                "word": "create_word_document",
                "powerpoint": "create_powerpoint",
                "excel": "create_excel",
            }

            params = {}
            if filename:
                params["filename"] = filename
            if folder:
                params["folder"] = folder

            # If we extracted article content, reference it
            if any(s.action in ["extract_article", "scrape_website"] for s in steps):
                params["content"] = "{{extracted_content}}"

            steps.append(
                ParsedStep(
                    action=action_map[doc_type],
                    category="universal_automation",
                    params=params,
                    priority=3,
                    dependencies=list(range(len(steps))),
                )
            )

        return steps

    def _create_web_scraping_workflow(
        self, command: str, context: dict[str, Any]
    ) -> list[ParsedStep]:
        """Create workflow for web scraping projects"""
        steps = []

        # Extract project name
        project_match = re.search(
            r'(?:project|folder)\s+(?:called\s+)?[\'"]?([^\'"]+)[\'"]?', command
        )
        project_name = project_match.group(1) if project_match else "WebScrapingProject"

        # Step 1: Create project structure
        steps.append(
            ParsedStep(
                action="create_web_scraping_project",
                category="project_generator",
                params={"name": project_name, "type": "web_scraping"},
                priority=1,
            )
        )

        # Step 2: Install dependencies
        if "requests" in command or "beautifulsoup" in command:
            steps.append(
                ParsedStep(
                    action="install_packages",
                    category="package_manager",
                    params={"packages": ["requests", "beautifulsoup4", "lxml"]},
                    dependencies=[0],
                    priority=2,
                )
            )

        # Step 3: Create scraper file
        if "news" in command or "headlines" in command:
            steps.append(
                ParsedStep(
                    action="create_news_scraper",
                    category="code_generator",
                    params={"filename": "news_scraper.py", "target": "headlines"},
                    dependencies=[0, 1],
                    priority=3,
                )
            )

        # Step 4: Open in editor
        if "vscode" in command or "vs code" in command:
            steps.append(
                ParsedStep(
                    action="open_in_vscode",
                    category="editor",
                    params={"path": project_name},
                    dependencies=[0, 1, 2],
                    priority=4,
                )
            )

        return steps

    def _create_dev_environment_workflow(
        self, command: str, context: dict[str, Any]
    ) -> list[ParsedStep]:
        """Create development environment setup workflow"""
        steps = []

        # Install Git
        if "git" in command:
            steps.append(
                ParsedStep(
                    action="install_git", category="installer", params={"silent": True}, priority=1
                )
            )

        # Install Node.js
        if "nodejs" in command or "node.js" in command or "npm" in command:
            steps.append(
                ParsedStep(
                    action="install_nodejs",
                    category="installer",
                    params={"version": "latest"},
                    priority=2,
                )
            )

        # Install VS Code
        if "vscode" in command or "vs code" in command:
            steps.append(
                ParsedStep(
                    action="install_vscode",
                    category="installer",
                    params={"extensions": ["python", "javascript"]},
                    priority=3,
                )
            )

        # Clone repository
        if "clone" in command and "repo" in command:
            repo_match = re.search(r"github\.com/([^/]+/[^/\s]+)", command)
            if repo_match:
                steps.append(
                    ParsedStep(
                        action="clone_repository",
                        category="git",
                        params={"url": f"https://github.com/{repo_match.group(1)}"},
                        dependencies=[0] if "git" in command else [],
                        priority=4,
                    )
                )

        # Start dev server
        if "start" in command and ("server" in command or "dev" in command):
            steps.append(
                ParsedStep(
                    action="start_dev_server",
                    category="development",
                    params={"command": "npm start"},
                    dependencies=list(range(len(steps))),
                    priority=5,
                )
            )

        return steps

    def _create_backup_and_install_workflow(
        self, command: str, context: dict[str, Any]
    ) -> list[ParsedStep]:
        """Create backup and installation workflow"""
        steps = []

        # Create backup
        if "backup" in command and "documents" in command:
            steps.append(
                ParsedStep(
                    action="backup_folder",
                    category="backup",
                    params={"source": "Documents", "destination": "Backup_Documents"},
                    priority=1,
                )
            )

        # Download installer
        if "download" in command and "python" in command:
            steps.append(
                ParsedStep(
                    action="download_python_installer",
                    category="downloader",
                    params={"version": "latest"},
                    priority=2,
                )
            )

        # Take screenshot when done
        if "screenshot" in command:
            steps.append(
                ParsedStep(
                    action="take_screenshot",
                    category="gui",
                    params={"filename": "workflow_complete.png"},
                    dependencies=list(range(len(steps))),
                    priority=99,
                )
            )

        return steps

    def _create_project_setup_workflow(
        self, command: str, context: dict[str, Any]
    ) -> list[ParsedStep]:
        """Create project setup workflow"""
        steps = []

        # Determine project type from context
        if "python" in context["programming_languages"]:
            project_type = "python"
        elif "javascript" in context["programming_languages"]:
            project_type = "javascript"
        else:
            project_type = "generic"

        # Extract project name
        project_match = re.search(r'(?:project|folder)\s+[\'"]?([^\'"]+)[\'"]?', command)
        project_name = project_match.group(1) if project_match else "MyProject"

        # Create project
        steps.append(
            ParsedStep(
                action=f"create_{project_type}_project",
                category="project_generator",
                params={"name": project_name},
                priority=1,
            )
        )

        return steps

    def _create_data_analysis_workflow(
        self, command: str, context: dict[str, Any]
    ) -> list[ParsedStep]:
        """Create workflow for data analysis projects"""
        steps = []

        # Extract project name
        project_match = re.search(
            r'(?:project|analysis)\s+(?:called\s+)?[\'"]?([^\'"]+)[\'"]?', command
        )
        project_name = project_match.group(1) if project_match else "DataAnalysisProject"

        # Step 1: Create data analysis project structure
        steps.append(
            ParsedStep(
                action="create_data_analysis_project",
                category="project_generator",
                params={"name": project_name, "type": "data_analysis"},
                priority=1,
            )
        )

        # Step 2: Install data science packages
        packages = ["pandas", "numpy", "matplotlib", "seaborn", "jupyter"]
        if "scipy" in command:
            packages.append("scipy")
        if "plotly" in command:
            packages.append("plotly")
        if "sklearn" in command or "scikit-learn" in command:
            packages.append("scikit-learn")

        steps.append(
            ParsedStep(
                action="install_packages",
                category="package_manager",
                params={"packages": packages},
                dependencies=[0],
                priority=2,
            )
        )

        # Step 3: Generate sample data if requested
        if "sample" in command or "generate" in command:
            steps.append(
                ParsedStep(
                    action="generate_sample_data",
                    category="data_generator",
                    params={"project_name": project_name},
                    dependencies=[0],
                    priority=3,
                )
            )

        return steps

    # --- Compatibility wrappers ---
    def parse_flexible(self, command: str):
        """Compatibility wrapper expected by other components.

        Returns a simple object with attributes: action, category, params, confidence
        """
        complex_cmd = self.parse_complex_command(command)

        # Build a lightweight parsed object
        class _Parsed:
            def __init__(self):
                self.action = ""
                self.category = ""
                self.params = {}
                self.confidence = 0.5

        parsed = _Parsed()

        if complex_cmd.steps and len(complex_cmd.steps) > 0:
            first = complex_cmd.steps[0]
            parsed.action = first.action
            parsed.category = first.category
            parsed.params = first.params or {}
        else:
            # Fallback simple parse
            parsed.action = "create_folder" if "create" in command.lower() else "noop"
            parsed.category = "filesystem"
            parsed.params = {}

        # Map complexity to a confidence score
        confidence_map = {
            CommandComplexity.SIMPLE: 0.95,
            CommandComplexity.COMPOUND: 0.85,
            CommandComplexity.WORKFLOW: 0.60,
            CommandComplexity.CONDITIONAL: 0.60,
        }
        parsed.confidence = confidence_map.get(complex_cmd.complexity, 0.5)

        return parsed

    def get_command_variations(self, command: str) -> list[str]:
        """Return simple paraphrases/variations for a given command (compatibility helper)."""
        # Very small heuristic-based variations to satisfy callers
        variations = [command]
        # Remove parenthetical phrases
        import re

        no_paren = re.sub(r"\([^\)]*\)", "", command).strip()
        if no_paren and no_paren != command:
            variations.append(no_paren)

        # Shorten long conjunction chains into simpler sentences
        if " and " in command.lower():
            parts = [
                p.strip() for p in re.split(r"\band\b", command, flags=re.IGNORECASE) if p.strip()
            ]
            variations.extend(parts[:3])

        # Deduplicate preserving order
        seen = set()
        out = []
        for v in variations:
            if v not in seen:
                out.append(v)
                seen.add(v)

        return out

    def parse(self, command: str) -> dict[str, Any]:
        """Backward-compatible simple parse method returning a dict with action, category, params."""
        parsed = self.parse_flexible(command)
        return {
            "action": getattr(parsed, "action", ""),
            "category": getattr(parsed, "category", "filesystem"),
            "params": getattr(parsed, "params", {}),
        }

    def _parse_compound_command(self, command: str) -> list[ParsedStep]:
        """Parse compound commands with multiple actions"""
        steps = []

        # Split by conjunctions
        parts = re.split(r"\s+(?:and|then|also|plus)\s+", command)

        for i, part in enumerate(parts):
            # Parse each part as a simple command
            simple_steps = self._parse_simple_command(part.strip())
            for step in simple_steps:
                step.priority = i + 1
                if i > 0:  # Add dependency on previous step
                    step.dependencies = [len(steps) - 1]
                steps.append(step)

        return steps

    def _parse_simple_command(self, command: str) -> list[ParsedStep]:
        """Parse simple single-action commands with smart NLP"""

        # Handle file modification: "modify p1.py from fibonacci to prime numbers"
        modify_match = re.search(
            r"modify\s+(\S+)\s+from\s+(\w+)\s+to\s+(\w+(?:\s+\w+)*)", command, re.IGNORECASE
        )
        if modify_match:
            file_path = modify_match.group(1)
            old_type = modify_match.group(2)
            new_type = modify_match.group(3)
            return [
                ParsedStep(
                    action="modify_file",
                    category="code_modification",
                    params={"file_path": file_path, "intent": f"convert {old_type} to {new_type}"},
                    priority=1,
                )
            ]

        # Handle batch folder/file creation: "create 10 folders from project1 to project10"
        batch_folder_match = re.search(
            r"create\s+(\d+)\s+(?:folders?|directories?)\s+(?:(?:from|named)\s+)?(\w+)\s+to\s+(\w+)",
            command,
            re.IGNORECASE,
        )
        if batch_folder_match:
            int(batch_folder_match.group(1))
            start_name = batch_folder_match.group(2)
            end_name = batch_folder_match.group(3)

            # Extract location if specified
            location_match = re.search(r"(?:on|in|at)\s+(\w+)", command, re.IGNORECASE)
            location = location_match.group(1) if location_match else None

            # Generate folder names
            start_num = self._extract_number(start_name)
            end_num = self._extract_number(end_name)
            base_start = self._extract_base_name(start_name)
            base_end = self._extract_base_name(end_name)

            # Use the common base name
            base_name = base_start if base_start == base_end else start_name

            steps = []
            if start_num is not None and end_num is not None:
                for i in range(start_num, end_num + 1):
                    folder_name = f"{base_name}{i}"
                    steps.append(
                        ParsedStep(
                            action="create_folder",
                            category="filesystem",
                            params={"name": folder_name, "location": location},
                            priority=i - start_num + 1,
                        )
                    )
            return (
                steps
                if steps
                else [
                    ParsedStep(
                        action="unknown",
                        category="unknown",
                        params={"raw_command": command},
                        priority=1,
                    )
                ]
            )

        # Handle simple copy/move/delete commands
        if "copy" in command.lower():
            parts = command.lower().split(" to ")
            if len(parts) == 2:
                source = parts[0].replace("copy", "").strip()
                dest = parts[1].strip()
                return [
                    ParsedStep(
                        action="copy",
                        category="filesystem",
                        params={"source": source, "destination": dest},
                        priority=1,
                    )
                ]

        if "move" in command.lower():
            parts = command.lower().split(" to ")
            if len(parts) == 2:
                source = parts[0].replace("move", "").strip()
                dest = parts[1].strip()
                return [
                    ParsedStep(
                        action="move",
                        category="filesystem",
                        params={"source": source, "destination": dest},
                        priority=1,
                    )
                ]

        # Handle folder creation
        if ("create" in command.lower() or "make" in command.lower()) and (
            "folder" in command.lower() or "directory" in command.lower()
        ):
            # Prefer explicit "named X" or "called X" over word immediately after "folder"
            name_match = re.search(r'(?:named?|called)\s+["\']?(\S+)["\']?', command, re.IGNORECASE)
            if not name_match:
                name_match = re.search(
                    r'(?:folder|directory)\s+["\']?(\w+)["\']?', command, re.IGNORECASE
                )
            folder_name = name_match.group(1).strip() if name_match else "NewFolder"
            # Strip trailing punctuation/whitespace
            folder_name = folder_name.rstrip(".,;:").strip()

            location_match = re.search(r"(?:on|in|at)\s+(\w+)", command, re.IGNORECASE)
            location = location_match.group(1) if location_match else None

            return [
                ParsedStep(
                    action="create_folder",
                    category="filesystem",
                    params={"name": folder_name, "location": location},
                    priority=1,
                )
            ]

        # Handle file creation: "create a file named hello.txt with content hello world"
        if ("create" in command.lower() or "make" in command.lower()) and "file" in command.lower():
            # Prefer "named X" / "called X", then fall back to word directly after "file"
            name_match = re.search(r'(?:named?|called)\s+["\']?(\S+)["\']?', command, re.IGNORECASE)
            if not name_match:
                name_match = re.search(
                    r'\bfile\s+["\']?([\w][\w.\-+#]*)["\']?', command, re.IGNORECASE
                )
            file_name = name_match.group(1) if name_match else "newfile.txt"
            content_match = re.search(
                r"(?:with\s+content|containing|with\s+text)\s+(.+)", command, re.IGNORECASE
            )
            content = content_match.group(1) if content_match else ""
            location_match = re.search(r"(?:in|at|on)\s+(\w+)", command, re.IGNORECASE)
            location = location_match.group(1) if location_match else None
            return [
                ParsedStep(
                    action="create_file",
                    category="filesystem",
                    params={"name": file_name, "content": content, "location": location},
                    priority=1,
                )
            ]

        # Handle rename: "rename folder X to Y", "rename the folder called X to Y", etc.
        if "rename" in command.lower():
            rename_match = re.search(
                r"rename\s+(?:the\s+)?(?:(?:folder|file|directory)\s+)?(?:(?:named?|called)\s+)?"
                r'["\']?([\w][\w.\-]*)["\']?\s+(?:to|as)\s+["\']?([\w][\w.\-]*)["\']?',
                command,
                re.IGNORECASE,
            )
            if rename_match:
                return [
                    ParsedStep(
                        action="rename",
                        category="filesystem",
                        params={
                            "old_name": rename_match.group(1),
                            "new_name": rename_match.group(2),
                        },
                        priority=1,
                    )
                ]

        # Handle delete/remove: "delete folder X", "delete file X", "remove the folder called X"
        if "delete" in command.lower() or "remove" in command.lower():
            # Try "called X" / "named X" first for natural language phrases
            del_match = re.search(
                r'(?:delete|remove).*?(?:called|named?)\s+["\']?(\S+)["\']?', command, re.IGNORECASE
            )
            if not del_match:
                del_match = re.search(
                    r'(?:delete|remove)\s+(?:(?:the|a|an)\s+)?(?:(?:folder|file|directory)\s+)?["\']?([\w][\w.\-+]*)["\']?',
                    command,
                    re.IGNORECASE,
                )
            if del_match:
                target = del_match.group(1).strip("\"'.,")
                return [
                    ParsedStep(
                        action="delete", category="filesystem", params={"path": target}, priority=1
                    )
                ]

        # Handle list/show directory: "list files", "ls", "show files in /path"
        list_keywords = ["list", "ls", "show files", "show directory", "dir"]
        if any(kw in command.lower() for kw in list_keywords):
            path_match = re.search(
                r"(?:in|at|inside|of|from)\s+[\"']?([^\s\"']+)[\"']?", command, re.IGNORECASE
            )
            path = path_match.group(1) if path_match else "."
            return [
                ParsedStep(
                    action="list",
                    category="filesystem",
                    params={"path": path},
                    priority=1,
                )
            ]

        # Handle system-info queries: "show os version", "system info",
        # "what os am i on", "kernel version", "which distro".
        sys_info_patterns = [
            r"\b(?:os|operating system|system|kernel|distro|distribution)\s+"
            r"(?:version|info|information|details)\b",
            r"\b(?:show|get|display|tell me|what(?:'s| is)?|which)\b.*"
            r"\b(?:os|operating system|kernel|distro|distribution)\b",
            r"\bsystem\s+info(?:rmation)?\b",
        ]
        low = command.lower()
        if any(re.search(p, low) for p in sys_info_patterns):
            return [
                ParsedStep(
                    action="get_info",
                    category="system",
                    params={},
                    priority=1,
                )
            ]

        # Default fallback
        return [
            ParsedStep(
                action="unknown", category="unknown", params={"raw_command": command}, priority=1
            )
        ]

    def _extract_number(self, text: str) -> int | None:
        """Extract number from text like 'project1' -> 1"""
        match = re.search(r"(\d+)", text)
        return int(match.group(1)) if match else None

    def _extract_base_name(self, text: str) -> str:
        """Extract base name from text like 'project1' -> 'project'"""
        return re.sub(r"\d+$", "", text)

    def _parse_conditional_command(self, command: str) -> list[ParsedStep]:
        """Parse conditional commands with if-then logic"""
        steps = []

        # Extract condition and action parts
        if_match = re.search(r"if\s+(.+?)\s+then\s+(.+)", command)
        when_match = re.search(r"when\s+(.+?)\s+(?:then\s+)?(.+)", command)

        if if_match:
            condition = if_match.group(1)
            action = if_match.group(2)
        elif when_match:
            condition = when_match.group(1)
            action = when_match.group(2)
        else:
            # Fallback to compound parsing
            return self._parse_compound_command(command)

        # Create conditional step
        action_steps = self._parse_simple_command(action)
        for step in action_steps:
            step.conditions = [condition]
            steps.append(step)

        return steps

    def _parse_generic_workflow(self, command: str) -> list[ParsedStep]:
        """Parse generic workflow commands"""
        # Split by conjunctions and create steps
        parts = re.split(r"\s+(?:and|then|after|next|also|plus|followed by)\s+", command)
        steps = []

        for i, part in enumerate(parts):
            simple_steps = self._parse_simple_command(part.strip())
            for step in simple_steps:
                step.priority = i + 1
                if i > 0:
                    step.dependencies = [len(steps) - 1]
                steps.append(step)

        return steps

    def _estimate_duration(self, steps: list[ParsedStep]) -> int:
        """Estimate execution duration in seconds"""
        duration_map = {
            "create_folder": 1,
            "create_file": 2,
            "install_packages": 30,
            "download_file": 60,
            "backup_folder": 120,
            "clone_repository": 45,
            "install_git": 180,
            "install_nodejs": 240,
            "install_vscode": 300,
        }

        total_duration = 0
        for step in steps:
            total_duration += duration_map.get(step.action, 5)

        return total_duration

    def _load_workflow_patterns(self) -> dict[str, list[str]]:
        """Load common workflow patterns"""
        return {
            "web_development": [
                "create project",
                "install dependencies",
                "setup server",
                "open editor",
            ],
            "data_science": ["create project", "install packages", "create notebook", "load data"],
            "mobile_development": ["create project", "setup sdk", "create app", "test device"],
            "devops": ["setup environment", "configure tools", "deploy application", "monitor"],
        }

    def _load_action_keywords(self) -> list[str]:
        """Load action keywords for complexity detection"""
        return [
            "create",
            "make",
            "build",
            "generate",
            "setup",
            "install",
            "download",
            "upload",
            "copy",
            "move",
            "delete",
            "remove",
            "open",
            "close",
            "start",
            "stop",
            "run",
            "execute",
            "launch",
            "kill",
            "terminate",
            "backup",
            "restore",
            "sync",
            "clone",
            "commit",
            "push",
            "pull",
            "deploy",
            "test",
            "debug",
            "compile",
            "build",
        ]

    def _load_context_keywords(self) -> dict[str, list[str]]:
        """Load context keywords for better understanding"""
        return {
            "development": ["project", "code", "programming", "development", "software"],
            "web": ["website", "web", "html", "css", "javascript", "server", "api"],
            "data": ["data", "database", "csv", "json", "analysis", "visualization"],
            "system": ["system", "admin", "configuration", "settings", "registry"],
            "network": ["network", "internet", "download", "upload", "sync", "cloud"],
        }

    def _parse_inside_nested_structure(
        self, command: str, context: dict[str, Any]
    ) -> list[ParsedStep]:
        """
        Parse commands with 'inside/inside each' nesting patterns
        Example: "create folder1, inside 100 folders numbered 1-100, inside each 15 subfolders, inside each readme"
        """
        steps = []

        try:
            # Split by commas to get nesting levels
            parts = [p.strip() for p in command.split(",")]

            if not parts:
                return []

            # Level 0: Root folder creation
            root_part = parts[0]
            root_match = re.search(
                r"create\s+(?:a\s+)?(?:folder\s+)?(?:named?\s+)?([a-zA-Z_][a-zA-Z0-9_]*)",
                root_part,
                re.IGNORECASE,
            )
            if root_match:
                root_name = root_match.group(1)
                steps.append(
                    ParsedStep(
                        action="create_folder",
                        category="filesystem",
                        params={"name": root_name, "location": "."},
                        priority=1,
                    )
                )
                context["root_folder"] = root_name

            # Parse remaining levels
            for level_idx, part in enumerate(parts[1:], start=1):
                part_lower = part.lower()

                # Extract count and range — match "folders", "subfolders", "directories"
                count_match = re.search(
                    r"inside\s+(?:each\s+)?(\d+)\s+(?:sub)?folders?(?:\s|,|$)", part_lower
                )
                range_match = re.search(
                    r"(?:numbered?|naming|from)\s+(\d+)\s*(?:-|to)\s*(\d+)", part_lower
                )

                if count_match:
                    count = int(count_match.group(1))
                    start_num = 1
                    end_num = count

                    if range_match:
                        start_num = int(range_match.group(1))
                        end_num = int(range_match.group(2))
                        count = end_num - start_num + 1

                    # "inside each" = nested inside every folder from the previous level
                    is_nested = "inside each" in part_lower or (
                        level_idx > 1 and "inside" in part_lower
                    )

                    steps.append(
                        ParsedStep(
                            action="create_nested_folders"
                            if is_nested and level_idx > 1
                            else "create_bulk_folders",
                            category="filesystem",
                            params={
                                "count": count,
                                "start": start_num,
                                "end": end_num,
                                "parent_folder": context.get("root_folder", ".")
                                if level_idx == 1
                                else context.get("root_folder", "."),
                                "nested_in_each": is_nested,
                                "level": level_idx,
                            },
                            priority=level_idx + 1,
                            dependencies=list(range(len(steps))),
                        )
                    )
                    context[f"level_{level_idx}_count"] = count
                    context["last_folder_level"] = level_idx

                # Check for file creation (readme, etc.)
                elif re.search(r"readme|\.md\b|\.txt\b|\bfile\b", part_lower):
                    # Match "readme file", "a readme file", "readme.md" etc.
                    filename = "README.md"
                    file_match = re.search(
                        r"(?:a\s+)?([a-zA-Z_][a-zA-Z0-9_.]*(?:\.(?:md|txt|py|js|html))?)\s+file",
                        part_lower,
                    )
                    if file_match:
                        name = file_match.group(1)
                        if name == "readme":
                            filename = "README.md"
                        elif "." in name:
                            filename = name
                        else:
                            filename = name + ".md"

                    # Extract content if provided
                    content = ""
                    content_match = re.search(
                        r'(?:with\s+(?:the\s+)?text|saying|containing)\s+["\']?(.+?)["\']?$',
                        part,
                        re.IGNORECASE,
                    )
                    if content_match:
                        content = content_match.group(1).strip()

                    # "inside each" = create in every deepest-level folder
                    is_nested = "inside each" in part_lower

                    steps.append(
                        ParsedStep(
                            action="create_nested_files" if is_nested else "create_file",
                            category="filesystem",
                            params={
                                "filename": filename,
                                "content": content,
                                "nested_in_each": is_nested,
                                "level": level_idx,
                                "parent_folder": context.get("root_folder", "."),
                            },
                            priority=level_idx + 1,
                            dependencies=list(range(len(steps))),
                        )
                    )

            return steps if steps else []

        except Exception as e:
            self.logger.error(f"Error parsing inside nested structure: {e}")
            return []

    def _has_loop_construct(self, command: str) -> bool:
        """Check if command contains loop/iteration constructs"""
        loop_indicators = [
            r"\b\d+\s+folders?\b",  # "10 folders"
            r"create.*(?:each|every)\b",  # "create for each"
            r"(?:for|to)\s+\d+\s*(?:times?|iterations?)",  # "for 10 times"
            r"from.*to\s+\d+",  # "from 1 to 10"
            r"multiply|multiplication table",  # multiplication operations
            r"repeat|duplicate.*\d+",  # "repeat 5 times"
            r"\d+\s+(?:times?|copies|instances)",  # "5 times", "5 copies"
        ]

        return any(re.search(indicator, command, re.IGNORECASE) for indicator in loop_indicators)

    def _has_nested_operations(self, command: str) -> bool:
        """Check if command contains nested/hierarchical operations"""
        nested_indicators = [
            r"in\s+(?:that|those|each|every)",  # "in each folder"
            r"inside\s+(?:that|those|each)",  # "inside each"
            r"and\s+in\s+(?:those|each)",  # "and in each"
            r"with\s+(?:each|every)\s+(?:file|folder)",  # "with each file"
        ]

        return any(re.search(indicator, command, re.IGNORECASE) for indicator in nested_indicators)

    def _parse_loop_command(self, command: str, context: dict[str, Any]) -> list[ParsedStep]:
        """
        Parse commands with loops/iterations - intelligently handles:
        - Sequential loops: "create folder A, then create X items in it, then create Y items in each X"
        - Range-based loops: "naming from test2 to test100"
        - Nested loops: "among those folders create..."
        """
        steps = []

        try:
            # NEW INTELLIGENT PARSING: Break down command by sequential operations
            # Pattern: "[CREATE main] AND [CREATE N folders NAMING FROM X TO Y] AND [AMONG THOSE CREATE M folders NAMING FROM A TO B]"

            # Step 1: Extract all major operations separated by "and"
            operations = self._split_complex_operations(command)

            for op_idx, operation in enumerate(operations):
                op_lower = operation.lower().strip()

                # Operation Type 1: Create main container
                if op_idx == 0 and re.search(
                    r"create\s+(?:a\s+)?folder\s+(?:named?|as)\s+", op_lower
                ):
                    folder_match = re.search(
                        r"create\s+(?:a\s+)?folder\s+(?:named?|as)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
                        op_lower,
                    )
                    if folder_match:
                        folder_name = folder_match.group(1).strip()
                        # Get location from command
                        location = self._extract_location_from_command(command)

                        steps.append(
                            ParsedStep(
                                action="create_folder",
                                category="filesystem",
                                params={
                                    "name": folder_name,
                                    "location": location if location else ".",
                                },
                                priority=1,
                            )
                        )
                        context["container_name"] = folder_name
                        context["container_location"] = location
                        continue

                # Operation Type 2: Create N folders with naming pattern
                if re.search(r"create\s+\d+\s+folders?\s+", op_lower):
                    count_match = re.search(r"create\s+(\d+)\s+folders?", op_lower)
                    if count_match:
                        count = int(count_match.group(1))

                        # Extract naming pattern
                        pattern_info = self._extract_naming_pattern(operation)

                        if pattern_info:
                            steps.append(
                                ParsedStep(
                                    action="create_bulk_folders",
                                    category="filesystem",
                                    params={
                                        "count": count,
                                        "naming_pattern": pattern_info,
                                        "parent_folder": context.get("container_name", ""),
                                        "location": context.get("container_location", "."),
                                    },
                                    priority=2,
                                    conditions=["parent_folder_exists"],
                                )
                            )
                            context["current_parent"] = pattern_info.get("prefix", "")
                            context["last_count"] = count

                # Operation Type 3: Among/In those folders, create nested items
                if re.search(r"among\s+those|in\s+each\s+(?:of\s+)?(?:those|the)", op_lower):
                    nested_count_match = re.search(r"create\s+(\d+)\s+folders?", op_lower)
                    if nested_count_match:
                        nested_count = int(nested_count_match.group(1))

                        # Extract nested naming pattern
                        nested_pattern = self._extract_naming_pattern(operation)

                        if nested_pattern:
                            steps.append(
                                ParsedStep(
                                    action="create_nested_folders",
                                    category="filesystem",
                                    params={
                                        "count": nested_count,
                                        "naming_pattern": nested_pattern,
                                        "parent_folders_count": context.get("last_count", 1),
                                        "parent_prefix": context.get("current_parent", ""),
                                        "container": context.get("container_name", ""),
                                    },
                                    priority=3,
                                    conditions=["bulk_folders_created"],
                                )
                            )

            return steps if steps else self._fallback_parse_simple(command, context)

        except Exception:
            return self._fallback_parse_simple(command, context)

    def _split_complex_operations(self, command: str) -> list[str]:
        """Split command into major operations by conjunctions"""
        # Split by 'and' but preserve the operation context
        parts = re.split(r"\s+and\s+", command, flags=re.IGNORECASE)
        return [part.strip() for part in parts if part.strip()]

    def _extract_location_from_command(self, command: str) -> str:
        """Extract the location/path from command"""
        # Match Windows paths
        path_match = re.search(r'(?:at|from|in)\s+([A-Za-z]:\\[^\s"\']+)', command, re.IGNORECASE)
        if path_match:
            return path_match.group(1)
        return ""

    def _extract_naming_pattern(self, operation: str) -> dict[str, Any]:
        """
        Extract naming pattern from operation
        Handles: "naming from test2 to test100", "naming as 1.1 to 1.15", etc.
        """
        pattern_match = re.search(
            r"naming\s+(?:from|as)\s+([a-zA-Z0-9_.]+)\s+to\s+([a-zA-Z0-9_.]+)",
            operation,
            re.IGNORECASE,
        )

        if pattern_match:
            start_val = pattern_match.group(1)
            end_val = pattern_match.group(2)

            # Detect pattern type (numeric, decimal, alphanumeric)
            if re.match(r"^\d+$", start_val) and re.match(r"^\d+$", end_val):
                # Numeric: "1 to 100"
                return {
                    "type": "numeric",
                    "prefix": "",
                    "start": int(start_val),
                    "end": int(end_val),
                }
            elif "." in start_val and "." in end_val:
                # Decimal: "1.1 to 1.15"
                prefix = re.match(r"^(\d+)\.", start_val).group(1)
                start_decimal = int(start_val.split(".")[1])
                end_decimal = int(end_val.split(".")[1])
                return {
                    "type": "decimal",
                    "prefix": prefix,
                    "start": start_decimal,
                    "end": end_decimal,
                    "separator": ".",
                }
            else:
                # Alphanumeric: "test2 to test100"
                # Extract common prefix
                prefix_match = re.match(r"^([a-zA-Z_]+)", start_val)
                if prefix_match:
                    prefix = prefix_match.group(1)
                    start_num = int(re.search(r"\d+", start_val).group())
                    end_num = int(re.search(r"\d+", end_val).group())
                    return {
                        "type": "alphanumeric",
                        "prefix": prefix,
                        "start": start_num,
                        "end": end_num,
                    }

        # Also handle "named X to Y" or plain "X to Y" range without "naming" keyword
        range_match = re.search(
            r"(?:named?\s+|from\s+)?([a-zA-Z0-9_.]+)\s+to\s+([a-zA-Z0-9_.]+)",
            operation,
            re.IGNORECASE,
        )
        if range_match:
            start_val = range_match.group(1)
            end_val = range_match.group(2)
            # Skip pure keyword tokens that aren't valid range bounds
            skip_words = {
                "a",
                "an",
                "the",
                "to",
                "from",
                "in",
                "on",
                "at",
                "of",
                "each",
                "folder",
                "folders",
                "file",
                "files",
            }
            if start_val.lower() not in skip_words and end_val.lower() not in skip_words:
                prefix_match = re.match(r"^([a-zA-Z_]*)", start_val)
                prefix = prefix_match.group(1) if prefix_match else ""
                try:
                    start_num_m = re.search(r"\d+", start_val)
                    end_num_m = re.search(r"\d+", end_val)
                    start_num = int(start_num_m.group()) if start_num_m else 1
                    end_num = int(end_num_m.group()) if end_num_m else start_num
                    return {
                        "type": "alphanumeric" if prefix else "numeric",
                        "prefix": prefix,
                        "start": start_num,
                        "end": end_num,
                    }
                except (ValueError, AttributeError):
                    pass

        return None

    def _extract_items_between_patterns(
        self, command: str, start_pattern: str, end_pattern: str
    ) -> list[str]:
        """Extract items between two regex patterns"""
        match = re.search(
            start_pattern + r"([a-zA-Z0-9_\s]+?)" + end_pattern, command, re.IGNORECASE
        )
        if match:
            return self._parse_item_list(match.group(1))
        return []

    def _parse_item_list(self, items_str: str) -> list[str]:
        """Parse a comma/and-separated list of items intelligently"""
        if not items_str or not items_str.strip():
            return []

        # Replace "and" with delimiter
        items_str = re.sub(r"\s+and\s+", "|", items_str, flags=re.IGNORECASE)
        # Split by whitespace and delimiter, remove articles
        items = re.split(r"[\s|]+", items_str)
        items = [
            item.strip()
            for item in items
            if item.strip() and item.lower() not in ["and", "the", "a", "an"]
        ]
        return items

    def _infer_item_type(self, item: str, items: list[str], command: str) -> str:
        """Infer the type of item (service, test, component, etc.)"""
        # Check for common suffixes
        if item.endswith("_service"):
            return "service"
        elif item.endswith("_tests"):
            return "test"
        elif item.endswith("_folder"):
            return "folder"
        elif item.endswith("_component"):
            return "component"
        else:
            # Use a generic term
            return "folder"

    def _fallback_parse_complex(self, command: str, context: dict[str, Any]) -> list[ParsedStep]:
        """Fallback parser for commands that are too complex"""
        self.logger.warning(
            "Command complexity exceeds supported nesting levels. Creating basic structure."
        )
        steps = []

        # Extract basic container name
        container_match = re.search(
            r"create\s+(?:a\s+)?([a-zA-Z\s]+?)\s+folder", command, re.IGNORECASE
        )
        container_name = container_match.group(1).strip() if container_match else "project"
        container_name = re.sub(
            r"^\s*(?:a|an|the)\s+", "", container_name, flags=re.IGNORECASE
        ).strip()

        # Extract location
        location_match = re.search(
            r'location\s+(?:of\s+the\s+main\s+folder\s+should\s+be\s+)?([A-Za-z]:\\[^\s"\']+)',
            command,
            re.IGNORECASE,
        )
        location = location_match.group(1) if location_match else ""

        # Create container
        steps.append(
            ParsedStep(
                action="create_folder",
                category="filesystem",
                params={"name": container_name, "location": location if location else "."},
                priority=1,
            )
        )

        return steps

    def _fallback_parse_simple(self, command: str, context: dict[str, Any]) -> list[ParsedStep]:
        """Fallback parser for simple commands"""
        steps = []

        container_match = re.search(
            r"create\s+(?:a\s+)?([a-zA-Z\s]+?)\s+folder", command, re.IGNORECASE
        )
        container_name = container_match.group(1).strip() if container_match else "project"

        location_match = re.search(
            r'location\s+(?:of\s+the\s+main\s+folder\s+should\s+be\s+)?([A-Za-z]:\\[^\s"\']+)',
            command,
            re.IGNORECASE,
        )
        location = location_match.group(1) if location_match else ""

        steps.append(
            ParsedStep(
                action="create_folder",
                category="filesystem",
                params={"name": container_name, "location": location if location else "."},
                priority=1,
            )
        )

        return steps

    def _generate_test_config(self) -> str:
        """Generate test configuration file content"""
        return """{
  "test_framework": "pytest",
  "test_runner": "python -m pytest",
  "coverage_enabled": true,
  "min_coverage": 80,
  "parallel_execution": true,
  "timeout_seconds": 300,
  "log_level": "INFO",
  "environment": "test"
}"""

    def _generate_master_registry(
        self, container: str, items: list[str], subitems: list[str]
    ) -> str:
        """Generate master registry file"""
        lines = [
            "=" * 70,
            "MASTER TEST REGISTRY",
            "=" * 70,
            f"Test Framework: {container}",
            f"Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "TEST SUITES:",
            "-" * 70,
        ]

        for item in items:
            lines.append(f"\n[{item.upper()}]")
            lines.append(f"Location: {container}/{item}")
            lines.append(f"Description: {item.replace('_', ' ').title()} tests")

            if subitems:
                lines.append("Subfolders:")
                for subitem in subitems:
                    lines.append(f"  - {subitem}: {subitem.replace('_', ' ').title()}")

        lines.extend(
            [
                "",
                "=" * 70,
                "Configuration: test_config.json",
                "=" * 70,
            ]
        )

        return "\n".join(lines)

    def _parse_nested_command(self, command: str, context: dict[str, Any]) -> list[ParsedStep]:
        """Parse commands with nested operations"""
        # This uses the loop parser since nested operations are usually within loops
        return self._parse_loop_command(command, context)

    def _generate_multiplication_table(self, number: int) -> str:
        """Generate multiplication table for a number"""
        lines = [f"Multiplication Table of {number}", "=" * 40]
        for i in range(1, 11):
            lines.append(f"{number} × {i} = {number * i}")
        return "\n".join(lines)
