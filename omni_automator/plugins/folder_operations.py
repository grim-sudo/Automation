"""
Folder Operations Plugin
Handles bulk folder creation, deletion, and organization tasks
"""

import os
import shutil
from typing import Dict, Any, List
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
    
    def get_capabilities(self) -> List[str]:
        return [
            'create_bulk_folders',
            'create_nested_folders',
            'move_folder',
            'move',
            'delete_folder_tree'
        ]
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
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
    
    def create_bulk_folders(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create multiple folders with naming pattern
        params:
            base_path: where to create folders
            folder_prefix: prefix for folder names
            start: starting number
            end: ending number
            separator: separator between prefix and number (default: '')
        """
        try:
            # Accept multiple param styles: parser may send naming_pattern, parent_folder, location
            base_path = params.get('base_path') or params.get('location')
            # If parser passed a parent folder name, combine with location (desktop fallback)
            parent_folder = params.get('parent_folder') or params.get('parent') or params.get('container')

            if not base_path and parent_folder:
                desktop = os.path.expanduser('~/Desktop')
                base_path = os.path.join(desktop, parent_folder)

            # Naming information: plugin-friendly keys or parser naming_pattern
            prefix = params.get('folder_prefix', '')
            separator = params.get('separator', '')
            start = None
            end = None

            naming = params.get('naming_pattern') or {}
            if naming:
                # naming_pattern may be dict with type/start/end/prefix
                prefix = prefix or naming.get('prefix', '')
                separator = separator or naming.get('separator', '')
                if naming.get('type') in ('numeric', 'alphanumeric', 'decimal'):
                    start = int(naming.get('start', 1))
                    end = int(naming.get('end', 10))

            # Fallback to explicit start/end keys
            if start is None:
                start = int(params.get('start', params.get('from', 1)))
            if end is None:
                end = int(params.get('end', params.get('to', params.get('count', start))))

            # Default prefix when none provided
            if not prefix:
                prefix = params.get('folder_prefix', 'folder')

            if not base_path or not os.path.exists(os.path.dirname(base_path) if parent_folder and not os.path.exists(base_path) else base_path):
                # If base_path doesn't exist, try Desktop as a fallback root
                desktop = os.path.expanduser('~/Desktop')
                if parent_folder:
                    base_path = os.path.join(desktop, parent_folder)
                elif not base_path:
                    return {'success': False, 'error': f'Invalid base path: {base_path}'}
            
            created_folders = []
            failed_folders = []
            
            for i in range(start, end + 1):
                folder_name = f"{prefix}{separator}{i}" if prefix else f"{i}"
                folder_path = os.path.join(base_path, folder_name)
                
                try:
                    os.makedirs(folder_path, exist_ok=True)
                    created_folders.append(folder_path)
                except Exception as e:
                    failed_folders.append({'name': folder_name, 'error': str(e)})
            
            return {
                'success': True,
                'operation': 'create_bulk_folders',
                'total_requested': end - start + 1,
                'created_count': len(created_folders),
                'failed_count': len(failed_folders),
                'created_folders': created_folders,
                'failed_folders': failed_folders
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def create_nested_folders(self, params: Dict[str, Any]) -> Dict[str, Any]:
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
            # Accept parser-style params: location / container / main_folder
            base_path = params.get('base_path') or params.get('location')
            main_folder = params.get('main_folder') or params.get('container') or params.get('name') or 'main'
            # sub_folders may be list of names or dict pattern or nested instructions
            sub_folders = params.get('sub_folders') or params.get('children') or params.get('nested') or []

            # If base_path not provided, try Desktop or current working dir
            if not base_path:
                desktop = os.path.expanduser('~/Desktop')
                base_path = params.get('location') or desktop

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
    
    def delete_folder_tree(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

    def move_folder(self, params: Dict[str, Any]) -> Dict[str, Any]:
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

            # Resolve common names like Desktop/Downloads
            home = os.path.expanduser('~')
            desktop = os.path.join(home, 'Desktop')
            downloads = os.path.join(home, 'Downloads')

            if not src:
                return {'success': False, 'error': 'Source folder not specified'}

            # If src is a simple name, try to resolve with src_parent, Desktop, cwd
            if not os.path.isabs(str(src)):
                candidate = os.path.join(src_parent or desktop, src) if src_parent else os.path.join(desktop, src)
                if os.path.exists(candidate):
                    src_path = os.path.abspath(candidate)
                else:
                    # try cwd
                    candidate2 = os.path.abspath(os.path.join(os.getcwd(), src))
                    if os.path.exists(candidate2):
                        src_path = candidate2
                    else:
                        # last resort: treat src as given (may be absolute)
                        src_path = os.path.abspath(src)
            else:
                src_path = os.path.abspath(src)

            if not os.path.exists(src_path) or not os.path.isdir(src_path):
                return {'success': False, 'error': f'Source not found or not a folder: {src_path}'}

            # Resolve destination
            if not dest:
                return {'success': False, 'error': 'Destination not specified'}

            # Accept common keywords
            dest_lower = str(dest).lower()
            if 'desktop' in dest_lower:
                dest_root = desktop
            elif 'download' in dest_lower:
                dest_root = downloads
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
