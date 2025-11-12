"""
Project generator plugin for creating programming projects with templates
"""

import os
from typing import Dict, Any, List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omni_automator.core.plugin_manager import AutomationPlugin


class ProjectGeneratorPlugin(AutomationPlugin):
    """Plugin for generating programming projects with templates"""
    
    @property
    def name(self) -> str:
        return "project_generator"
    
    @property
    def description(self) -> str:
        return "Generate programming projects with templates and boilerplate code"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def get_capabilities(self) -> List[str]:
        return [
            'create_c_project',
            'create_python_project',
            'create_java_project',
            'create_web_project',
            'create_c_program',
            'create_hello_world'
        ]
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute project generation action"""
        try:
            # Input validation
            if not isinstance(action, str) or not action:
                raise ValueError("Action must be a non-empty string")
            if not isinstance(params, dict):
                raise ValueError("Params must be a dictionary")
            
            if action == 'create_c_project':
                name = params.get('name', 'MyProject')
                location = params.get('location')
                return self._create_c_project(name, location)
            elif action == 'create_c_program':
                name = params.get('name', 'program.c')
                location = params.get('location')
                program_type = params.get('program_type', 'addition')
                return self._create_c_program(name, location, program_type)
            elif action == 'create_hello_world':
                language = params.get('language', 'c')
                name = params.get('name', 'hello')
                location = params.get('location')
                return self._create_hello_world(language, name, location)
            elif action == 'create_python_project':
                name = params.get('name', 'MyPythonProject')
                location = params.get('location')
                return self._create_python_project(name, location)
            else:
                raise ValueError(f"Unknown project generator action: {action}")
        except Exception as e:
            raise Exception(f"Project generator execution failed: {e}")
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize project/file name"""
        # Remove invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        name = name.strip(' .')
        
        # Ensure name is not empty
        if not name:
            name = 'unnamed_project'
        
        return name
    
    def _create_c_project(self, project_name: str, location: str = None) -> Dict[str, Any]:
        """Create a complete C project structure"""
        try:
            # Input validation
            if not project_name or not isinstance(project_name, str):
                raise ValueError("Project name must be a non-empty string")
            
            # Sanitize project name
            project_name = self._sanitize_name(project_name)
            
            # Determine project path
            if location:
                if not isinstance(location, str):
                    raise ValueError("Location must be a string")
                # Validate location exists or can be created
                if not os.path.exists(location):
                    os.makedirs(location, exist_ok=True)
                project_path = os.path.join(location, project_name)
            else:
                desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                project_path = os.path.join(desktop, project_name)
            
            # Security check
            if '..' in project_path or project_path.startswith('/'):
                raise ValueError("Invalid project path detected")
            
            # Create project directory
            os.makedirs(project_path, exist_ok=True)
            
            # Create subdirectories
            src_dir = os.path.join(project_path, 'src')
            include_dir = os.path.join(project_path, 'include')
            os.makedirs(src_dir, exist_ok=True)
            os.makedirs(include_dir, exist_ok=True)
            
            # Create main.c with addition program
            main_c_content = '''#include <stdio.h>

int main() {
    int num1, num2, sum;
    
    printf("Enter first number: ");
    scanf("%d", &num1);
    
    printf("Enter second number: ");
    scanf("%d", &num2);
    
    sum = num1 + num2;
    
    printf("Sum of %d and %d is: %d\\n", num1, num2, sum);
    
    return 0;
}
'''
            
            main_c_path = os.path.join(src_dir, 'main.c')
            with open(main_c_path, 'w') as f:
                f.write(main_c_content)
            
            # Create Makefile
            makefile_content = '''CC=gcc
CFLAGS=-Wall -Wextra -std=c99
SRCDIR=src
SOURCES=$(wildcard $(SRCDIR)/*.c)
TARGET=program

$(TARGET): $(SOURCES)
\t$(CC) $(CFLAGS) -o $(TARGET) $(SOURCES)

clean:
\trm -f $(TARGET)

.PHONY: clean
'''
            
            makefile_path = os.path.join(project_path, 'Makefile')
            with open(makefile_path, 'w') as f:
                f.write(makefile_content)
            
            # Create README.md
            readme_content = f'''# {project_name}

A simple C program for adding two numbers.

## Compilation

```bash
make
```

## Usage

```bash
./{project_name.lower()}
```

## Files

- `src/main.c` - Main program file
- `Makefile` - Build configuration
'''
            
            readme_path = os.path.join(project_path, 'README.md')
            with open(readme_path, 'w') as f:
                f.write(readme_content)
            
            return {
                'project_path': project_path,
                'files_created': [main_c_path, makefile_path, readme_path],
                'message': f'C project "{project_name}" created successfully'
            }
            
        except Exception as e:
            raise Exception(f"Failed to create C project: {e}")
    
    def _create_c_program(self, filename: str, location: str = None, program_type: str = 'addition') -> Dict[str, Any]:
        """Create a specific C program file"""
        try:
            # Input validation
            if not filename or not isinstance(filename, str):
                raise ValueError("Filename must be a non-empty string")
            
            # Ensure .c extension
            if not filename.endswith('.c'):
                filename += '.c'
            
            # Sanitize filename
            filename = self._sanitize_name(filename)
            
            # Determine file path
            if location:
                if not isinstance(location, str):
                    raise ValueError("Location must be a string")
                if not os.path.exists(location):
                    os.makedirs(location, exist_ok=True)
                file_path = os.path.join(location, filename)
            else:
                desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                file_path = os.path.join(desktop, filename)
            
            # Generate program content based on type
            if program_type == 'addition':
                content = '''#include <stdio.h>

int main() {
    int a = 2;
    int b = 3;
    int sum = a + b;
    
    printf("Addition of %d and %d is: %d\\n", a, b, sum);
    
    return 0;
}
'''
            else:
                content = '''#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}
'''
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                'file_path': file_path,
                'message': f'C program "{filename}" created successfully'
            }
            
        except Exception as e:
            raise Exception(f"Failed to create C program: {e}")
    
    def _create_hello_world(self, language: str, name: str, location: str = None) -> Dict[str, Any]:
        """Create a hello world program in specified language"""
        try:
            # Input validation
            if not isinstance(language, str) or not language:
                raise ValueError("Language must be a non-empty string")
            if not isinstance(name, str) or not name:
                raise ValueError("Name must be a non-empty string")
            
            # Sanitize name
            name = self._sanitize_name(name)
            
            # Language-specific content and extension
            if language.lower() == 'c':
                extension = '.c'
                content = '''#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}
'''
            elif language.lower() == 'python':
                extension = '.py'
                content = '''#!/usr/bin/env python3

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
'''
            else:
                raise ValueError(f"Unsupported language: {language}")
            
            filename = name + extension
            
            # Determine file path
            if location:
                if not isinstance(location, str):
                    raise ValueError("Location must be a string")
                if not os.path.exists(location):
                    os.makedirs(location, exist_ok=True)
                file_path = os.path.join(location, filename)
            else:
                desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                file_path = os.path.join(desktop, filename)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                'file_path': file_path,
                'message': f'{language} hello world program "{filename}" created successfully'
            }
            
        except Exception as e:
            raise Exception(f"Failed to create hello world program: {e}")
    
    def _create_python_project(self, project_name: str, location: str = None) -> Dict[str, Any]:
        """Create a Python project structure"""
        try:
            # Input validation
            if not project_name or not isinstance(project_name, str):
                raise ValueError("Project name must be a non-empty string")
            
            # Sanitize project name
            project_name = self._sanitize_name(project_name)
            
            # Determine project path
            if location:
                if not isinstance(location, str):
                    raise ValueError("Location must be a string")
                if not os.path.exists(location):
                    os.makedirs(location, exist_ok=True)
                project_path = os.path.join(location, project_name)
            else:
                desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
                project_path = os.path.join(desktop, project_name)
            
            # Create project directory
            os.makedirs(project_path, exist_ok=True)
            
            # Create main.py
            main_py_content = '''#!/usr/bin/env python3
"""
Main module for the project
"""

def main():
    """Main function"""
    print("Hello from Python project!")

if __name__ == "__main__":
    main()
'''
            
            main_py_path = os.path.join(project_path, 'main.py')
            with open(main_py_path, 'w', encoding='utf-8') as f:
                f.write(main_py_content)
            
            # Create requirements.txt
            requirements_content = '''# Add your project dependencies here
# Example:
# requests>=2.28.0
# pandas>=1.5.0
'''
            
            requirements_path = os.path.join(project_path, 'requirements.txt')
            with open(requirements_path, 'w', encoding='utf-8') as f:
                f.write(requirements_content)
            
            # Create README.md
            readme_content = f'''# {project_name}

A Python project created with OmniAutomator.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the project:
   ```bash
   python main.py
   ```

## Project Structure

- `main.py` - Main application file
- `requirements.txt` - Project dependencies
- `README.md` - This file
'''
            
            readme_path = os.path.join(project_path, 'README.md')
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            return {
                'project_path': project_path,
                'files_created': [main_py_path, requirements_path, readme_path],
                'message': f'Python project "{project_name}" created successfully'
            }
            
        except Exception as e:
            raise Exception(f"Failed to create Python project: {e}")
