# OmniAutomator — Complete Task Reference

Every example below runs as `python omni.py run "..."`, inside `omni chatbot`, or as a line in a batch file.

> **Typos are auto-corrected.** "creat a fodler" → "create a folder" — you don't have to be exact.

---

## Table of Contents

1. [Folder operations](#folder-operations)
2. [File operations](#file-operations)
3. [Bulk and numbered creation](#bulk-and-numbered-creation)
4. [Copy and move](#copy-and-move)
5. [Rename and reorganise](#rename-and-reorganise)
6. [Find and list](#find-and-list)
7. [System information](#system-information)
8. [Process management](#process-management)
9. [Service management](#service-management)
10. [User and permission management](#user-and-permission-management)
11. [Package management](#package-management)
12. [Project generation](#project-generation)
13. [Document generation](#document-generation)
14. [DevOps and infrastructure](#devops-and-infrastructure)
15. [Cloud deployment](#cloud-deployment)
16. [Browser automation](#browser-automation)
17. [Web scraping](#web-scraping)
18. [File downloads and networking](#file-downloads-and-networking)
19. [Screenshots and UI control](#screenshots-and-ui-control)
20. [Security operations](#security-operations)
21. [Data and analytics](#data-and-analytics)
22. [n8n workflows](#n8n-workflows)
23. [Custom Linux distro builder](#custom-linux-distro-builder)
24. [Batch file patterns](#batch-file-patterns)
25. [Chatbot / multi-turn mode](#chatbot--multi-turn-mode)
26. [Global flags reference](#global-flags-reference)
27. [Spell correction examples](#spell-correction-examples)
28. [Tips](#tips)

---

## Folder operations

### Create a single folder

```bash
python omni.py run "create a folder named reports"
python omni.py run "create a folder called archive in ~/Documents"
python omni.py run "make a directory named logs in /var/app"
python omni.py run "create folder projects/web on the Desktop"
python omni.py run "mkdir /tmp/workspace"
```

### Create nested folders

```bash
python omni.py run "create a folder named app with subfolders src, tests, and docs"
python omni.py run "create nested folders: project/src/components and project/src/utils"
python omni.py run "create folder structure api/v1/routes and api/v1/models"
python omni.py run "create project layout with folders frontend, backend, and shared"
```

### Delete a folder

```bash
python omni.py run "delete the folder named reports"
python omni.py run "remove folder archive from ~/Documents"
python omni.py run "delete folder old_logs and all its contents"
python omni.py run "permanently delete the build folder"
```

```bash
# Always safe to add --safe-mode for deletions
python omni.py run "delete folder archive" --safe-mode
```

### Move a folder

```bash
python omni.py run "move folder old_project to ~/archive"
python omni.py run "move src to ~/Projects/myapp/src"
python omni.py run "move the folder downloads to /mnt/storage/downloads"
```

---

## File operations

### Create a file

```bash
python omni.py run "create an empty file named notes.txt in ~/Documents"
python omni.py run "create a file called config.json with empty content"
python omni.py run "create a Python script named hello.py"
python omni.py run "create a shell script named deploy.sh in ~/scripts"
python omni.py run "create a Markdown file named README.md in the current folder"
```

### Delete a file

```bash
python omni.py run "delete the file notes.txt in ~/Documents"
python omni.py run "remove file old_config.json"
python omni.py run "delete all .log files in /var/log/myapp"
python omni.py run "delete all temporary files in ~/Downloads"
python omni.py run "remove all .DS_Store files from ~/Projects"
```

### Delete files by age

```bash
python omni.py run "delete all files older than 30 days in ~/Downloads"
python omni.py run "remove files modified more than 7 days ago in /tmp"
python omni.py run "clean up log files older than 90 days in /var/log"
```

### Delete files by type

```bash
python omni.py run "delete all .pyc files in the project"
python omni.py run "delete all .tmp and .bak files in ~/Documents"
python omni.py run "remove all compiled object files in ~/Projects/myapp"
```

### Write content to a file

```bash
python omni.py run "write 'Hello, World!' to a file named greeting.txt"
python omni.py run "append today's date to a log file named activity.log"
python omni.py run "create a file named .gitignore with standard Python ignores"
```

---

## Bulk and numbered creation

### Create numbered folders

```bash
python omni.py run "create 10 folders named folder1 through folder10"
python omni.py run "create 50 folders from test1 to test50 in ~/experiments"
python omni.py run "create 5 folders named project_1 through project_5 on the Desktop"
python omni.py run "create 100 folders named client001 through client100"
```

### Create numbered files

```bash
python omni.py run "create 20 empty text files named note1.txt through note20.txt"
python omni.py run "create 5 Python scripts named script_1.py through script_5.py"
python omni.py run "create 12 markdown files named month_01.md through month_12.md"
```

### Create folders with nested structure

```bash
python omni.py run "create 3 project folders each with src, tests, and docs subfolders"
python omni.py run "create 10 folders named client1 through client10, each with invoices and contracts subfolders"
python omni.py run "create 5 folders named week1 to week5, each containing a notes and tasks subfolder"
```

### Create with date-based names

```bash
python omni.py run "create folders named report_2024_01 through report_2024_12"
python omni.py run "create folders named week_01 through week_52 inside ~/planning"
```

---

## Copy and move

### Copy a file

```bash
python omni.py run "copy file report.pdf to ~/archive"
python omni.py run "copy notes.txt to /tmp/notes_backup.txt"
python omni.py run "duplicate config.json as config.backup.json"
```

### Copy a folder

```bash
python omni.py run "copy folder src to src_backup"
python omni.py run "copy folder ~/Projects/myapp to ~/Projects/myapp_backup"
python omni.py run "copy the docs folder to ~/Documents/project_docs"
```

### Copy all files of a type

```bash
python omni.py run "copy all PDF files from ~/Documents to ~/archive/pdfs"
python omni.py run "copy all images from ~/Downloads to ~/Pictures/new"
python omni.py run "copy all .py files to ~/code_backup"
python omni.py run "copy every .csv file in ~/data to ~/data/backup"
```

### Move files and folders

```bash
python omni.py run "move report.pdf to ~/archive"
python omni.py run "move all .log files from /var/app to /var/app/logs"
python omni.py run "move the file notes.txt to ~/Documents/notes"
python omni.py run "move folder old_project to ~/archive"
python omni.py run "move all zip files in ~/Downloads to ~/archive/zips"
```

---

## Rename and reorganise

### Rename a file or folder

```bash
python omni.py run "rename file report.pdf to quarterly_report_Q1.pdf"
python omni.py run "rename notes.txt to meeting_notes_2024.txt"
python omni.py run "rename folder old_name to new_name"
python omni.py run "rename directory src to source"
```

### Batch rename

```bash
python omni.py run "rename all .jpeg files to .jpg in ~/Pictures"
python omni.py run "rename all files in ~/exported by adding the prefix 2024_ to each"
python omni.py run "rename all .txt files to .md in ~/notes"
python omni.py run "lowercase all filenames in ~/downloads"
```

### Organise files into subfolders

```bash
python omni.py run "move all PDF files into a subfolder called pdfs"
python omni.py run "sort files in ~/Downloads into folders by extension"
python omni.py run "organise photos in ~/Pictures by year and month"
python omni.py run "group all Python files in ~/scripts into a src folder"
```

---

## Find and list

### List files and folders

```bash
python omni.py run "list all files in ~/Documents"
python omni.py run "show files in the current directory"
python omni.py run "list all Python files in ~/Projects"
python omni.py run "show all .log files in /var/log"
python omni.py run "list folders in ~/Projects sorted by date"
```

### Find files

```bash
python omni.py run "find all PDF files in ~/Documents"
python omni.py run "find files larger than 100MB in ~/Downloads"
python omni.py run "find all files modified in the last 24 hours in ~/Projects"
python omni.py run "find all empty folders in ~/Projects"
python omni.py run "find all files named config.json under ~/Projects"
```

### Check existence and size

```bash
python omni.py run "check if the folder reports exists in ~/Documents"
python omni.py run "verify that config.toml exists in the current directory"
python omni.py run "show the size of the folder ~/Projects/myapp"
python omni.py run "what is the total size of all files in ~/Downloads"
```

---

## System information

### Disk usage

```bash
python omni.py run "show disk usage on /"
python omni.py run "check how much space is available on /home"
python omni.py run "show disk usage for all mounted drives"
python omni.py run "which directories are using the most space in /var"
python omni.py run "check disk space on all partitions"
```

### Memory and CPU

```bash
python omni.py run "show current memory usage"
python omni.py run "how much RAM is being used"
python omni.py run "show CPU usage"
python omni.py run "display system resource summary"
python omni.py run "what percentage of RAM is free"
```

### OS and hardware

```bash
python omni.py run "show OS version"
python omni.py run "what kernel version is running"
python omni.py run "show hostname and IP addresses"
python omni.py run "display system uptime"
python omni.py run "show CPU model and core count"
python omni.py run "list all network interfaces"
```

---

## Process management

### List processes

```bash
python omni.py run "show all running processes"
python omni.py run "list processes sorted by CPU usage"
python omni.py run "show processes using the most memory"
python omni.py run "find processes named nginx"
python omni.py run "show the top 10 processes by memory"
```

### Kill processes

```bash
python omni.py run "kill process named firefox" --safe-mode
python omni.py run "stop all processes matching python" --safe-mode
python omni.py run "kill the process with PID 1234" --safe-mode
python omni.py run "force-kill all zombie processes" --safe-mode
```

> Always use `--safe-mode` when killing processes to get a confirmation prompt before anything is terminated.

---

## Service management

### Start, stop, restart services

```bash
python omni.py run "start the nginx service"
python omni.py run "stop the postgresql service"
python omni.py run "restart the application service"
python omni.py run "reload the nginx configuration"
python omni.py run "restart all failed services"
```

### Enable and disable on boot

```bash
python omni.py run "enable nginx to start on boot"
python omni.py run "disable the bluetooth service"
python omni.py run "enable postgresql at startup"
```

### Check service status

```bash
python omni.py run "check the status of the nginx service"
python omni.py run "is postgresql running"
python omni.py run "show all failed systemd services"
python omni.py run "list all enabled services"
```

---

## User and permission management

### User accounts

```bash
python omni.py run "create a user named deploy with a home directory"
python omni.py run "add user deploy to the sudo group"
python omni.py run "remove user old_account"
python omni.py run "list all system users"
python omni.py run "show which groups user deploy belongs to"
```

### File permissions

```bash
python omni.py run "set permissions on ~/scripts/deploy.sh to executable"
python omni.py run "make all .sh files in ~/scripts executable"
python omni.py run "set the folder ~/app to be owned by the www-data user"
python omni.py run "give read and write permissions to ~/shared to all users"
python omni.py run "recursively set correct permissions on /var/www/html"
```

### Scheduled tasks (cron)

```bash
python omni.py run "schedule a task to run backup.sh every day at 3am"
python omni.py run "add a cron job to delete /tmp files every Sunday at midnight"
python omni.py run "schedule cleanup.py to run at 2am on the first of every month"
python omni.py run "list all scheduled cron jobs"
```

---

## Package management

### Install packages

```bash
python omni.py run "install package vim"
python omni.py run "install nginx and curl"
python omni.py run "install Python packages requests, httpx, and pydantic"
python omni.py run "install npm package express"
python omni.py run "install the latest version of git"
python omni.py run "install docker"
```

### Search and list

```bash
python omni.py run "search for packages matching http client"
python omni.py run "search for python packages matching async"
python omni.py run "list all installed packages"
python omni.py run "list all Python packages installed in this environment"
python omni.py run "check if nginx is installed"
```

### Uninstall and update

```bash
python omni.py run "uninstall package vim"
python omni.py run "remove nginx and purge its config files"
python omni.py run "update all system packages"
python omni.py run "upgrade pip to the latest version"
python omni.py run "update only security packages"
```

---

## Project generation

### Python

```bash
python omni.py run "create a Python project named myapi"
python omni.py run "generate a Python project with Flask and PostgreSQL"
python omni.py run "create a FastAPI project with JWT auth and Docker support"
python omni.py run "setup a Django project with REST framework"
python omni.py run "create a Python package with tests, CI, and a README"
python omni.py run "generate a Python CLI tool named myscript"
```

### Python virtual environment

```bash
python omni.py run "create a virtual environment in ~/Projects/myapp"
python omni.py run "setup a venv named .venv in the current directory"
python omni.py run "create a virtualenv and install requirements.txt"
```

### C and C++

```bash
python omni.py run "create a C project named calculator"
python omni.py run "generate a C program named sorter that sorts an array"
python omni.py run "create a C hello world program"
python omni.py run "create a C++ project named image-processor with CMake"
```

### Java

```bash
python omni.py run "create a Java project named inventory-system"
python omni.py run "generate a Java Maven project named backend-api"
python omni.py run "create a Spring Boot project named user-service"
```

### Hello World in any language

```bash
python omni.py run "create a hello world program in Python"
python omni.py run "create a hello world program in C"
python omni.py run "create a hello world program in Go"
python omni.py run "generate a hello world in Rust"
python omni.py run "create a hello world in JavaScript"
```

### Node.js / JavaScript / TypeScript

```bash
python omni.py run "create a Node.js Express API server"
python omni.py run "generate a React app named my-dashboard"
python omni.py run "create a React application with TypeScript and Jest"
python omni.py run "setup a Next.js project with TailwindCSS"
python omni.py run "create a Vue 3 project with Vite"
python omni.py run "generate a Node.js CLI tool"
```

### Data science and analysis

```bash
python omni.py run "create a data analysis project with pandas and matplotlib"
python omni.py run "generate a machine learning project with scikit-learn"
python omni.py run "create a Jupyter notebook project for EDA"
python omni.py run "setup a data science environment with numpy, pandas, and seaborn"
```

### Web scraping

```bash
python omni.py run "create a web scraping project using BeautifulSoup"
python omni.py run "generate a Scrapy project for crawling product pages"
python omni.py run "create a scraper project with Playwright and Python"
```

### With specific features

```bash
python omni.py run "create a Python project with Redis caching, Celery workers, and Docker Compose"
python omni.py run "generate a REST API with OpenAPI docs, database migrations, and pytest"
python omni.py run "create a full-stack project with React frontend and FastAPI backend"
```

---

## Document generation

> Requires core dependencies (`python-docx`, `python-pptx`, `openpyxl`, `reportlab` — all included in the base install).

### Word documents (.docx)

```bash
python omni.py run "create a Word document named quarterly-report.docx"
python omni.py run "generate a Word document named meeting-agenda.docx with a title and bullet points"
python omni.py run "create a Word document named proposal with an introduction and three sections"
python omni.py run "write a Word document named contract.docx in ~/Documents"
python omni.py run "generate a formatted Word report with headings and a table"
```

### PowerPoint presentations (.pptx)

```bash
python omni.py run "create a PowerPoint presentation about AI trends"
python omni.py run "generate a 5-slide presentation named company-intro.pptx"
python omni.py run "create a PowerPoint deck with a title slide and 4 content slides"
python omni.py run "make a presentation named sales-q1.pptx with charts and bullet points"
python omni.py run "generate a product pitch deck in PowerPoint format"
```

### Excel spreadsheets (.xlsx)

```bash
python omni.py run "create an Excel spreadsheet with columns for name, date, and amount"
python omni.py run "generate an Excel file named sales-data.xlsx with sample rows"
python omni.py run "create a budget spreadsheet with income and expense columns"
python omni.py run "make an Excel worksheet with a header row and 10 data rows"
python omni.py run "create an Excel report with summary and detail sheets"
python omni.py run "generate a timesheet template in Excel format"
```

### PDF documents

```bash
python omni.py run "generate a PDF invoice named invoice-001.pdf"
python omni.py run "create a PDF report with a title and three sections"
python omni.py run "generate a PDF resume template"
python omni.py run "create a PDF with a cover page and table of contents"
```

### Save content to a document

```bash
python omni.py run "save the text 'Project started on 2024-01-01' to a Word document named project-log.docx"
python omni.py run "append a new row containing 'Alice, 2024-03, 5000' to sales.xlsx"
python omni.py run "write the system info output to a Word document named system-report.docx"
```

---

## DevOps and infrastructure

### Docker

```bash
python omni.py run "create a Dockerfile for my Python Flask app"
python omni.py run "create a Dockerfile for a Node.js application"
python omni.py run "generate a multi-stage Dockerfile for a Go binary"
python omni.py run "create a Dockerfile that runs a FastAPI app on port 8000"
```

### Docker Compose

```bash
python omni.py run "generate a docker-compose.yml with nginx, postgres, and redis"
python omni.py run "create a docker-compose.yml with a web service and a PostgreSQL database"
python omni.py run "add a Redis cache service to my docker-compose.yml"
python omni.py run "create a docker-compose file for a full-stack app with a React frontend and a Node backend"
```

### Kubernetes

```bash
python omni.py run "create a Kubernetes deployment YAML for my API service"
python omni.py run "generate a Kubernetes service and ingress for my web app"
python omni.py run "create a Kubernetes deployment with resource limits and readiness probes"
python omni.py run "generate a Kubernetes ConfigMap and Secret for my app"
python omni.py run "create a Helm chart for my microservice"
```

### CI/CD pipelines

```bash
python omni.py run "configure a GitHub Actions CI pipeline for a Python project"
python omni.py run "create a GitHub Actions workflow that runs tests on every push"
python omni.py run "generate a GitLab CI pipeline with build, test, and deploy stages"
python omni.py run "create a Jenkins pipeline for my Node.js app"
python omni.py run "setup automated deployment to AWS on tag push using GitHub Actions"
```

### Terraform

```bash
python omni.py run "generate Terraform config for an AWS EC2 instance"
python omni.py run "create a Terraform file for an S3 bucket with versioning enabled"
python omni.py run "generate Terraform config for a GCP Cloud Run service"
python omni.py run "create a Terraform module for a VPC with public and private subnets"
```

### Monitoring

```bash
python omni.py run "setup monitoring for my web application"
python omni.py run "configure Prometheus and Grafana for my services"
python omni.py run "create a health check script for my API endpoints"
python omni.py run "setup log aggregation with the ELK stack"
python omni.py run "generate alerting rules for high CPU and memory usage"
```

### Deploy and release

```bash
python omni.py run "deploy the app"
python omni.py run "release version 1.2.0"
python omni.py run "publish the package to PyPI"
python omni.py run "ship the latest build to production"
python omni.py run "deploy the Docker image to the staging environment"
```

---

## Cloud deployment

### AWS

```bash
python omni.py run "deploy the app to AWS"
python omni.py run "deploy to AWS Elastic Beanstalk"
python omni.py run "push the Docker image to AWS ECR"
python omni.py run "create an S3 bucket named my-artifacts and upload the build"
python omni.py run "deploy a Lambda function from lambda.zip"
```

### Google Cloud

```bash
python omni.py run "deploy the application to GCP"
python omni.py run "push the image to Google Container Registry"
python omni.py run "deploy to Cloud Run with 2 replicas"
python omni.py run "upload build artifacts to Google Cloud Storage"
```

### Azure

```bash
python omni.py run "deploy the app to Azure"
python omni.py run "push the Docker image to Azure Container Registry"
python omni.py run "deploy to Azure App Service"
```

### Heroku

```bash
python omni.py run "deploy the app to Heroku"
python omni.py run "create a new Heroku app named my-service"
python omni.py run "scale the Heroku web dyno to 2"
python omni.py run "set the Heroku environment variable DATABASE_URL"
```

---

## Browser automation

> Requires `[web]` extras: `pip install -e ".[web]"` (Selenium + Playwright).

### Open and navigate

```bash
python omni.py run "open https://example.com in a browser"
python omni.py run "navigate to https://myapp.local/dashboard"
python omni.py run "open https://example.com in headless Chrome"
```

### Interact with page elements

```bash
python omni.py run "click the button with text 'Submit' on https://example.com/form"
python omni.py run "fill in the username field on the login page with 'admin'"
python omni.py run "type 'search query' into the search box on https://example.com"
python omni.py run "click the first link in the navigation menu"
python omni.py run "check the checkbox labelled 'Accept terms'"
python omni.py run "select 'Option 2' from the dropdown menu"
```

### Take screenshots

```bash
python omni.py run "open https://example.com and take a screenshot"
python omni.py run "take a screenshot of https://myapp.local/dashboard and save as dashboard.png"
python omni.py run "capture the full-page screenshot of https://example.com"
```

### Fill and submit forms

```bash
python omni.py run "fill in the login form at https://myapp.local with username admin and password secret"
python omni.py run "submit the contact form at https://example.com with name Alice and email alice@example.com"
python omni.py run "fill out and submit the registration form at https://example.com/signup"
```

### Close browser

```bash
python omni.py run "close the browser"
python omni.py run "close all open browser windows"
```

---

## Web scraping

> Requires `beautifulsoup4` (included in base dependencies) and optionally `[web]` for JavaScript-rendered sites.

### Scrape a full page

```bash
python omni.py run "scrape https://example.com and save the content"
python omni.py run "scrape all text from https://example.com/article"
python omni.py run "extract the main article text from https://news.example.com/story"
```

### Extract links

```bash
python omni.py run "extract all links from https://example.com"
python omni.py run "get all href links on https://example.com/resources"
python omni.py run "find all external links on https://example.com"
python omni.py run "list all PDF links on https://example.com/downloads"
```

### Extract images

```bash
python omni.py run "extract all images from https://example.com"
python omni.py run "get all image URLs from https://example.com/gallery"
python omni.py run "download all images from the page at https://example.com/photos"
```

### Extract tables

```bash
python omni.py run "scrape the first table from https://example.com/data"
python omni.py run "extract all tables from https://example.com/stats and save as CSV"
python omni.py run "get the pricing table from https://example.com/pricing"
```

### Search and extract

```bash
python omni.py run "search example.com for 'python tutorial' and extract the first 5 results"
python omni.py run "find all articles tagged 'automation' on https://example.com/blog"
python omni.py run "scrape product names and prices from https://shop.example.com"
```

### Extract article content

```bash
python omni.py run "extract the article text from https://example.com/post/123"
python omni.py run "get the title, author, and body from https://blog.example.com/post"
python omni.py run "extract and clean the article at https://news.example.com"
```

---

## File downloads and networking

### Download files

```bash
python omni.py run "download https://example.com/file.zip to ~/Downloads"
python omni.py run "fetch the file at https://example.com/data.csv and save to ~/data"
python omni.py run "download the latest release from https://example.com/releases/latest"
```

### Check connectivity

```bash
python omni.py run "check if google.com is reachable"
python omni.py run "ping 8.8.8.8 and show the result"
python omni.py run "test the connection to https://api.example.com/health"
python omni.py run "check if port 5432 is open on localhost"
```

### API testing

```bash
python omni.py run "test the GET endpoint https://api.example.com/users and show the response"
python omni.py run "send a POST request to https://api.example.com/auth with username and password"
python omni.py run "check the response time of https://api.example.com/health"
```

---

## Screenshots and UI control

### Take a screenshot

```bash
python omni.py run "take a screenshot and save to ~/screenshots/now.png"
python omni.py run "take a screenshot of the current screen"
python omni.py run "capture the screen and save as screenshot.png on the Desktop"
```

### UI interaction (desktop)

```bash
python omni.py run "click at position 100, 200 on the screen"
python omni.py run "type 'hello world' into the currently focused window"
python omni.py run "press the Enter key"
python omni.py run "scroll down on the current window"
```

> Requires `[gui]` extras: `pip install -e ".[gui]"`. On headless Linux, set `DISPLAY` first.

---

## Security operations

### Vulnerability scanning

```bash
python omni.py run "run a security scan on the current project"
python omni.py run "scan for vulnerabilities in my Python dependencies"
python omni.py run "check for known CVEs in requirements.txt"
python omni.py run "run a vulnerability assessment on the application"
```

### SSL and certificates

```bash
python omni.py run "setup SSL for my domain example.com"
python omni.py run "generate a self-signed SSL certificate for localhost"
python omni.py run "check when the SSL certificate for example.com expires"
python omni.py run "renew the SSL certificate for my domain"
python omni.py run "manage SSL certificates for my web server"
```

### Auditing and compliance

```bash
python omni.py run "audit the system for security issues"
python omni.py run "run a compliance check against CIS benchmarks"
python omni.py run "check file permissions for sensitive configuration files"
python omni.py run "audit all user accounts with sudo access"
python omni.py run "scan for world-writable files in /etc"
```

### Security hardening

```bash
python omni.py run "harden the system security configuration"
python omni.py run "disable unused system services for security"
python omni.py run "configure the firewall to allow only ports 22, 80, and 443"
python omni.py run "enable fail2ban to block brute-force login attempts"
python omni.py run "restrict SSH to key-based authentication only"
```

### Firewall management

```bash
python omni.py run "configure the firewall to allow port 80"
python omni.py run "block incoming connections on port 23"
python omni.py run "allow traffic from IP 192.168.1.100"
python omni.py run "show current firewall rules"
python omni.py run "enable the firewall"
```

---

## Data and analytics

### Data processing

```bash
python omni.py run "process the CSV file data.csv and calculate summary statistics"
python omni.py run "filter rows in sales.csv where amount is greater than 1000"
python omni.py run "merge dataset_a.csv and dataset_b.csv on the user_id column"
python omni.py run "clean the data in customers.csv by removing duplicates and nulls"
```

### ETL and pipelines

```bash
python omni.py run "setup a data pipeline to ingest CSV files from ~/data/incoming"
python omni.py run "create an ETL pipeline that transforms JSON to CSV"
python omni.py run "migrate data from the old PostgreSQL database to the new one"
python omni.py run "setup a data pipeline from the REST API to a local SQLite database"
```

### Machine learning

```bash
python omni.py run "train a classification model on the iris dataset"
python omni.py run "run a machine learning pipeline on data.csv to predict churn"
python omni.py run "generate a regression model for the housing price dataset"
python omni.py run "run feature importance analysis on the training data"
```

### Analytics and visualisation

```bash
python omni.py run "run analytics on the sales data and generate a report"
python omni.py run "create a bar chart of monthly revenue from sales.csv"
python omni.py run "setup a dashboard to visualise system metrics"
python omni.py run "generate a summary report of the logs in /var/log/app"
```

---

## n8n workflows

### Prerequisites

Ensure n8n is running and configured in `.env`:

```dotenv
N8N_URL=http://localhost:5678
N8N_API_KEY=your-api-key
```

### List workflows

```bash
python omni.py n8n list
```

Sample output:

```
┌──────────────────────────────────────────────────────────────┐
│ ID                  Name                    Active            │
├──────────────────────────────────────────────────────────────┤
│ YUnR6qxyj0FveVOU    Daily Report            false             │
│ aBcDeFgHiJkLmNoP    Slack Notifier          true              │
└──────────────────────────────────────────────────────────────┘
```

### Create a workflow from natural language

**Scheduled tasks:**

```bash
python omni.py n8n create "every morning at 9am, send me an email with today's weather"
python omni.py n8n create "every hour, check if the API at /health returns 200 and alert if not"
python omni.py n8n create "every Friday afternoon, summarise this week's GitHub issues and post to Slack"
python omni.py n8n create "daily at midnight, delete log files older than 7 days"
python omni.py n8n create "every Monday morning, email a weekday briefing"
```

**Event-driven:**

```bash
python omni.py n8n create "when a file appears in my S3 bucket, send a Slack notification"
python omni.py n8n create "when a new row is added to the Google Sheet, create a Jira ticket"
python omni.py n8n create "when a form is submitted, add the data to Airtable and send a welcome email"
python omni.py n8n create "when a webhook is received from GitHub, run the CI pipeline"
python omni.py n8n create "when a new Stripe payment arrives, log it and send a receipt"
```

**Data pipelines:**

```bash
python omni.py n8n create "every day, fetch sales data from the API and write it to Google Sheets"
python omni.py n8n create "sync new Stripe payments to QuickBooks every hour"
python omni.py n8n create "every hour, pull metrics from Prometheus and write to a dashboard"
python omni.py n8n create "when a customer signs up, add them to Mailchimp and create a CRM record"
```

### Trigger a workflow manually

```bash
python omni.py n8n run <workflow-id>
```

### Check status

```bash
python omni.py n8n status <workflow-id>
```

### Full lifecycle example

```bash
# 1. Create the workflow
python omni.py n8n create "every day at midnight, archive old log files"

# 2. Note the ID printed, e.g. YUnR6qxyj0FveVOU
# 3. Test-trigger manually
python omni.py n8n run YUnR6qxyj0FveVOU

# 4. Check the result
python omni.py n8n status YUnR6qxyj0FveVOU

# 5. Activate in the n8n UI for recurring execution
```

---

## Custom Linux distro builder

> Requires Linux, root access, and `pip install -e ".[distro]"`.
> See [SETUP.md](SETUP.md) for host tool installation.

### List available profiles

```bash
python omni.py distro profiles
```

### Estimate before building

Always estimate first — builds can take 20–60 min and use several GB of disk:

```bash
python omni.py distro estimate --profile minimal
python omni.py distro estimate --profile debian_base
```

### Build from a named profile

```bash
# Minimal headless Debian server
sudo python omni.py distro build --profile minimal --output ~/isos/

# Full Debian base
sudo python omni.py distro build --profile debian_base --output ~/isos/

# Custom output name
sudo python omni.py distro build --profile debian_base --name "MyServer-1.0" --output ~/isos/
```

### Build from natural language

```bash
sudo python omni.py distro build --nl "minimal Debian ISO with nginx and ssh, no GUI" --output ~/isos/
sudo python omni.py distro build --nl "Arch Linux with KDE Plasma and gaming packages" --output ~/isos/
sudo python omni.py distro build --nl "tiny headless Debian for a Raspberry Pi" --output ~/isos/
sudo python omni.py distro build --nl "Debian server with Docker, Kubernetes tools, and Prometheus" --output ~/isos/
sudo python omni.py distro build --nl "minimal buildroot image for an embedded ARM device" --output ~/isos/
```

### What gets built (10 stages)

1. Validate environment and check host tools
2. Fetch kernel source (cached in `~/.omniautomator/kernel_cache`)
3. Configure kernel (apply kconfig overrides from profile)
4. Compile kernel
5. Build root filesystem (`debootstrap` / `pacstrap`)
6. Install selected packages
7. Configure system (hostname, locale, timezone)
8. Set up bootloader (syslinux)
9. Assemble `.iso` with xorriso
10. Verify integrity and write checksum

The finished `.iso` is saved to `output_dir` (default `./distro_output`).

---

## Batch file patterns

Batch files run commands in sequence. Lines starting with `#` are comments; blank lines are ignored.

### Directory setup

```text
# setup_workspace.txt
create a folder named workspace in ~/Projects
create a folder named workspace/frontend in ~/Projects
create a folder named workspace/backend in ~/Projects
create a folder named workspace/docs in ~/Projects
take a screenshot and save to ~/Projects/workspace/docs/initial.png
```

```bash
python omni.py batch setup_workspace.txt
```

### Cleanup

```text
# cleanup.txt
delete all .pyc files in ~/Projects/myapp
delete folder ~/Projects/myapp/dist
delete folder ~/Projects/myapp/.pytest_cache
delete all .log files older than 7 days in /var/log/myapp
```

```bash
python omni.py batch cleanup.txt --safe-mode
```

### Morning system check

```text
# morning.txt
show disk usage on /
show current memory usage
list processes sorted by CPU usage
check if the nginx service is running
check the status of the postgresql service
take a screenshot and save to ~/logs/screenshots/morning.png
```

```bash
python omni.py batch morning.txt
```

### Project scaffold

```text
# new_project.txt
create a Python project named my-new-service in ~/Projects
create folder ~/Projects/my-new-service/docs
create a folder named scripts in ~/Projects/my-new-service
create a Dockerfile for the Python application
generate a docker-compose.yml with the app and a postgres database
```

```bash
python omni.py batch new_project.txt
```

### Document generation batch

```text
# monthly_reports.txt
create a Word document named january_report.docx in ~/reports
create a Word document named february_report.docx in ~/reports
create a Word document named march_report.docx in ~/reports
create an Excel spreadsheet named Q1_summary.xlsx with revenue columns
create a PowerPoint named Q1_review.pptx with 5 slides
```

```bash
python omni.py batch monthly_reports.txt
```

### Batch run options

```bash
python omni.py batch tasks.txt --stop-on-error    # halt on first failure
python omni.py batch cleanup.txt --safe-mode      # confirm destructive steps
python omni.py batch tasks.txt --debug            # verbose per-step output
python omni.py --log-file ~/batch.jsonl batch tasks.txt  # structured log
```

---

## Chatbot / multi-turn mode

```bash
python omni.py chatbot
```

Context is held across turns in the same session — refer to previous results without repeating them.

### Example — building a project

```
You> create a Python project named user-service in ~/Projects
Bot> Created user-service at ~/Projects/user-service with src/, tests/, and README.md.

You> add a Dockerfile to it
Bot> Added Dockerfile to ~/Projects/user-service.

You> now create a docker-compose.yml with postgres and redis
Bot> Created docker-compose.yml with web, postgres, and redis services.

You> generate Word documentation for this project
Bot> Created ~/Projects/user-service/docs/project-docs.docx.
```

### Example — file organisation

```
You> show me all files in ~/Downloads
Bot> Found 47 files. Largest: archive.zip (2.3 GB), dataset.csv (450 MB)...

You> move all zip files to ~/archive
Bot> Moved 12 .zip files to ~/archive.

You> delete everything older than 30 days
Bot> Found 23 files older than 30 days. Confirm deletion? [y/N]
> y
Bot> Deleted 23 files.
```

### Example — n8n workflow

```
You> list my n8n workflows
Bot> Found 3 workflows: Daily Report (active), Slack Notifier (active), Test Webhook (inactive).

You> create a new one that emails me a weekly summary every Monday
Bot> Created workflow "Weekly Summary Email", ID: xYz123. Activate in n8n UI to start.

You> run it now to test
Bot> Triggered execution of xYz123. Check status with /n8n status xYz123.
```

### Special chatbot commands

```
/status        — current AI model, connection state, token count
/history       — list of commands run this session
/context       — active conversation context window
/cd ~/Projects — change working directory
/pwd           — print current directory
/ls            — list files in current directory
/clear         — reset conversation context (keeps history)
exit           — quit
```

---

## Global flags reference

These flags prefix any command:

| Flag | Description |
|------|-------------|
| `--debug` | Verbose logging to the console |
| `--safe-mode` | Confirm before any destructive operation |
| `--log-file PATH` | Write structured JSON logs to a file |
| `--version` / `-V` | Print version and exit |

Per-command flags (on `omni run` only):

| Flag | Description |
|------|-------------|
| `--safe-mode` | Override for this command |
| `--debug` | Override for this command |
| `--model` / `-m MODEL_ID` | Force a specific AI model |

### Examples

```bash
# Debug any subcommand
python omni.py --debug run "create folder test"
python omni.py --debug n8n list
python omni.py --debug distro profiles

# Log everything to a file
python omni.py --log-file ~/omni.jsonl batch morning.txt

# Safe mode for an entire batch run
python omni.py --safe-mode batch cleanup.txt

# Force a specific model for one command
python omni.py run "write a technical summary" -m openai/gpt-4o

# Combine multiple flags
python omni.py --debug --safe-mode --log-file /tmp/omni.jsonl run "delete old backups"
```

---

## Spell correction examples

The NLP engine uses Levenshtein distance to correct typos silently before processing. You do not need to type commands perfectly.

| What you type | What gets executed |
|---------------|-------------------|
| `creat a fodler named test` | create a folder named test |
| `delet all files in downloads` | delete all files in downloads |
| `intall packge nginx` | install package nginx |
| `mkae a dirctory called logs` | make a directory called logs |
| `coyp file report.pdf to archiv` | copy file report.pdf to archive |
| `moev folder src to backup` | move folder src to backup |
| `lits all runig procesess` | list all running processes |
| `shwo disk usag on /` | show disk usage on / |
| `genrate a dockerfile` | generate a Dockerfile |
| `deplyo the app` | deploy the app |
| `pubish the packge` | publish the package |

Synonyms are also handled — these all do the same thing:

```bash
python omni.py run "create a folder named test"
python omni.py run "make a directory named test"
python omni.py run "mkdir test"
python omni.py run "new folder test"
python omni.py run "please create a folder called test"
python omni.py run "can you create a directory called test"
```

---

## Tips

**Combine `--safe-mode` with batch files** for any workflow that touches important files or processes:

```bash
python omni.py batch restore_prod.txt --safe-mode
```

**Use `--log-file` for auditing** — the JSON log contains every action taken:

```bash
python omni.py --log-file ~/audit.jsonl batch production_tasks.txt
python -m json.tool < ~/audit.jsonl   # pretty-print
grep '"level":"ERROR"' ~/audit.jsonl  # filter errors only
```

**Explore interactively first, then automate** — use `omni chatbot` to validate sequences, then copy them into a batch file:

```bash
python omni.py chatbot
# test your commands one by one
# then copy them into a batch file for repeatable execution
```

**Model selection** — OmniAutomator auto-picks the best free model. Override only when you need a specific capability:

```bash
python omni.py run "translate this to French" -m openai/gpt-4o
```

**Refer back to previous results in chatbot mode** — the context window remembers the whole session:

```
You> create a Python project named api-server
Bot> Created at ~/Projects/api-server ...

You> add tests to it         ← "it" resolves from context
You> now dockerise it        ← still refers to api-server
```

**Batch file comments help with maintenance:**

```text
# Runs every Sunday night
# cleanup.txt — v2 — 2024-05-01

# Step 1: remove build artifacts
delete folder ./dist
delete folder ./.pytest_cache

# Step 2: archive old logs
move all .log files older than 7 days from /var/log to ~/archive/logs
```
