# Archon — Complete Task Reference

Every example below runs as `archon run "..."`, inside `archon chatbot`, or as a line in a batch file.

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
archon run "create a folder named reports"
archon run "create a folder called archive in ~/Documents"
archon run "make a directory named logs in /var/app"
archon run "create folder projects/web on the Desktop"
archon run "mkdir /tmp/workspace"
```

### Create nested folders

```bash
archon run "create a folder named app with subfolders src, tests, and docs"
archon run "create nested folders: project/src/components and project/src/utils"
archon run "create folder structure api/v1/routes and api/v1/models"
archon run "create project layout with folders frontend, backend, and shared"
```

### Delete a folder

```bash
archon run "delete the folder named reports"
archon run "remove folder archive from ~/Documents"
archon run "delete folder old_logs and all its contents"
archon run "permanently delete the build folder"
```

```bash
# Always safe to add --safe-mode for deletions
archon run "delete folder archive" --safe-mode
```

### Move a folder

```bash
archon run "move folder old_project to ~/archive"
archon run "move src to ~/Projects/myapp/src"
archon run "move the folder downloads to /mnt/storage/downloads"
```

---

## File operations

### Create a file

```bash
archon run "create an empty file named notes.txt in ~/Documents"
archon run "create a file called config.json with empty content"
archon run "create a Python script named hello.py"
archon run "create a shell script named deploy.sh in ~/scripts"
archon run "create a Markdown file named README.md in the current folder"
```

### Delete a file

```bash
archon run "delete the file notes.txt in ~/Documents"
archon run "remove file old_config.json"
archon run "delete all .log files in /var/log/myapp"
archon run "delete all temporary files in ~/Downloads"
archon run "remove all .DS_Store files from ~/Projects"
```

### Delete files by age

```bash
archon run "delete all files older than 30 days in ~/Downloads"
archon run "remove files modified more than 7 days ago in /tmp"
archon run "clean up log files older than 90 days in /var/log"
```

### Delete files by type

```bash
archon run "delete all .pyc files in the project"
archon run "delete all .tmp and .bak files in ~/Documents"
archon run "remove all compiled object files in ~/Projects/myapp"
```

### Write content to a file

```bash
archon run "write 'Hello, World!' to a file named greeting.txt"
archon run "append today's date to a log file named activity.log"
archon run "create a file named .gitignore with standard Python ignores"
```

---

## Bulk and numbered creation

### Create numbered folders

```bash
archon run "create 10 folders named folder1 through folder10"
archon run "create 50 folders from test1 to test50 in ~/experiments"
archon run "create 5 folders named project_1 through project_5 on the Desktop"
archon run "create 100 folders named client001 through client100"
```

### Create numbered files

```bash
archon run "create 20 empty text files named note1.txt through note20.txt"
archon run "create 5 Python scripts named script_1.py through script_5.py"
archon run "create 12 markdown files named month_01.md through month_12.md"
```

### Create folders with nested structure

```bash
archon run "create 3 project folders each with src, tests, and docs subfolders"
archon run "create 10 folders named client1 through client10, each with invoices and contracts subfolders"
archon run "create 5 folders named week1 to week5, each containing a notes and tasks subfolder"
```

### Create with date-based names

```bash
archon run "create folders named report_2024_01 through report_2024_12"
archon run "create folders named week_01 through week_52 inside ~/planning"
```

---

## Copy and move

### Copy a file

```bash
archon run "copy file report.pdf to ~/archive"
archon run "copy notes.txt to /tmp/notes_backup.txt"
archon run "duplicate config.json as config.backup.json"
```

### Copy a folder

```bash
archon run "copy folder src to src_backup"
archon run "copy folder ~/Projects/myapp to ~/Projects/myapp_backup"
archon run "copy the docs folder to ~/Documents/project_docs"
```

### Copy all files of a type

```bash
archon run "copy all PDF files from ~/Documents to ~/archive/pdfs"
archon run "copy all images from ~/Downloads to ~/Pictures/new"
archon run "copy all .py files to ~/code_backup"
archon run "copy every .csv file in ~/data to ~/data/backup"
```

### Move files and folders

```bash
archon run "move report.pdf to ~/archive"
archon run "move all .log files from /var/app to /var/app/logs"
archon run "move the file notes.txt to ~/Documents/notes"
archon run "move folder old_project to ~/archive"
archon run "move all zip files in ~/Downloads to ~/archive/zips"
```

---

## Rename and reorganise

### Rename a file or folder

```bash
archon run "rename file report.pdf to quarterly_report_Q1.pdf"
archon run "rename notes.txt to meeting_notes_2024.txt"
archon run "rename folder old_name to new_name"
archon run "rename directory src to source"
```

### Batch rename

```bash
archon run "rename all .jpeg files to .jpg in ~/Pictures"
archon run "rename all files in ~/exported by adding the prefix 2024_ to each"
archon run "rename all .txt files to .md in ~/notes"
archon run "lowercase all filenames in ~/downloads"
```

### Organise files into subfolders

```bash
archon run "move all PDF files into a subfolder called pdfs"
archon run "sort files in ~/Downloads into folders by extension"
archon run "organise photos in ~/Pictures by year and month"
archon run "group all Python files in ~/scripts into a src folder"
```

---

## Find and list

### List files and folders

```bash
archon run "list all files in ~/Documents"
archon run "show files in the current directory"
archon run "list all Python files in ~/Projects"
archon run "show all .log files in /var/log"
archon run "list folders in ~/Projects sorted by date"
```

### Find files

```bash
archon run "find all PDF files in ~/Documents"
archon run "find files larger than 100MB in ~/Downloads"
archon run "find all files modified in the last 24 hours in ~/Projects"
archon run "find all empty folders in ~/Projects"
archon run "find all files named config.json under ~/Projects"
```

### Check existence and size

```bash
archon run "check if the folder reports exists in ~/Documents"
archon run "verify that config.toml exists in the current directory"
archon run "show the size of the folder ~/Projects/myapp"
archon run "what is the total size of all files in ~/Downloads"
```

---

## System information

### Disk usage

```bash
archon run "show disk usage on /"
archon run "check how much space is available on /home"
archon run "show disk usage for all mounted drives"
archon run "which directories are using the most space in /var"
archon run "check disk space on all partitions"
```

### Memory and CPU

```bash
archon run "show current memory usage"
archon run "how much RAM is being used"
archon run "show CPU usage"
archon run "display system resource summary"
archon run "what percentage of RAM is free"
```

### OS and hardware

```bash
archon run "show OS version"
archon run "what kernel version is running"
archon run "show hostname and IP addresses"
archon run "display system uptime"
archon run "show CPU model and core count"
archon run "list all network interfaces"
```

---

## Process management

### List processes

```bash
archon run "show all running processes"
archon run "list processes sorted by CPU usage"
archon run "show processes using the most memory"
archon run "find processes named nginx"
archon run "show the top 10 processes by memory"
```

### Kill processes

```bash
archon run "kill process named firefox" --safe-mode
archon run "stop all processes matching python" --safe-mode
archon run "kill the process with PID 1234" --safe-mode
archon run "force-kill all zombie processes" --safe-mode
```

> Always use `--safe-mode` when killing processes to get a confirmation prompt before anything is terminated.

---

## Service management

### Start, stop, restart services

```bash
archon run "start the nginx service"
archon run "stop the postgresql service"
archon run "restart the application service"
archon run "reload the nginx configuration"
archon run "restart all failed services"
```

### Enable and disable on boot

```bash
archon run "enable nginx to start on boot"
archon run "disable the bluetooth service"
archon run "enable postgresql at startup"
```

### Check service status

```bash
archon run "check the status of the nginx service"
archon run "is postgresql running"
archon run "show all failed systemd services"
archon run "list all enabled services"
```

---

## User and permission management

### User accounts

```bash
archon run "create a user named deploy with a home directory"
archon run "add user deploy to the sudo group"
archon run "remove user old_account"
archon run "list all system users"
archon run "show which groups user deploy belongs to"
```

### File permissions

```bash
archon run "set permissions on ~/scripts/deploy.sh to executable"
archon run "make all .sh files in ~/scripts executable"
archon run "set the folder ~/app to be owned by the www-data user"
archon run "give read and write permissions to ~/shared to all users"
archon run "recursively set correct permissions on /var/www/html"
```

### Scheduled tasks (cron)

```bash
archon run "schedule a task to run backup.sh every day at 3am"
archon run "add a cron job to delete /tmp files every Sunday at midnight"
archon run "schedule cleanup.py to run at 2am on the first of every month"
archon run "list all scheduled cron jobs"
```

---

## Package management

### Install packages

```bash
archon run "install package vim"
archon run "install nginx and curl"
archon run "install Python packages requests, httpx, and pydantic"
archon run "install npm package express"
archon run "install the latest version of git"
archon run "install docker"
```

### Search and list

```bash
archon run "search for packages matching http client"
archon run "search for python packages matching async"
archon run "list all installed packages"
archon run "list all Python packages installed in this environment"
archon run "check if nginx is installed"
```

### Uninstall and update

```bash
archon run "uninstall package vim"
archon run "remove nginx and purge its config files"
archon run "update all system packages"
archon run "upgrade pip to the latest version"
archon run "update only security packages"
```

---

## Project generation

### Python

```bash
archon run "create a Python project named myapi"
archon run "generate a Python project with Flask and PostgreSQL"
archon run "create a FastAPI project with JWT auth and Docker support"
archon run "setup a Django project with REST framework"
archon run "create a Python package with tests, CI, and a README"
archon run "generate a Python CLI tool named myscript"
```

### Python virtual environment

```bash
archon run "create a virtual environment in ~/Projects/myapp"
archon run "setup a venv named .venv in the current directory"
archon run "create a virtualenv and install requirements.txt"
```

### C and C++

```bash
archon run "create a C project named calculator"
archon run "generate a C program named sorter that sorts an array"
archon run "create a C hello world program"
archon run "create a C++ project named image-processor with CMake"
```

### Java

```bash
archon run "create a Java project named inventory-system"
archon run "generate a Java Maven project named backend-api"
archon run "create a Spring Boot project named user-service"
```

### Hello World in any language

```bash
archon run "create a hello world program in Python"
archon run "create a hello world program in C"
archon run "create a hello world program in Go"
archon run "generate a hello world in Rust"
archon run "create a hello world in JavaScript"
```

### Node.js / JavaScript / TypeScript

```bash
archon run "create a Node.js Express API server"
archon run "generate a React app named my-dashboard"
archon run "create a React application with TypeScript and Jest"
archon run "setup a Next.js project with TailwindCSS"
archon run "create a Vue 3 project with Vite"
archon run "generate a Node.js CLI tool"
```

### Data science and analysis

```bash
archon run "create a data analysis project with pandas and matplotlib"
archon run "generate a machine learning project with scikit-learn"
archon run "create a Jupyter notebook project for EDA"
archon run "setup a data science environment with numpy, pandas, and seaborn"
```

### Web scraping

```bash
archon run "create a web scraping project using BeautifulSoup"
archon run "generate a Scrapy project for crawling product pages"
archon run "create a scraper project with Playwright and Python"
```

### With specific features

```bash
archon run "create a Python project with Redis caching, Celery workers, and Docker Compose"
archon run "generate a REST API with OpenAPI docs, database migrations, and pytest"
archon run "create a full-stack project with React frontend and FastAPI backend"
```

---

## Document generation

> Requires core dependencies (`python-docx`, `python-pptx`, `openpyxl`, `reportlab` — all included in the base install).

### Word documents (.docx)

```bash
archon run "create a Word document named quarterly-report.docx"
archon run "generate a Word document named meeting-agenda.docx with a title and bullet points"
archon run "create a Word document named proposal with an introduction and three sections"
archon run "write a Word document named contract.docx in ~/Documents"
archon run "generate a formatted Word report with headings and a table"
```

### PowerPoint presentations (.pptx)

```bash
archon run "create a PowerPoint presentation about AI trends"
archon run "generate a 5-slide presentation named company-intro.pptx"
archon run "create a PowerPoint deck with a title slide and 4 content slides"
archon run "make a presentation named sales-q1.pptx with charts and bullet points"
archon run "generate a product pitch deck in PowerPoint format"
```

### Excel spreadsheets (.xlsx)

```bash
archon run "create an Excel spreadsheet with columns for name, date, and amount"
archon run "generate an Excel file named sales-data.xlsx with sample rows"
archon run "create a budget spreadsheet with income and expense columns"
archon run "make an Excel worksheet with a header row and 10 data rows"
archon run "create an Excel report with summary and detail sheets"
archon run "generate a timesheet template in Excel format"
```

### PDF documents

```bash
archon run "generate a PDF invoice named invoice-001.pdf"
archon run "create a PDF report with a title and three sections"
archon run "generate a PDF resume template"
archon run "create a PDF with a cover page and table of contents"
```

### Save content to a document

```bash
archon run "save the text 'Project started on 2024-01-01' to a Word document named project-log.docx"
archon run "append a new row containing 'Alice, 2024-03, 5000' to sales.xlsx"
archon run "write the system info output to a Word document named system-report.docx"
```

---

## DevOps and infrastructure

### Docker

```bash
archon run "create a Dockerfile for my Python Flask app"
archon run "create a Dockerfile for a Node.js application"
archon run "generate a multi-stage Dockerfile for a Go binary"
archon run "create a Dockerfile that runs a FastAPI app on port 8000"
```

### Docker Compose

```bash
archon run "generate a docker-compose.yml with nginx, postgres, and redis"
archon run "create a docker-compose.yml with a web service and a PostgreSQL database"
archon run "add a Redis cache service to my docker-compose.yml"
archon run "create a docker-compose file for a full-stack app with a React frontend and a Node backend"
```

### Kubernetes

```bash
archon run "create a Kubernetes deployment YAML for my API service"
archon run "generate a Kubernetes service and ingress for my web app"
archon run "create a Kubernetes deployment with resource limits and readiness probes"
archon run "generate a Kubernetes ConfigMap and Secret for my app"
archon run "create a Helm chart for my microservice"
```

### CI/CD pipelines

```bash
archon run "configure a GitHub Actions CI pipeline for a Python project"
archon run "create a GitHub Actions workflow that runs tests on every push"
archon run "generate a GitLab CI pipeline with build, test, and deploy stages"
archon run "create a Jenkins pipeline for my Node.js app"
archon run "setup automated deployment to AWS on tag push using GitHub Actions"
```

### Terraform

```bash
archon run "generate Terraform config for an AWS EC2 instance"
archon run "create a Terraform file for an S3 bucket with versioning enabled"
archon run "generate Terraform config for a GCP Cloud Run service"
archon run "create a Terraform module for a VPC with public and private subnets"
```

### Monitoring

```bash
archon run "setup monitoring for my web application"
archon run "configure Prometheus and Grafana for my services"
archon run "create a health check script for my API endpoints"
archon run "setup log aggregation with the ELK stack"
archon run "generate alerting rules for high CPU and memory usage"
```

### Deploy and release

```bash
archon run "deploy the app"
archon run "release version 1.2.0"
archon run "publish the package to PyPI"
archon run "ship the latest build to production"
archon run "deploy the Docker image to the staging environment"
```

---

## Cloud deployment

### AWS

```bash
archon run "deploy the app to AWS"
archon run "deploy to AWS Elastic Beanstalk"
archon run "push the Docker image to AWS ECR"
archon run "create an S3 bucket named my-artifacts and upload the build"
archon run "deploy a Lambda function from lambda.zip"
```

### Google Cloud

```bash
archon run "deploy the application to GCP"
archon run "push the image to Google Container Registry"
archon run "deploy to Cloud Run with 2 replicas"
archon run "upload build artifacts to Google Cloud Storage"
```

### Azure

```bash
archon run "deploy the app to Azure"
archon run "push the Docker image to Azure Container Registry"
archon run "deploy to Azure App Service"
```

### Heroku

```bash
archon run "deploy the app to Heroku"
archon run "create a new Heroku app named my-service"
archon run "scale the Heroku web dyno to 2"
archon run "set the Heroku environment variable DATABASE_URL"
```

---

## Browser automation

> Requires `[web]` extras: `pip install -e ".[web]"` (Selenium + Playwright).

### Open and navigate

```bash
archon run "open https://example.com in a browser"
archon run "navigate to https://myapp.local/dashboard"
archon run "open https://example.com in headless Chrome"
```

### Interact with page elements

```bash
archon run "click the button with text 'Submit' on https://example.com/form"
archon run "fill in the username field on the login page with 'admin'"
archon run "type 'search query' into the search box on https://example.com"
archon run "click the first link in the navigation menu"
archon run "check the checkbox labelled 'Accept terms'"
archon run "select 'Option 2' from the dropdown menu"
```

### Take screenshots

```bash
archon run "open https://example.com and take a screenshot"
archon run "take a screenshot of https://myapp.local/dashboard and save as dashboard.png"
archon run "capture the full-page screenshot of https://example.com"
```

### Fill and submit forms

```bash
archon run "fill in the login form at https://myapp.local with username admin and password secret"
archon run "submit the contact form at https://example.com with name Alice and email alice@example.com"
archon run "fill out and submit the registration form at https://example.com/signup"
```

### Close browser

```bash
archon run "close the browser"
archon run "close all open browser windows"
```

---

## Web scraping

> Requires `beautifulsoup4` (included in base dependencies) and optionally `[web]` for JavaScript-rendered sites.

### Scrape a full page

```bash
archon run "scrape https://example.com and save the content"
archon run "scrape all text from https://example.com/article"
archon run "extract the main article text from https://news.example.com/story"
```

### Extract links

```bash
archon run "extract all links from https://example.com"
archon run "get all href links on https://example.com/resources"
archon run "find all external links on https://example.com"
archon run "list all PDF links on https://example.com/downloads"
```

### Extract images

```bash
archon run "extract all images from https://example.com"
archon run "get all image URLs from https://example.com/gallery"
archon run "download all images from the page at https://example.com/photos"
```

### Extract tables

```bash
archon run "scrape the first table from https://example.com/data"
archon run "extract all tables from https://example.com/stats and save as CSV"
archon run "get the pricing table from https://example.com/pricing"
```

### Search and extract

```bash
archon run "search example.com for 'python tutorial' and extract the first 5 results"
archon run "find all articles tagged 'automation' on https://example.com/blog"
archon run "scrape product names and prices from https://shop.example.com"
```

### Extract article content

```bash
archon run "extract the article text from https://example.com/post/123"
archon run "get the title, author, and body from https://blog.example.com/post"
archon run "extract and clean the article at https://news.example.com"
```

---

## File downloads and networking

### Download files

```bash
archon run "download https://example.com/file.zip to ~/Downloads"
archon run "fetch the file at https://example.com/data.csv and save to ~/data"
archon run "download the latest release from https://example.com/releases/latest"
```

### Check connectivity

```bash
archon run "check if google.com is reachable"
archon run "ping 8.8.8.8 and show the result"
archon run "test the connection to https://api.example.com/health"
archon run "check if port 5432 is open on localhost"
```

### API testing

```bash
archon run "test the GET endpoint https://api.example.com/users and show the response"
archon run "send a POST request to https://api.example.com/auth with username and password"
archon run "check the response time of https://api.example.com/health"
```

---

## Screenshots and UI control

### Take a screenshot

```bash
archon run "take a screenshot and save to ~/screenshots/now.png"
archon run "take a screenshot of the current screen"
archon run "capture the screen and save as screenshot.png on the Desktop"
```

### UI interaction (desktop)

```bash
archon run "click at position 100, 200 on the screen"
archon run "type 'hello world' into the currently focused window"
archon run "press the Enter key"
archon run "scroll down on the current window"
```

> Requires `[gui]` (desktop automation) extras: `pip install -e ".[gui]"`. On headless Linux, set `DISPLAY` first.

---

## Security operations

### Vulnerability scanning

```bash
archon run "run a security scan on the current project"
archon run "scan for vulnerabilities in my Python dependencies"
archon run "check for known CVEs in requirements.txt"
archon run "run a vulnerability assessment on the application"
```

### SSL and certificates

```bash
archon run "setup SSL for my domain example.com"
archon run "generate a self-signed SSL certificate for localhost"
archon run "check when the SSL certificate for example.com expires"
archon run "renew the SSL certificate for my domain"
archon run "manage SSL certificates for my web server"
```

### Auditing and compliance

```bash
archon run "audit the system for security issues"
archon run "run a compliance check against CIS benchmarks"
archon run "check file permissions for sensitive configuration files"
archon run "audit all user accounts with sudo access"
archon run "scan for world-writable files in /etc"
```

### Security hardening

```bash
archon run "harden the system security configuration"
archon run "disable unused system services for security"
archon run "configure the firewall to allow only ports 22, 80, and 443"
archon run "enable fail2ban to block brute-force login attempts"
archon run "restrict SSH to key-based authentication only"
```

### Firewall management

```bash
archon run "configure the firewall to allow port 80"
archon run "block incoming connections on port 23"
archon run "allow traffic from IP 192.168.1.100"
archon run "show current firewall rules"
archon run "enable the firewall"
```

---

## Data and analytics

### Data processing

```bash
archon run "process the CSV file data.csv and calculate summary statistics"
archon run "filter rows in sales.csv where amount is greater than 1000"
archon run "merge dataset_a.csv and dataset_b.csv on the user_id column"
archon run "clean the data in customers.csv by removing duplicates and nulls"
```

### ETL and pipelines

```bash
archon run "setup a data pipeline to ingest CSV files from ~/data/incoming"
archon run "create an ETL pipeline that transforms JSON to CSV"
archon run "migrate data from the old PostgreSQL database to the new one"
archon run "setup a data pipeline from the REST API to a local SQLite database"
```

### Machine learning

```bash
archon run "train a classification model on the iris dataset"
archon run "run a machine learning pipeline on data.csv to predict churn"
archon run "generate a regression model for the housing price dataset"
archon run "run feature importance analysis on the training data"
```

### Analytics and visualisation

```bash
archon run "run analytics on the sales data and generate a report"
archon run "create a bar chart of monthly revenue from sales.csv"
archon run "setup a dashboard to visualise system metrics"
archon run "generate a summary report of the logs in /var/log/app"
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
archon n8n list
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
archon n8n create "every morning at 9am, send me an email with today's weather"
archon n8n create "every hour, check if the API at /health returns 200 and alert if not"
archon n8n create "every Friday afternoon, summarise this week's GitHub issues and post to Slack"
archon n8n create "daily at midnight, delete log files older than 7 days"
archon n8n create "every Monday morning, email a weekday briefing"
```

**Event-driven:**

```bash
archon n8n create "when a file appears in my S3 bucket, send a Slack notification"
archon n8n create "when a new row is added to the Google Sheet, create a Jira ticket"
archon n8n create "when a form is submitted, add the data to Airtable and send a welcome email"
archon n8n create "when a webhook is received from GitHub, run the CI pipeline"
archon n8n create "when a new Stripe payment arrives, log it and send a receipt"
```

**Data pipelines:**

```bash
archon n8n create "every day, fetch sales data from the API and write it to Google Sheets"
archon n8n create "sync new Stripe payments to QuickBooks every hour"
archon n8n create "every hour, pull metrics from Prometheus and write to a dashboard"
archon n8n create "when a customer signs up, add them to Mailchimp and create a CRM record"
```

### Trigger a workflow manually

```bash
archon n8n run <workflow-id>
```

### Check status

```bash
archon n8n status <workflow-id>
```

### Full lifecycle example

```bash
# 1. Create the workflow
archon n8n create "every day at midnight, archive old log files"

