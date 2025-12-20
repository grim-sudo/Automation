"""Project generator plugin for creating programming projects with templates"""

import os
from typing import Dict, Any, List
import sys

# Ensure the project root is on sys.path so core imports work
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
            'create_virtual_environment',
            'create_java_project',
            'create_web_scraping_project',
            'create_data_analysis_project',
            'create_web_project',
            'create_react_app',
            'create_next_app',
            'create_express_backend',
            'create_c_program',
            'create_hello_world'
        ]

    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute project generation action"""
        try:
            if not isinstance(action, str) or not action:
                raise ValueError("Action must be a non-empty string")
            if not isinstance(params, dict):
                raise ValueError("Params must be a dictionary")

            if action == 'create_c_project':
                return self._create_c_project(params.get('name', 'MyProject'), params.get('location'))
            if action == 'create_virtual_environment':
                return self._create_virtual_environment(params.get('project_path') or params.get('location'), params)
            if action == 'create_c_program':
                return self._create_c_program(params.get('name', 'program.c'), params.get('location'), params.get('program_type', 'addition'))
            if action == 'create_hello_world':
                return self._create_hello_world(params.get('language', 'c'), params.get('name', 'hello'), params.get('location'))
            if action == 'create_python_project':
                return self._create_python_project(params.get('name', 'MyPythonProject'), params.get('location'))
            if action in ('create_web_project', 'create_react_app', 'create_next_app'):
                template = params.get('template', 'react')
                if action == 'create_next_app':
                    template = 'next'
                return self._create_web_project(params.get('name', 'MyWebProject'), params.get('location'), template, params)
            if action == 'create_express_backend':
                return self._create_express_backend(params.get('name', 'MyBackend'), params.get('location'), params)

            raise ValueError(f"Unknown project generator action: {action}")
        except Exception as e:
            raise Exception(f"Project generator execution failed: {e}")

    def _sanitize_name(self, name: str) -> str:
        if not isinstance(name, str):
            return 'unnamed_project'
        invalid_chars = '<>:"/\\|?*'
        for ch in invalid_chars:
            name = name.replace(ch, '_')
        name = name.strip(' .')
        return name or 'unnamed_project'

    def _create_c_project(self, project_name: str, location: str = None) -> Dict[str, Any]:
        try:
            project_name = self._sanitize_name(project_name)
            project_path = (os.path.join(location, project_name) if location else os.path.join(os.path.expanduser('~'), 'Desktop', project_name))
            os.makedirs(project_path, exist_ok=True)
            src_dir = os.path.join(project_path, 'src')
            include_dir = os.path.join(project_path, 'include')
            os.makedirs(src_dir, exist_ok=True)
            os.makedirs(include_dir, exist_ok=True)

            main_c = '''#include <stdio.h>\n\nint main() {\n    printf("Hello, C project!\\n");\n    return 0;\n}\n'''
            main_c_path = os.path.join(src_dir, 'main.c')
            with open(main_c_path, 'w', encoding='utf-8') as f:
                f.write(main_c)

            makefile = 'CC=gcc\\nCFLAGS=-Wall -Wextra -std=c99\\nSRCDIR=src\\nSOURCES=$(wildcard $(SRCDIR)/*.c)\\nTARGET=program\\n\\n$(TARGET): $(SOURCES)\\n\\t$(CC) $(CFLAGS) -o $(TARGET) $(SOURCES)\\n\\nclean:\\n\\trm -f $(TARGET)\\n\\n.PHONY: clean\\n'
            makefile_path = os.path.join(project_path, 'Makefile')
            with open(makefile_path, 'w', encoding='utf-8') as f:
                f.write(makefile)

            readme = f"# {project_name}\\n\\nA simple C project.\\n"
            readme_path = os.path.join(project_path, 'README.md')
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme)

            return {'project_path': project_path, 'files_created': [main_c_path, makefile_path, readme_path], 'message': f'C project "{project_name}" created successfully'}
        except Exception as e:
            raise Exception(f'Failed to create C project: {e}')

    def _create_c_program(self, filename: str, location: str = None, program_type: str = 'addition') -> Dict[str, Any]:
        try:
            if not filename.endswith('.c'):
                filename = filename + '.c'
            filename = self._sanitize_name(filename)
            file_path = os.path.join(location, filename) if location else os.path.join(os.path.expanduser('~'), 'Desktop', filename)
            if program_type == 'addition':
                content = """#include <stdio.h>\n\nint main() {\n    int a = 2;\n    int b = 3;\n    printf("Sum: %d\\n", a + b);\n    return 0;\n}\n"""
            else:
                content = """#include <stdio.h>\n\nint main() {\n    printf("Hello, World!\\n");\n    return 0;\n}\n"""
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {'file_path': file_path, 'message': f'C program "{filename}" created successfully'}
        except Exception as e:
            raise Exception(f'Failed to create C program: {e}')

    def _create_web_project(self, project_name: str, location: str = None, template: str = 'react', params: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            project_name = self._sanitize_name(project_name)
            project_path = os.path.join(location, project_name) if location else os.path.join(os.getcwd(), project_name)
            os.makedirs(project_path, exist_ok=True)
            src_dir = os.path.join(project_path, 'src')
            os.makedirs(src_dir, exist_ok=True)

            package = {
                'name': project_name.lower().replace(' ', '-'),
                'version': '0.1.0',
                'private': True,
                'dependencies': {'react': '^18.0.0', 'react-dom': '^18.0.0'},
                'devDependencies': {'vite': '^4.0.0', '@vitejs/plugin-react': '^3.0.0'},
                'scripts': {'dev': 'vite', 'build': 'vite build', 'preview': 'vite preview'}
            }

            import json as _json
            with open(os.path.join(project_path, 'package.json'), 'w', encoding='utf-8') as f:
                f.write(_json.dumps(package, indent=2))

            index_html = f"""<!doctype html>\n<html>\n  <head>\n    <meta charset=\"utf-8\" />\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\n    <title>{project_name}</title>\n  </head>\n  <body>\n    <div id=\"root\"></div>\n    <script type=\"module\" src=\"/src/main.jsx\"></script>\n  </body>\n</html>\n"""
            with open(os.path.join(project_path, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(index_html)

            main_jsx = """import React from 'react'\nimport { createRoot } from 'react-dom/client'\nimport App from './App'\n\ncreateRoot(document.getElementById('root')).render(<App />)\n"""
            app_jsx = """import React from 'react'\n\nexport default function App() {\n  return (\n    <div>\n      <h1>Welcome to {project_name}</h1>\n      <p>Scaffolded app</p>\n    </div>\n  )\n}\n"""
            with open(os.path.join(src_dir, 'main.jsx'), 'w', encoding='utf-8') as f:
                f.write(main_jsx)
            with open(os.path.join(src_dir, 'App.jsx'), 'w', encoding='utf-8') as f:
                f.write(app_jsx.replace('{project_name}', project_name))

            params = params or {}
            sandbox = params.get('_sandbox', False)
            if params.get('install', False) and not sandbox:
                try:
                    import subprocess
                    subprocess.run(['npm', 'install'], check=True, cwd=project_path)
                except Exception as e:
                    return {'success': False, 'error': f'Install failed: {e}', 'project_path': project_path}

            return {'project_path': project_path, 'files_created': [os.path.join(project_path, 'package.json'), os.path.join(project_path, 'index.html'), os.path.join(src_dir, 'main.jsx'), os.path.join(src_dir, 'App.jsx')], 'message': f'Created web project: {project_name}', 'sandbox': sandbox}
        except Exception as e:
            raise Exception(f'Failed to create web project: {e}')

    def _create_express_backend(self, project_name: str, location: str = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            project_name = self._sanitize_name(project_name)
            project_path = os.path.join(location, project_name) if location else os.path.join(os.getcwd(), project_name)
            os.makedirs(project_path, exist_ok=True)
            src_dir = os.path.join(project_path, 'src')
            os.makedirs(src_dir, exist_ok=True)

            package = {'name': project_name.lower().replace(' ', '-'), 'version': '0.1.0', 'main': 'src/index.js', 'dependencies': {'express': '^4.18.0'}, 'scripts': {'start': 'node src/index.js'}}
            index_js = """const express = require('express')\nconst app = express()\nconst port = process.env.PORT || 3000\n\napp.get('/', (req, res) => {\n  res.send('Hello from Express backend')\n})\n\napp.listen(port, () => console.log(`Server listening on ${port}`))\n"""

            import json as _json
            with open(os.path.join(project_path, 'package.json'), 'w', encoding='utf-8') as f:
                f.write(_json.dumps(package, indent=2))
            with open(os.path.join(src_dir, 'index.js'), 'w', encoding='utf-8') as f:
                f.write(index_js)

            params = params or {}
            sandbox = params.get('_sandbox', False)
            if params.get('install', False) and not sandbox:
                try:
                    import subprocess
                    subprocess.run(['npm', 'install'], check=True, cwd=project_path)
                except Exception as e:
                    return {'success': False, 'error': f'Install failed: {e}', 'project_path': project_path}

            return {'project_path': project_path, 'files_created': [os.path.join(src_dir, 'index.js'), os.path.join(project_path, 'package.json')], 'sandbox': sandbox}
        except Exception as e:
            raise Exception(f'Failed to create express backend: {e}')

    def _create_web_scraping_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            name = params.get('name', 'WebScrapingProject')
            project_name = self._sanitize_name(name)
            location = params.get('location') or os.getcwd()
            project_path = os.path.join(location, project_name)
            os.makedirs(project_path, exist_ok=True)

            scraper_content = (
                "#!/usr/bin/env python3\n"
                "import requests\n"
                "from bs4 import BeautifulSoup\n"
                "import json\n"
                "from datetime import datetime\n\n"
                "def scrape_headlines():\n"
                "    headlines = []\n"
                "    sources = {'BBC':'https://www.bbc.com/news','Reuters':'https://www.reuters.com'}\n"
                "    for source_name, url in sources.items():\n"
                "        try:\n"
                "            r = requests.get(url, timeout=10)\n"
                "            soup = BeautifulSoup(r.content, 'html.parser')\n"
                "            elems = soup.select('h1,h2,h3')[:5]\n"
                "            for e in elems:\n"
                "                t = e.get_text(strip=True)\n"
                "                if len(t) > 20:\n"
                "                    headlines.append({'source': source_name, 'headline': t, 'timestamp': datetime.now().isoformat(), 'url': url})\n"
                "        except Exception:\n"
                "            pass\n"
                "    return headlines\n\n"
                "if __name__ == '__main__':\n"
                "    hs = scrape_headlines()\n"
                "    with open('headlines.json', 'w', encoding='utf-8') as f:\n"
                "        json.dump(hs, f, indent=2, ensure_ascii=False)\n"
            )

            main_path = os.path.join(project_path, 'main.py')
            with open(main_path, 'w', encoding='utf-8') as f:
                f.write(scraper_content)

            requirements_content = 'requests>=2.31.0\nbeautifulsoup4>=4.12.0\nlxml>=4.9.0\n'
            with open(os.path.join(project_path, 'requirements.txt'), 'w', encoding='utf-8') as f:
                f.write(requirements_content)

            readme_content = f"""# {project_name}

A Python web scraping project for collecting news headlines.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Files

- main.py - Main scraper script
- requirements.txt - Python dependencies
- headlines.json - Output file (created after running)
"""
            with open(os.path.join(project_path, 'README.md'), 'w', encoding='utf-8') as f:
                f.write(readme_content)

            return {'project_path': project_path, 'files_created': [main_path, os.path.join(project_path, 'requirements.txt'), os.path.join(project_path, 'README.md')], 'message': f'Created web scraping project: {project_name}'}
        except Exception as e:
            raise Exception(f'Failed to create web scraping project: {e}')

    def _create_data_analysis_project(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            name = params.get('name', 'DataAnalysisProject')
            project_name = self._sanitize_name(name)
            location = params.get('location') or os.getcwd()
            project_path = os.path.join(location, project_name)
            os.makedirs(project_path, exist_ok=True)
            os.makedirs(os.path.join(project_path, 'data'), exist_ok=True)
            os.makedirs(os.path.join(project_path, 'notebooks'), exist_ok=True)
            os.makedirs(os.path.join(project_path, 'src'), exist_ok=True)
            os.makedirs(os.path.join(project_path, 'reports'), exist_ok=True)
            os.makedirs(os.path.join(project_path, 'visualizations'), exist_ok=True)

            # Create a simple notebook JSON
            import json as _json
            notebook_data = {
                "cells": [
                    {"cell_type": "markdown", "metadata": {}, "source": ["# Data Analysis Project\n", "\n", "Comprehensive data analysis with automated report generation"]},
                    {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": ["# Import required libraries\n", "import pandas as pd\n", "import numpy as np\n", "import matplotlib.pyplot as plt\n", "import seaborn as sns\n", "from datetime import datetime\n", "\n", "print('📊 Data Analysis Environment Ready!')"]}
                ],
                "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.8.0"}},
                "nbformat": 4,
                "nbformat_minor": 4
            }

            notebook_content = _json.dumps(notebook_data, indent=1)
            with open(os.path.join(project_path, 'notebooks', 'analysis_notebook.ipynb'), 'w', encoding='utf-8') as f:
                f.write(notebook_content)

            utils_content = '''#!/usr/bin/env python3
"""
Data Analysis Utilities
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import os

class DataAnalyzer:
    def __init__(self, data_path=None):
        self.data_path = data_path
        self.df = None
    
    def load_data(self, file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            self.df = pd.read_csv(file_path)
        elif ext in ['.xlsx', '.xls']:
            self.df = pd.read_excel(file_path)
        elif ext == '.json':
            self.df = pd.read_json(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
        return self.df
'''
            with open(os.path.join(project_path, 'src', 'data_analyzer.py'), 'w', encoding='utf-8') as f:
                f.write(utils_content)

            requirements_content = 'jupyter>=1.0.0\npandas>=2.0.0\nnumpy>=1.24.0\nmatplotlib>=3.7.0\nseaborn>=0.12.0\nscipy>=1.10.0\nopenpyxl>=3.1.0\n'
            with open(os.path.join(project_path, 'requirements.txt'), 'w', encoding='utf-8') as f:
                f.write(requirements_content)

            readme_content = f"""# {project_name}

Comprehensive data analysis project with automated report generation.

See notebooks/analysis_notebook.ipynb for examples.
"""
            with open(os.path.join(project_path, 'README.md'), 'w', encoding='utf-8') as f:
                f.write(readme_content)

            sample_script = '''#!/usr/bin/env python3
"""
Generate sample data for analysis
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_sample_data(n_samples=1000):
    np.random.seed(42)
    start_date = datetime.now() - timedelta(days=n_samples)
    dates = pd.date_range(start_date, periods=n_samples, freq='D')
    data = {
        'date': dates,
        'product': np.random.choice(['Product_A','Product_B','Product_C','Product_D'], n_samples),
        'region': np.random.choice(['North','South','East','West'], n_samples),
        'sales': np.random.normal(1000, 200, n_samples),
        'profit': np.random.normal(150, 50, n_samples),
    }
    df = pd.DataFrame(data)
    df.to_csv('sample_dataset.csv', index=False)

if __name__ == '__main__':
    df = generate_sample_data(1000)
    print('Sample dataset created')
'''
            with open(os.path.join(project_path, 'data', 'generate_sample_data.py'), 'w', encoding='utf-8') as f:
                f.write(sample_script)

            return {'project_path': project_path, 'files_created': [os.path.join(project_path, 'notebooks', 'analysis_notebook.ipynb'), os.path.join(project_path, 'src', 'data_analyzer.py'), os.path.join(project_path, 'requirements.txt')], 'message': f'Created comprehensive data analysis project: {project_name}'}
        except Exception as e:
            raise Exception(f'Failed to create data analysis project: {e}')

    def _create_hello_world(self, language: str, name: str, location: str = None) -> Dict[str, Any]:
        try:
            if not isinstance(language, str) or not language:
                raise ValueError('Language must be a non-empty string')
            if not isinstance(name, str) or not name:
                raise ValueError('Name must be a non-empty string')

            name = self._sanitize_name(name)
            if language.lower() == 'c':
                ext = '.c'
                content = '#include <stdio.h>\\n\\nint main() {\\n    printf("Hello, World!\\\\n");\\n    return 0;\\n}\\n'
            elif language.lower() == 'python':
                ext = '.py'
                content = '#!/usr/bin/env python3\\n\\nprint("Hello, World!")\\n'
            else:
                raise ValueError(f'Unsupported language: {language}')

            filename = name + ext
            file_path = os.path.join(location, filename) if location else os.path.join(os.path.expanduser('~'), 'Desktop', filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return {'file_path': file_path, 'message': f'{language} hello world program "{filename}" created successfully'}
        except Exception as e:
            raise Exception(f'Failed to create hello world program: {e}')

    def _create_python_project(self, project_name: str, location: str = None) -> Dict[str, Any]:
        try:
            project_name = self._sanitize_name(project_name)
            project_path = os.path.join(location, project_name) if location else os.path.join(os.path.expanduser('~'), 'Desktop', project_name)
            os.makedirs(project_path, exist_ok=True)

            main = '#!/usr/bin/env python3\\n\\ndef main():\\n    print("Hello from Python project!")\\n\\nif __name__ == "__main__":\\n    main()\\n'
            main_path = os.path.join(project_path, 'main.py')
            with open(main_path, 'w', encoding='utf-8') as f:
                f.write(main)

            reqs = '# Add your project dependencies here\\n'
            req_path = os.path.join(project_path, 'requirements.txt')
            with open(req_path, 'w', encoding='utf-8') as f:
                f.write(reqs)

            readme = f"# {project_name}\\n\\nA Python project created with OmniAutomator.\\n"
            readme_path = os.path.join(project_path, 'README.md')
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme)

            return {'project_path': project_path, 'files_created': [main_path, req_path, readme_path], 'message': f'Python project "{project_name}" created successfully'}
        except Exception as e:
            raise Exception(f'Failed to create Python project: {e}')

    def _create_virtual_environment(self, project_path: str = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create a virtual environment inside the given project path.

        If `_sandbox` is True in params, do not perform filesystem changes — return a mocked success.
        """
        import venv
        try:
            params = params or {}
            sandbox = params.get('_sandbox', False)
            env_name = params.get('env_name', 'venv')
            if not project_path:
                project_path = params.get('location') or os.path.join(os.path.expanduser('~'), 'Desktop')
            project_path = os.path.abspath(project_path)
            env_path = os.path.join(project_path, env_name)

            if sandbox:
                return {'success': True, 'message': 'Sandbox mode: skipped virtual environment creation', 'env_path': env_path}

            os.makedirs(project_path, exist_ok=True)
            # Create virtual environment
            venv.create(env_path, with_pip=True)
            return {'success': True, 'message': f'Virtual environment created at {env_path}', 'env_path': env_path}
        except Exception as e:
            raise Exception(f'Failed to create virtual environment: {e}')

