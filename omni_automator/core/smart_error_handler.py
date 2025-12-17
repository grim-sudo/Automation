#!/usr/bin/env python3
"""
Smart Error Handler with User Interaction
Handles errors gracefully and prompts user for clarification
"""

import os
import sys
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from ..utils.logger import get_logger


class SmartErrorHandler:
    """Intelligent error handling with user interaction"""
    
    def __init__(self):
        self.logger = get_logger("SmartErrorHandler")
        self.error_history: List[Dict[str, Any]] = []
        self.user_preferences: Dict[str, Any] = {
            'auto_create_paths': True,
            'interactive_mode': True,
            'suggest_alternatives': True
        }
    
    def handle_path_error(self, path: str, context: str = "") -> Optional[str]:
        """
        Handle path errors intelligently
        Asks user if path should be created or corrected
        
        Args:
            path: The invalid path
            context: Context about what was being done
            
        Returns:
            Corrected path or None if user cancels
        """
        self.logger.warning(f"Path error: {path}")
        
        # Check if path exists
        if not os.path.exists(path):
            # Try to suggest similar existing paths
            suggestions = self._suggest_similar_paths(path)
            
            print(f"\n❌ Path not found: {path}")
            if context:
                print(f"   Context: {context}")
            
            print("\nOptions:")
            print(f"1. Create the path: {path}")
            print(f"2. Use current directory: {os.getcwd()}")
            
            if suggestions:
                for i, suggestion in enumerate(suggestions[:3], start=3):
                    print(f"{i}. Use existing path: {suggestion}")
            
            print("4. Enter a custom path")
            print("5. Cancel")
            
            choice = self._get_user_input("Choose an option (1-5): ", valid_options=['1', '2', '3', '4', '5'])
            
            if choice == '1':
                try:
                    os.makedirs(path, exist_ok=True)
                    print(f"✓ Created path: {path}")
                    return path
                except Exception as e:
                    print(f"✗ Failed to create path: {e}")
                    return self.handle_path_error(path, context)
            elif choice == '2':
                return os.getcwd()
            elif choice == '3' and suggestions:
                idx = int(choice) - 3
                if 0 <= idx < len(suggestions):
                    return suggestions[idx]
            elif choice == '4':
                custom_path = input("Enter path: ").strip()
                if custom_path:
                    return self.handle_path_error(custom_path, context)
            else:
                print("Cancelled")
                return None
        
        return path
    
    def handle_file_not_found(self, filename: str) -> Optional[str]:
        """
        Handle file not found errors
        Searches for similar files or asks user
        """
        self.logger.warning(f"File not found: {filename}")
        
        # Try to find similar files
        similar_files = self._find_similar_files(filename)
        
        print(f"\n❌ File not found: {filename}")
        
        if similar_files:
            print("\nDid you mean:")
            for i, file in enumerate(similar_files[:5], start=1):
                print(f"{i}. {file}")
            
            print("6. Enter a different path")
            print("7. Cancel")
            
            choice = self._get_user_input("Choose (1-7): ", valid_options=['1', '2', '3', '4', '5', '6', '7'])
            
            if choice in ['1', '2', '3', '4', '5']:
                idx = int(choice) - 1
                if idx < len(similar_files):
                    return similar_files[idx]
            elif choice == '6':
                return input("Enter file path: ").strip() or None
        else:
            print("\nOptions:")
            print("1. Enter a different path")
            print("2. Cancel")
            
            choice = self._get_user_input("Choose (1-2): ", valid_options=['1', '2'])
            if choice == '1':
                return input("Enter file path: ").strip() or None
        
        return None
    
    def handle_ambiguous_input(self, user_input: str, options: List[str]) -> Optional[str]:
        """
        Handle ambiguous user input
        Presents options for user to choose from
        """
        print(f"\n⚠️  Ambiguous input: '{user_input}'")
        print("\nDid you mean:")
        
        for i, option in enumerate(options[:10], start=1):
            print(f"{i}. {option}")
        
        print(f"{len(options) + 1}. None of the above")
        
        choice = self._get_user_input(f"Choose (1-{len(options) + 1}): ", 
                                      valid_options=[str(i) for i in range(1, len(options) + 2)])
        
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return options[idx]
        
        return None
    
    def handle_missing_parameter(self, parameter: str, expected_type: str = "", context: str = "") -> Optional[str]:
        """
        Handle missing required parameters
        Prompts user to provide the value
        """
        print(f"\n⚠️  Missing required parameter: {parameter}")
        if context:
            print(f"   Context: {context}")
        if expected_type:
            print(f"   Expected type: {expected_type}")
        
        value = input(f"\nProvide {parameter}: ").strip()
        
        if value:
            return value
        else:
            print("❌ Cancelled - required parameter not provided")
            return None
    
    def handle_permission_error(self, path: str) -> bool:
        """
        Handle permission errors
        Offers options to resolve
        """
        self.logger.warning(f"Permission denied: {path}")
        
        print(f"\n❌ Permission denied: {path}")
        print("\nOptions:")
        print("1. Try with elevated privileges (requires restart)")
        print("2. Try alternative location")
        print("3. Cancel")
        
        choice = self._get_user_input("Choose (1-3): ", valid_options=['1', '2', '3'])
        
        if choice == '1':
            print("ℹ️  Restart the application with administrator privileges")
            return False
        elif choice == '2':
            alt_path = input("Enter alternative path: ").strip()
            if alt_path and os.path.exists(os.path.dirname(alt_path)):
                return True
        
        return False
    
    def handle_execution_error(self, error: Exception, context: str = "") -> bool:
        """
        Handle execution errors
        Offers debugging options and recovery
        """
        error_msg = str(error)
        self.logger.error(f"Execution error: {error_msg}")
        self.error_history.append({
            'error': error_msg,
            'context': context,
            'type': type(error).__name__
        })
        
        print(f"\n❌ Error: {error_msg}")
        if context:
            print(f"   Context: {context}")
        
        print("\nOptions:")
        print("1. Retry with same parameters")
        print("2. Skip this step and continue")
        print("3. View error details")
        print("4. Cancel")
        
        choice = self._get_user_input("Choose (1-4): ", valid_options=['1', '2', '3', '4'])
        
        if choice == '1':
            return True  # Signal retry
        elif choice == '3':
            print(f"\nFull error:\n{error}")
            import traceback
            traceback.print_exc()
            return self.handle_execution_error(error, context)
        
        return False
    
    def suggest_correction(self, user_input: str, error_type: str) -> Optional[str]:
        """
        Suggest corrections based on error type
        """
        suggestions = {
            'typo_command': "Did you mean one of these commands?",
            'invalid_path': "The path doesn't exist. Would you like to:",
            'missing_file': "Could not find the file. Would you like to:",
            'syntax_error': "There's a syntax issue. Did you mean:"
        }
        
        message = suggestions.get(error_type, "Would you like to try:")
        print(f"\n💡 {message}")
        
        return None
    
    def confirm_destructive_action(self, action: str, target: str) -> bool:
        """
        Confirm destructive actions like delete
        """
        print(f"\n⚠️  WARNING: {action}")
        print(f"   Target: {target}")
        print("\nThis action cannot be undone!")
        
        confirm = input(f"\nDo you want to proceed? (yes/no): ").strip().lower()
        
        return confirm in ['yes', 'y', 'true']
    
    def _find_similar_files(self, filename: str, search_dir: str = None) -> List[str]:
        """Find files similar to the given filename"""
        if search_dir is None:
            search_dir = os.getcwd()
        
        similar = []
        from difflib import SequenceMatcher
        
        try:
            for root, dirs, files in os.walk(search_dir):
                # Limit depth to avoid long searches
                if root.count(os.sep) - search_dir.count(os.sep) > 3:
                    continue
                
                for file in files:
                    ratio = SequenceMatcher(None, filename.lower(), file.lower()).ratio()
                    if ratio > 0.6:
                        similar.append(os.path.join(root, file))
                
                if len(similar) >= 5:
                    break
        except Exception as e:
            self.logger.debug(f"Error searching for similar files: {e}")
        
        return similar[:5]
    
    def _suggest_similar_paths(self, path: str) -> List[str]:
        """Suggest similar existing paths"""
        suggestions = []
        base_dir = os.path.dirname(path) or os.getcwd()
        
        try:
            # Get parent directory
            parent = os.path.dirname(base_dir)
            if os.path.exists(parent):
                for item in os.listdir(parent):
                    full_path = os.path.join(parent, item)
                    if os.path.isdir(full_path):
                        from difflib import SequenceMatcher
                        ratio = SequenceMatcher(None, base_dir.lower(), full_path.lower()).ratio()
                        if ratio > 0.6:
                            suggestions.append(full_path)
        except Exception as e:
            self.logger.debug(f"Error suggesting paths: {e}")
        
        return suggestions[:3]
    
    def _get_user_input(self, prompt: str, valid_options: List[str] = None) -> str:
        """Get user input with validation"""
        while True:
            try:
                user_input = input(prompt).strip()
                if valid_options and user_input not in valid_options:
                    print(f"Invalid option. Please choose from: {', '.join(valid_options)}")
                    continue
                return user_input
            except KeyboardInterrupt:
                print("\n❌ Cancelled by user")
                return ""
            except Exception as e:
                self.logger.error(f"Input error: {e}")
                continue


# Global instance
_error_handler = None


def get_smart_error_handler() -> SmartErrorHandler:
    """Get or create global error handler instance"""
    global _error_handler
    if _error_handler is None:
        _error_handler = SmartErrorHandler()
    return _error_handler
