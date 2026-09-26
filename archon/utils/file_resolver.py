"""Shared filesystem path resolution.

Extracted from the duplicate ``_resolve_file_with_disambiguation`` methods that
lived in both :mod:`archon.core.engine` and :mod:`archon.ai.task_executor`.
Behavior is preserved exactly; ``use_icons`` reproduces the two call sites'
only difference (task_executor prefixed log lines with emoji).
"""

from __future__ import annotations

import os

from loguru import logger


def resolve_desktop_path(path: str) -> str:
    """Resolve a path, expanding ``~`` and Desktop references to absolute form.

    Extracted from ``UniversalAutomationPlugin._resolve_path`` so document and
    filesystem capabilities share one implementation.
    """
    if not path:
        return path

    # Expand user home
    path = os.path.expanduser(path)

    # Normalize separators
    path = path.replace("\\", "/")

    # Handle Desktop references
    parts = path.split("/")
    lower_parts = [p.lower() for p in parts]

    if "desktop" in lower_parts:
        idx = lower_parts.index("desktop")
        tail = parts[idx + 1 :] if idx + 1 < len(parts) else []
        home = os.path.expanduser("~")
        path = os.path.join(home, "Desktop", *tail) if tail else os.path.join(home, "Desktop")

    # If not absolute, make it absolute
    if not os.path.isabs(path):
        path = os.path.abspath(path)

    return path


def resolve_file_with_disambiguation(file_name: str, *, use_icons: bool = False) -> str | None:
    """Resolve a file name to a full path.

    Prioritizes the current working directory, then common user directories.
    If several matches exist, prints their context and prompts the user to
    choose (falling back to the first on invalid input or interruption).
    Returns the resolved path, or None if nothing matches.
    """
    # Check current directory first
    if os.path.exists(file_name):
        return os.path.abspath(file_name)

    # Check Desktop
    desktop_path = os.path.expanduser("~/Desktop")
    if os.path.exists(os.path.join(desktop_path, file_name)):
        return os.path.join(desktop_path, file_name)

    # Search user project directories (limited depth, prioritize current dir)
    user_search_paths = [
        os.getcwd(),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Projects"),
    ]

    found_files: list[str] = []
    found_files_set: set[str] = set()
    current_dir = os.getcwd()

    for search_path in user_search_paths:
        if not os.path.exists(search_path):
            continue
        for root, _dirs, files in os.walk(search_path):
            # Limit depth to 5 levels for user directories
            depth = root.replace(search_path, "").count(os.sep)
            if depth > 5:
                continue
            # Skip system directories
            if any(
                skip in root.lower()
                for skip in ["appdata", "roaming", "site-packages", "dist-packages"]
            ):
                continue

            if file_name in files:
                full_path = os.path.abspath(os.path.join(root, file_name))
                if full_path not in found_files_set:
                    found_files.append(full_path)
                    found_files_set.add(full_path)

    if not found_files:
        return None

    if len(found_files) == 1:
        return found_files[0]

    # Multiple matches — show context and prompt.
    in_project_icon = "📁 " if use_icons else ""
    desktop_icon = "🖥️  " if use_icons else ""
    other_icon = "📂 " if use_icons else ""

    logger.warning(f"Multiple files named '{file_name}' found:")
    logger.info(f"Current working directory: {current_dir}")

    for idx, path in enumerate(found_files, 1):
        abs_path = os.path.abspath(path)

        if abs_path.startswith(current_dir):
            folder_context = (
                f"{in_project_icon}[IN PROJECT] "
                f"{os.path.dirname(os.path.relpath(abs_path, current_dir))}"
            )
        elif abs_path.startswith(desktop_path):
            folder_context = f"{desktop_icon}[ON DESKTOP]"
        else:
            folder_context = f"{other_icon}{os.path.dirname(abs_path)}"

        try:
            file_stat = os.stat(abs_path)
            size_kb = file_stat.st_size / 1024
            size_str = f"{size_kb:.1f}KB" if size_kb < 1024 else f"{size_kb / 1024:.1f}MB"
        except Exception:
            size_str = "?"

        logger.info(f"  {idx}. {folder_context}")
        logger.info(f"      Full path: {abs_path}")
        logger.info(f"      Size: {size_str}")

    try:
        choice = input(f"Enter the number of the file to use (1-{len(found_files)}): ").strip()
        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(found_files):
            selected_file = found_files[choice_idx]
            logger.info(f"Selected: {selected_file}")
            return selected_file
        logger.warning("Invalid choice. Using first option.")
        return found_files[0]
    except (ValueError, KeyboardInterrupt):
        logger.info(f"Using first option: {found_files[0]}")
        return found_files[0]
