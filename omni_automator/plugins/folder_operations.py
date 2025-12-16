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
            'delete_folder_tree'
        ]
    
    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute folder operation"""
        if operation == 'create_bulk_folders':
            return self.create_bulk_folders(params)
        elif operation == 'create_nested_folders':
            return self.create_nested_folders(params)
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
            base_path = params.get('base_path')
            prefix = params.get('folder_prefix', 'folder')
            start = int(params.get('start', 1))
            end = int(params.get('end', 10))
            separator = params.get('separator', '')
            
            if not base_path or not os.path.exists(base_path):
                return {'success': False, 'error': f'Invalid base path: {base_path}'}
            
            created_folders = []
            failed_folders = []
            
            for i in range(start, end + 1):
                folder_name = f"{prefix}{separator}{i}"
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
            base_path = params.get('base_path')
            main_folder = params.get('main_folder', 'main')
            sub_folders = params.get('sub_folders', [])
            
            if not base_path or not os.path.exists(base_path):
                return {'success': False, 'error': f'Invalid base path: {base_path}'}
            
            # Create main folder
            main_path = os.path.join(base_path, main_folder)
            os.makedirs(main_path, exist_ok=True)
            
            created_folders = [main_path]
            failed_folders = []
            
            # Create subfolders
            if isinstance(sub_folders, dict):
                # Pattern-based creation
                prefix = sub_folders.get('prefix', 'folder')
                start = int(sub_folders.get('start', 1))
                end = int(sub_folders.get('end', 10))
                separator = sub_folders.get('separator', '')
                
                for i in range(start, end + 1):
                    subfolder_name = f"{prefix}{separator}{i}"
                    subfolder_path = os.path.join(main_path, subfolder_name)
                    
                    try:
                        os.makedirs(subfolder_path, exist_ok=True)
                        created_folders.append(subfolder_path)
                    except Exception as e:
                        failed_folders.append({'name': subfolder_name, 'error': str(e)})
            else:
                # Direct list of subfolder names
                for subfolder_name in sub_folders:
                    subfolder_path = os.path.join(main_path, subfolder_name)
                    
                    try:
                        os.makedirs(subfolder_path, exist_ok=True)
                        created_folders.append(subfolder_path)
                    except Exception as e:
                        failed_folders.append({'name': subfolder_name, 'error': str(e)})
            
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
            
            if not folder_path or not os.path.exists(folder_path):
                return {'success': False, 'error': f'Folder not found: {folder_path}'}
            
            if not confirm:
                return {'success': False, 'error': 'Deletion requires confirm=True'}
            
            import shutil
            shutil.rmtree(folder_path)
            
            return {
                'success': True,
                'operation': 'delete_folder_tree',
                'deleted_path': folder_path
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