# 2. Note the ID printed, e.g. YUnR6qxyj0FveVOU
# 3. Test-trigger manually
archon n8n run YUnR6qxyj0FveVOU

# 4. Check the result
archon n8n status YUnR6qxyj0FveVOU

# 5. Activate in the n8n UI for recurring execution
```

---

## Custom Linux distro builder

> Requires Linux, root access, and `pip install -e ".[distro]"`.
> See [SETUP.md](SETUP.md) for host tool installation.

### List available profiles

```bash
archon distro profiles
```

### Estimate before building

Always estimate first — builds can take 20–60 min and use several GB of disk:

```bash
archon distro estimate --profile minimal
archon distro estimate --profile debian_base
```

### Build from a named profile

```bash
# Minimal headless Debian server
sudo archon distro build --profile minimal --output ~/isos/

# Full Debian base
sudo archon distro build --profile debian_base --output ~/isos/

# Custom output name
sudo archon distro build --profile debian_base --name "MyServer-1.0" --output ~/isos/
```

### Build from natural language

```bash
sudo archon distro build --nl "minimal Debian ISO with nginx and ssh, no GUI" --output ~/isos/
sudo archon distro build --nl "Arch Linux with KDE Plasma and gaming packages" --output ~/isos/
sudo archon distro build --nl "tiny headless Debian for a Raspberry Pi" --output ~/isos/
sudo archon distro build --nl "Debian server with Docker, Kubernetes tools, and Prometheus" --output ~/isos/
sudo archon distro build --nl "minimal buildroot image for an embedded ARM device" --output ~/isos/
```

### What gets built (10 stages)

1. Validate environment and check host tools
2. Fetch kernel source (cached in `~/.archon/kernel_cache`)
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
archon batch setup_workspace.txt
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
archon batch cleanup.txt --safe-mode
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
archon batch morning.txt
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
archon batch new_project.txt
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
archon batch monthly_reports.txt
```

