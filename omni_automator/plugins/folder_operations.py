"""
Folder Operations Plugin
Handles bulk folder creation, deletion, and organization tasks
"""

import os
import shutil
from typing import Any

from omni_automator.core.plugin_manager import AutomationPlugin


class FolderOperations(AutomationPlugin):
    """Handle folder creation and management tasks"""

    @property
    def name(self) -> str:
        return "folder_operations"

    @property
    def description(self) -> str:
        return "Create, delete, and manage folder structures with bulk operations"

    @property
    def version(self) -> str:
        return "1.0.0"

    def get_capabilities(self) -> list[str]:
        return [
            'create_bulk_folders',
            'create_nested_folders',
            'move_folder',
            'move',
            'delete_folder_tree'
        ]

    def execute(self, operation: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute folder operation"""
        if operation == 'create_bulk_folders':
            return self.create_bulk_folders(params)
        elif operation == 'create_nested_folders':
            return self.create_nested_folders(params)
        elif operation in ('move_folder', 'move'):
            return self.move_folder(params)
        elif operation == 'delete_folder_tree':
            return self.delete_folder_tree(params)
        else:
            return {'success': False, 'error': f'Unknown operation: {operation}'}

    def create_bulk_folders(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Create multiple folders with naming pattern
        params:
            base_path / location: root directory for folder creation
            parent_folder: subfolder inside location to create folders in
            folder_prefix: prefix for folder names (optional, defaults to numeric only)
            start: starting number
            end: ending number
        """
        try:
            # Resolve base path: prefer explicit base_path, then location+parent_folder
            base_path = params.get('base_path')
            location = params.get('location', '.')
            parent_folder = params.get('parent_folder') or params.get('parent') or params.get('container')

            if not base_path:
                if parent_folder:
                    # Combine location + parent_folder relative to CWD
                    base_path = os.path.join(os.path.abspath(location), parent_folder)
                else:
                    base_path = os.path.abspath(location)

            # Naming information
            prefix = params.get('folder_prefix', '')
            separator = params.get('separator', '')
            start = None
            end = None

            naming = params.get('naming_pattern') or {}
            if naming:
                prefix = prefix or naming.get('prefix', '')
                separator = separator or naming.get('separator', '')
                if naming.get('type') in ('numeric', 'alphanumeric', 'decimal'):
                    start = int(naming.get('start', 1))
                    end = int(naming.get('end', 10))

            if start is None:
                start = int(params.get('start', params.get('from', 1)))
            if end is None:
                end = int(params.get('end', params.get('to', params.get('count', start))))

            os.makedirs(base_path, exist_ok=True)

            created_folders = []
            failed_folders = []

            for i in range(start, end + 1):
                folder_name = f"{prefix}{separator}{i}" if prefix else str(i)
                folder_path = os.path.join(base_path, folder_name)
                try:
                    os.makedirs(folder_path, exist_ok=True)
                    created_folders.append(folder_path)
                except Exception as e:
                    failed_folders.append({'name': folder_name, 'error': str(e)})

            return {
                'success': True,
                'operation': 'create_bulk_folders',
                'base_path': base_path,
                'total_requested': end - start + 1,
                'created_count': len(created_folders),
                'failed_count': len(failed_folders),
                'created_folders': created_folders,
                'failed_folders': failed_folders
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def create_nested_folders(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Create a main folder with nested subfolders
        params:
            base_path: where to create the main folder
            main_folder: name of main folder
            sub_folders: list of subfolder names OR dict with pattern info
                - If list: create each name directly
                - If dict: create with pattern (prefix, start, end, separator)
        """
        try:
            # Accept parser-style params: location / container / main_folder / nested_in_each
            location = params.get('location', '.')
            parent_folder = params.get('parent_folder') or params.get('container') or params.get('name')
            base_path = params.get('base_path')

            if not base_path:
                base_path = os.path.abspath(location)

            # Handle nested_in_each mode: create N subfolders inside every existing dir in base_path
            nested_in_each = params.get('nested_in_each', False)
            if nested_in_each and parent_folder:
                root = os.path.join(base_path, parent_folder)
            else:
                root = base_path

            if nested_in_each:
                start = int(params.get('start', 1))
                end = int(params.get('end', params.get('count', 10)))
                prefix = params.get('folder_prefix', '')
                created_folders = []
                failed_folders = []
                if os.path.exists(root):
                    parent_dirs = sorted([d for d in os.listdir(root)
                                         if os.path.isdir(os.path.join(root, d))])
                    for pd in parent_dirs:
                        pd_path = os.path.join(root, pd)
                        for i in range(start, end + 1):
                            name = f"{prefix}{i}" if prefix else str(i)
                            p = os.path.join(pd_path, name)
                            try:
                                os.makedirs(p, exist_ok=True)
                                created_folders.append(p)
                            except Exception as e:
                                failed_folders.append({'name': name, 'error': str(e)})
                return {
                    'success': True,
                    'operation': 'create_nested_folders',
                    'total_created': len(created_folders),
                    'failed_count': len(failed_folders),
                    'created_folders': created_folders,
                    'failed_folders': failed_folders
                }

            main_folder = params.get('main_folder') or parent_folder or 'main'
            sub_folders = params.get('sub_folders') or params.get('children') or params.get('nested') or []

            # Create main folder path
            main_path = os.path.join(base_path, main_folder)
            try:
                os.makedirs(main_path, exist_ok=True)
            except Exception as e:
                return {'success': False, 'error': f'Failed to create main folder {main_path}: {e}'}

            created_folders = [main_path]
            failed_folders = []

            # If parser provided parent folder generation info (e.g., parent_prefix + count), handle it
            parent_prefix = params.get('parent_prefix')
            parent_count = int(params.get('parent_folders_count', 0) or params.get('parent_count', 0) or 0)
            parent_list = params.get('parent_folders') or params.get('parents') or []

            parents_to_process = []
            if parent_list:
                parents_to_process = parent_list
            elif parent_prefix and parent_count > 0:
                for i in range(1, parent_count + 1):
                    parents_to_process.append(f"{parent_prefix}{i}")
            else:
                # If no parent info, derive from sub_folders keys if provided as dict mapping
                if isinstance(sub_folders, dict) and 'parent_prefix' in sub_folders:
                    pp = sub_folders.get('parent_prefix')
                    pc = int(sub_folders.get('parent_count', 0) or 0)
                    for i in range(1, pc + 1):
                        parents_to_process.append(f"{pp}{i}")

            # Helper to create pattern-based children
            def create_children_at(path, pattern_info):
                created = []
                failed = []
                if not pattern_info:
                    return created, failed

                if isinstance(pattern_info, dict):
                    pref = pattern_info.get('prefix', '')
                    sep = pattern_info.get('separator', '')
                    start = int(pattern_info.get('start', 1))
                    end = int(pattern_info.get('end', 10))
                    for j in range(start, end + 1):
                        name = f"{pref}{sep}{j}" if pref else f"{j}"
                        p = os.path.join(path, name)
                        try:
                            os.makedirs(p, exist_ok=True)
                            created.append(p)
                        except Exception as e:
                            failed.append({'name': name, 'error': str(e)})
                elif isinstance(pattern_info, list):
                    for name in pattern_info:
                        p = os.path.join(path, name)
                        try:
                            os.makedirs(p, exist_ok=True)
                            created.append(p)
                        except Exception as e:
                            failed.append({'name': name, 'error': str(e)})

                return created, failed

            # If parents_to_process defined, create each parent and its nested children
            if parents_to_process:
                for parent_name in parents_to_process:
                    parent_path = os.path.join(main_path, parent_name)
                    try:
                        os.makedirs(parent_path, exist_ok=True)
                        created_folders.append(parent_path)
                    except Exception as e:
                        failed_folders.append({'name': parent_name, 'error': str(e)})
                        continue

                    # For each parent, create children based on sub_folders pattern
                    if isinstance(sub_folders, dict) and 'children_pattern' in sub_folders:
                        c_pattern = sub_folders.get('children_pattern')
                        c_created, c_failed = create_children_at(parent_path, c_pattern)
                        created_folders.extend(c_created)
                        failed_folders.extend(c_failed)
                    else:
                        c_created, c_failed = create_children_at(parent_path, sub_folders)
                        created_folders.extend(c_created)
                        failed_folders.extend(c_failed)
            else:
                # No parent generation; create subfolders directly under main_path
                c_created, c_failed = create_children_at(main_path, sub_folders)
                created_folders.extend(c_created)
                failed_folders.extend(c_failed)

            return {
                'success': True,
                'operation': 'create_nested_folders',
                'main_folder': main_path,
                'total_created': len(created_folders),
                'failed_count': len(failed_folders),
                'created_folders': created_folders,
                'failed_folders': failed_folders
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def delete_folder_tree(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Delete a folder and all its contents
        params:
            folder_path: path to folder to delete
            confirm: must be True to actually delete
        """
        try:
            folder_path = params.get('folder_path')
            confirm = params.get('confirm', False)
            permanent = params.get('permanent', False) or params.get('force', False)

            if not folder_path or not os.path.exists(folder_path):
                return {'success': False, 'error': f'Folder not found: {folder_path}'}

            if not confirm:
                return {'success': False, 'error': 'Deletion requires confirm=True'}

            # By default, send to recycle bin/trash unless user explicitly requests permanent deletion
            if permanent:
                shutil.rmtree(folder_path)
                return {
                    'success': True,
                    'operation': 'delete_folder_tree',
                    'deleted_path': folder_path,
                    'permanent': True
                }

            # Attempt to move to OS recycle bin using send2trash
            try:
                from send2trash import send2trash
            except Exception:
                return {
                    'success': False,
                    'error': (
                        'send2trash not available. Install it (`pip install send2trash`) to enable safe recycling, '
                        'or set `permanent=True` to force permanent deletion.'
                    )
                }

            try:
                send2trash(folder_path)
                return {
                    'success': True,
                    'operation': 'delete_folder_tree',
                    'moved_to_trash': True,
                    'path': folder_path
                }
            except Exception as e:
                return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def move_folder(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Move a folder from source to destination
        params:
            source / folder_path / folder / name: source folder or name
            from / from_location / src_location: optional source parent folder
            destination / dest / to / location: destination folder or parent
            confirm: optional bool
        """
        try:
            src = params.get('source') or params.get('folder_path') or params.get('folder') or params.get('name')
            src_parent = params.get('from') or params.get('from_location') or params.get('src_location')
            dest = params.get('destination') or params.get('dest') or params.get('to') or params.get('location')

            if not src:
                return {'success': False, 'error': 'Source folder not specified'}

            # If src is a simple name, resolve: try src_parent, then CWD, then Desktop
            if not os.path.isabs(str(src)):
                cwd = os.getcwd()
                home = os.path.expanduser('~')
                desktop = os.path.join(home, 'Desktop')

                if src_parent:
                    candidate = os.path.join(src_parent, src)
                else:
                    candidate = os.path.join(cwd, src)

                if os.path.exists(candidate):
                    src_path = os.path.abspath(candidate)
                else:
                    # try CWD explicitly
                    candidate2 = os.path.join(cwd, src)
                    if os.path.exists(candidate2):
                        src_path = candidate2
                    elif os.path.exists(os.path.join(desktop, src)):
                        src_path = os.path.abspath(os.path.join(desktop, src))
                    else:
                        src_path = os.path.abspath(src)
            else:
                src_path = os.path.abspath(src)

            if not os.path.exists(src_path) or not os.path.isdir(src_path):
                return {'success': False, 'error': f'Source not found or not a folder: {src_path}'}

            # Resolve destination
            if not dest:
                return {'success': False, 'error': 'Destination not specified'}

            # Accept common keywords for destination
            dest_lower = str(dest).lower()
            home = os.path.expanduser('~')
            if 'desktop' in dest_lower:
                dest_root = os.path.join(home, 'Desktop')
            elif 'download' in dest_lower:
                dest_root = os.path.join(home, 'Downloads')
            else:
                # if not absolute, assume relative to home or cwd
                if not os.path.isabs(dest):
                    # prefer Home-based candidate
                    candidate_home = os.path.join(home, dest)
                    if os.path.exists(candidate_home):
                        dest_root = candidate_home
                    else:
                        dest_root = os.path.abspath(dest)
                else:
                    dest_root = os.path.abspath(dest)

            # Ensure destination exists
            try:
                os.makedirs(dest_root, exist_ok=True)
            except Exception:
                return {'success': False, 'error': f'Failed to create destination directory: {dest_root}'}

            # Final move target path: put folder inside dest_root
            target_path = os.path.join(dest_root, os.path.basename(src_path))

            try:
                import shutil
                shutil.move(src_path, target_path)
                return {'success': True, 'source': src_path, 'destination': target_path, 'message': f'Moved {src_path} -> {target_path}'}
            except Exception as e:
                return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': str(e)}
