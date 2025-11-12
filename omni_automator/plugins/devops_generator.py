"""
DevOps and Infrastructure Generator Plugin
Handles complex DevOps tasks like Docker, Kubernetes, CI/CD pipelines
"""

import os
import json
from typing import Dict, Any, List
from omni_automator.core.plugin_manager import AutomationPlugin


class DevOpsGeneratorPlugin(AutomationPlugin):
    """Plugin for generating DevOps infrastructure and pipelines"""
    
    @property
    def name(self) -> str:
        return "devops_generator"
    
    @property
    def description(self) -> str:
        return "Generate DevOps infrastructure, Docker containers, Kubernetes manifests, and CI/CD pipelines"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def get_capabilities(self) -> List[str]:
        return [
            'create_dockerfile',
            'create_kubernetes_manifest',
            'create_docker_compose',
            'setup_ci_cd_pipeline',
            'create_github_actions',
            'create_jenkins_pipeline',
            'setup_monitoring',
            'create_terraform_config'
        ]
    
    def execute(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute DevOps generation action"""
        try:
            if action == 'create_dockerfile':
                return self._create_dockerfile(params)
            elif action == 'create_kubernetes_manifest':
                return self._create_kubernetes_manifest(params)
            elif action == 'create_docker_compose':
                return self._create_docker_compose(params)
            elif action == 'setup_ci_cd_pipeline':
                return self._setup_ci_cd_pipeline(params)
            elif action == 'create_github_actions':
                return self._create_github_actions(params)
            elif action == 'create_jenkins_pipeline':
                return self._create_jenkins_pipeline(params)
            elif action == 'setup_monitoring':
                return self._setup_monitoring(params)
            elif action == 'create_terraform_config':
                return self._create_terraform_config(params)
            else:
                raise ValueError(f"Unknown DevOps action: {action}")
        except Exception as e:
            raise Exception(f"DevOps generator execution failed: {e}")
    
    def _create_dockerfile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a Dockerfile"""
        app_type = params.get('app_type', 'node')
        location = params.get('location', '.')
        
        dockerfiles = {
            'node': '''FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

USER node

CMD ["npm", "start"]
''',
            'python': '''FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "app.py"]
''',
            'java': '''FROM openjdk:17-jre-slim

WORKDIR /app

COPY target/*.jar app.jar

EXPOSE 8080

CMD ["java", "-jar", "app.jar"]
''',
            'nginx': '''FROM nginx:alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY dist/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
'''
        }
        
        content = dockerfiles.get(app_type, dockerfiles['node'])
        dockerfile_path = os.path.join(location, 'Dockerfile')
        
        os.makedirs(location, exist_ok=True)
        with open(dockerfile_path, 'w') as f:
            f.write(content)
        
        return {
            'file_path': dockerfile_path,
            'message': f'Dockerfile for {app_type} application created successfully'
        }
    
    def _create_kubernetes_manifest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create Kubernetes deployment and service manifests"""
        app_name = params.get('app_name', 'myapp')
        image = params.get('image', f'{app_name}:latest')
        port = params.get('port', 3000)
        replicas = params.get('replicas', 3)
        location = params.get('location', '.')
        
        # Deployment manifest
        deployment = {
            'apiVersion': 'apps/v1',
            'kind': 'Deployment',
            'metadata': {
                'name': f'{app_name}-deployment',
                'labels': {'app': app_name}
            },
            'spec': {
                'replicas': replicas,
                'selector': {'matchLabels': {'app': app_name}},
                'template': {
                    'metadata': {'labels': {'app': app_name}},
                    'spec': {
                        'containers': [{
                            'name': app_name,
                            'image': image,
                            'ports': [{'containerPort': port}],
                            'resources': {
                                'requests': {'memory': '64Mi', 'cpu': '250m'},
                                'limits': {'memory': '128Mi', 'cpu': '500m'}
                            }
                        }]
                    }
                }
            }
        }
        
        # Service manifest
        service = {
            'apiVersion': 'v1',
            'kind': 'Service',
            'metadata': {
                'name': f'{app_name}-service',
                'labels': {'app': app_name}
            },
            'spec': {
                'selector': {'app': app_name},
                'ports': [{
                    'protocol': 'TCP',
                    'port': 80,
                    'targetPort': port
                }],
                'type': 'LoadBalancer'
            }
        }
        
        # Write files
        os.makedirs(location, exist_ok=True)
        
        deployment_path = os.path.join(location, f'{app_name}-deployment.yaml')
        service_path = os.path.join(location, f'{app_name}-service.yaml')
        
        with open(deployment_path, 'w') as f:
            f.write('---\n')
            json.dump(deployment, f, indent=2)
        
        with open(service_path, 'w') as f:
            f.write('---\n')
            json.dump(service, f, indent=2)
        
        return {
            'files_created': [deployment_path, service_path],
            'message': f'Kubernetes manifests for {app_name} created successfully'
        }
    
    def _create_docker_compose(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create Docker Compose configuration"""
        services = params.get('services', ['web', 'database'])
        location = params.get('location', '.')
        
        compose_config = {
            'version': '3.8',
            'services': {}
        }
        
        # Add services based on requirements
        if 'web' in services:
            compose_config['services']['web'] = {
                'build': '.',
                'ports': ['3000:3000'],
                'environment': ['NODE_ENV=production'],
                'depends_on': ['database'] if 'database' in services else []
            }
        
        if 'database' in services:
            compose_config['services']['database'] = {
                'image': 'postgres:15',
                'environment': [
                    'POSTGRES_DB=myapp',
                    'POSTGRES_USER=user',
                    'POSTGRES_PASSWORD=password'
                ],
                'volumes': ['postgres_data:/var/lib/postgresql/data'],
                'ports': ['5432:5432']
            }
        
        if 'redis' in services:
            compose_config['services']['redis'] = {
                'image': 'redis:7-alpine',
                'ports': ['6379:6379']
            }
        
        if 'nginx' in services:
            compose_config['services']['nginx'] = {
                'image': 'nginx:alpine',
                'ports': ['80:80'],
                'volumes': ['./nginx.conf:/etc/nginx/nginx.conf']
            }
        
        # Add volumes if needed
        if 'database' in services:
            compose_config['volumes'] = {'postgres_data': {}}
        
        # Write docker-compose.yml
        os.makedirs(location, exist_ok=True)
        compose_path = os.path.join(location, 'docker-compose.yml')
        
        with open(compose_path, 'w') as f:
            f.write('# Docker Compose Configuration\n')
            json.dump(compose_config, f, indent=2)
        
        return {
            'file_path': compose_path,
            'message': f'Docker Compose configuration with {len(services)} services created successfully'
        }
    
    def _create_github_actions(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create GitHub Actions CI/CD pipeline"""
        app_type = params.get('app_type', 'node')
        location = params.get('location', '.')
        
        workflow = '''name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
    
    - name: Install dependencies
      run: npm ci
    
    - name: Run tests
      run: npm test
    
    - name: Run linting
      run: npm run lint

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: docker build -t myapp:${{ github.sha }} .
    
    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    
    - name: Push Docker image
      run: |
        docker tag myapp:${{ github.sha }} myapp:latest
        docker push myapp:${{ github.sha }}
        docker push myapp:latest
    
    - name: Deploy to Kubernetes
      run: |
        echo "${{ secrets.KUBECONFIG }}" | base64 -d > kubeconfig
        export KUBECONFIG=kubeconfig
        kubectl set image deployment/myapp-deployment myapp=myapp:${{ github.sha }}
        kubectl rollout status deployment/myapp-deployment
'''
        
        # Create .github/workflows directory
        workflows_dir = os.path.join(location, '.github', 'workflows')
        os.makedirs(workflows_dir, exist_ok=True)
        
        workflow_path = os.path.join(workflows_dir, 'ci-cd.yml')
        with open(workflow_path, 'w') as f:
            f.write(workflow)
        
        return {
            'file_path': workflow_path,
            'message': 'GitHub Actions CI/CD pipeline created successfully'
        }
    
    def _setup_monitoring(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Setup monitoring with Prometheus and Grafana"""
        location = params.get('location', '.')
        
        # Prometheus configuration
        prometheus_config = '''global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
  
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
  
  - job_name: 'app'
    static_configs:
      - targets: ['web:3000']
'''
        
        # Docker Compose for monitoring stack
        monitoring_compose = {
            'version': '3.8',
            'services': {
                'prometheus': {
                    'image': 'prom/prometheus:latest',
                    'ports': ['9090:9090'],
                    'volumes': ['./prometheus.yml:/etc/prometheus/prometheus.yml']
                },
                'grafana': {
                    'image': 'grafana/grafana:latest',
                    'ports': ['3001:3000'],
                    'environment': [
                        'GF_SECURITY_ADMIN_PASSWORD=admin'
                    ]
                },
                'node-exporter': {
                    'image': 'prom/node-exporter:latest',
                    'ports': ['9100:9100']
                }
            }
        }
        
        # Write files
        os.makedirs(location, exist_ok=True)
        
        prometheus_path = os.path.join(location, 'prometheus.yml')
        compose_path = os.path.join(location, 'monitoring-compose.yml')
        
        with open(prometheus_path, 'w') as f:
            f.write(prometheus_config)
        
        with open(compose_path, 'w') as f:
            json.dump(monitoring_compose, f, indent=2)
        
        return {
            'files_created': [prometheus_path, compose_path],
            'message': 'Monitoring stack with Prometheus and Grafana created successfully'
        }