### Batch run options

```bash
archon batch tasks.txt --stop-on-error    # halt on first failure
archon batch cleanup.txt --safe-mode      # confirm destructive steps
archon batch tasks.txt --debug            # verbose per-step output
archon --log-file ~/batch.jsonl batch tasks.txt  # structured log
```

---

## Chatbot / multi-turn mode

```bash
archon chatbot
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
/help          — show available commands
/status        — current AI model and session status
/model         — list / switch the local Ollama model
/plugins       — list loaded plugins
/config        — config directory and AI settings
/history       — recent messages this session
/context       — session context
/cd ~/Projects — change working directory
/pwd           — print current directory
/ls [path]     — list a directory
/explain       — explain the last command
/clear         — redraw the console (keeps history)
/exit          — quit (or Ctrl+D)
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

Per-command flags (on `archon run` only):

| Flag | Description |
|------|-------------|
| `--safe-mode` | Override for this command |
| `--debug` | Override for this command |
| `--model` / `-m MODEL_ID` | Force a specific AI model |

### Examples

```bash
# Debug any subcommand
archon --debug run "create folder test"
archon --debug n8n list
archon --debug distro profiles

# Log everything to a file
archon --log-file ~/archon.jsonl batch morning.txt

# Safe mode for an entire batch run
archon --safe-mode batch cleanup.txt

# Force a specific model for one command
archon run "write a technical summary" -m openai/gpt-4o

# Combine multiple flags
archon --debug --safe-mode --log-file /tmp/archon.jsonl run "delete old backups"
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
archon run "create a folder named test"
archon run "make a directory named test"
archon run "mkdir test"
archon run "new folder test"
archon run "please create a folder called test"
archon run "can you create a directory called test"
```

---

## Tips

**Combine `--safe-mode` with batch files** for any workflow that touches important files or processes:

```bash
archon batch restore_prod.txt --safe-mode
```

**Use `--log-file` for auditing** — the JSON log contains every action taken:

```bash
archon --log-file ~/audit.jsonl batch production_tasks.txt
python -m json.tool < ~/audit.jsonl   # pretty-print
grep '"level":"ERROR"' ~/audit.jsonl  # filter errors only
```

**Explore interactively first, then automate** — use `archon chatbot` to validate sequences, then copy them into a batch file:

```bash
archon chatbot
# test your commands one by one
# then copy them into a batch file for repeatable execution
```

**Model selection** — Archon uses the model configured for Ollama. Override only when you need a specific model:

```bash
archon run "translate this to French" -m qwen3.5:9b
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
