# Tyranos — Complete Task Reference

Every example below runs as `tyranos run "..."`, inside `tyranos chatbot`, or as a line in a batch file.

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
tyranos run "create a folder named reports"
tyranos run "create a folder called archive in ~/Documents"
tyranos run "make a directory named logs in /var/app"
tyranos run "create folder projects/web on the Desktop"
tyranos run "mkdir /tmp/workspace"
```

### Create nested folders

```bash
tyranos run "create a folder named app with subfolders src, tests, and docs"
tyranos run "create nested folders: project/src/components and project/src/utils"
tyranos run "create folder structure api/v1/routes and api/v1/models"
tyranos run "create project layout with folders frontend, backend, and shared"
```

### Delete a folder

```bash
tyranos run "delete the folder named reports"
tyranos run "remove folder archive from ~/Documents"
tyranos run "delete folder old_logs and all its contents"
tyranos run "permanently delete the build folder"
```

```bash
# Always safe to add --safe-mode for deletions
tyranos run "delete folder archive" --safe-mode
```

### Move a folder

```bash
tyranos run "move folder old_project to ~/archive"
tyranos run "move src to ~/Projects/myapp/src"
tyranos run "move the folder downloads to /mnt/storage/downloads"
```

---

## File operations

### Create a file

```bash
tyranos run "create an empty file named notes.txt in ~/Documents"
tyranos run "create a file called config.json with empty content"
tyranos run "create a Python script named hello.py"
tyranos run "create a shell script named deploy.sh in ~/scripts"
tyranos run "create a Markdown file named README.md in the current folder"
```

### Delete a file

```bash
tyranos run "delete the file notes.txt in ~/Documents"
tyranos run "remove file old_config.json"
tyranos run "delete all .log files in /var/log/myapp"
tyranos run "delete all temporary files in ~/Downloads"
tyranos run "remove all .DS_Store files from ~/Projects"
```

### Delete files by age

```bash
tyranos run "delete all files older than 30 days in ~/Downloads"
tyranos run "remove files modified more than 7 days ago in /tmp"
tyranos run "clean up log files older than 90 days in /var/log"
```

### Delete files by type

```bash
tyranos run "delete all .pyc files in the project"
tyranos run "delete all .tmp and .bak files in ~/Documents"
tyranos run "remove all compiled object files in ~/Projects/myapp"
```

### Write content to a file

```bash
tyranos run "write 'Hello, World!' to a file named greeting.txt"
tyranos run "append today's date to a log file named activity.log"
tyranos run "create a file named .gitignore with standard Python ignores"
```

---

## Bulk and numbered creation

### Create numbered folders

```bash
tyranos run "create 10 folders named folder1 through folder10"
tyranos run "create 50 folders from test1 to test50 in ~/experiments"
tyranos run "create 5 folders named project_1 through project_5 on the Desktop"
tyranos run "create 100 folders named client001 through client100"
```

### Create numbered files

```bash
tyranos run "create 20 empty text files named note1.txt through note20.txt"
tyranos run "create 5 Python scripts named script_1.py through script_5.py"
tyranos run "create 12 markdown files named month_01.md through month_12.md"
```

### Create folders with nested structure

```bash
tyranos run "create 3 project folders each with src, tests, and docs subfolders"
tyranos run "create 10 folders named client1 through client10, each with invoices and contracts subfolders"
tyranos run "create 5 folders named week1 to week5, each containing a notes and tasks subfolder"
```

### Create with date-based names

```bash
tyranos run "create folders named report_2024_01 through report_2024_12"
tyranos run "create folders named week_01 through week_52 inside ~/planning"
```

---

## Copy and move

### Copy a file

```bash
tyranos run "copy file report.pdf to ~/archive"
tyranos run "copy notes.txt to /tmp/notes_backup.txt"
tyranos run "duplicate config.json as config.backup.json"
```

### Copy a folder

```bash
tyranos run "copy folder src to src_backup"
tyranos run "copy folder ~/Projects/myapp to ~/Projects/myapp_backup"
tyranos run "copy the docs folder to ~/Documents/project_docs"
```

### Copy all files of a type

```bash
tyranos run "copy all PDF files from ~/Documents to ~/archive/pdfs"
tyranos run "copy all images from ~/Downloads to ~/Pictures/new"
tyranos run "copy all .py files to ~/code_backup"
tyranos run "copy every .csv file in ~/data to ~/data/backup"
```

### Move files and folders

```bash
tyranos run "move report.pdf to ~/archive"
tyranos run "move all .log files from /var/app to /var/app/logs"
tyranos run "move the file notes.txt to ~/Documents/notes"
tyranos run "move folder old_project to ~/archive"
tyranos run "move all zip files in ~/Downloads to ~/archive/zips"
```

---

## Rename and reorganise

### Rename a file or folder

```bash
tyranos run "rename file report.pdf to quarterly_report_Q1.pdf"
tyranos run "rename notes.txt to meeting_notes_2024.txt"
tyranos run "rename folder old_name to new_name"
tyranos run "rename directory src to source"
```

### Batch rename

```bash
tyranos run "rename all .jpeg files to .jpg in ~/Pictures"
tyranos run "rename all files in ~/exported by adding the prefix 2024_ to each"
tyranos run "rename all .txt files to .md in ~/notes"
tyranos run "lowercase all filenames in ~/downloads"
```

### Organise files into subfolders

```bash
tyranos run "move all PDF files into a subfolder called pdfs"
tyranos run "sort files in ~/Downloads into folders by extension"
tyranos run "organise photos in ~/Pictures by year and month"
tyranos run "group all Python files in ~/scripts into a src folder"
```

---

## Find and list

### List files and folders

```bash
tyranos run "list all files in ~/Documents"
tyranos run "show files in the current directory"
tyranos run "list all Python files in ~/Projects"
tyranos run "show all .log files in /var/log"
tyranos run "list folders in ~/Projects sorted by date"
```

### Find files

```bash
tyranos run "find all PDF files in ~/Documents"
tyranos run "find files larger than 100MB in ~/Downloads"
tyranos run "find all files modified in the last 24 hours in ~/Projects"
tyranos run "find all empty folders in ~/Projects"
tyranos run "find all files named config.json under ~/Projects"
```

### Check existence and size

```bash
tyranos run "check if the folder reports exists in ~/Documents"
tyranos run "verify that config.toml exists in the current directory"
tyranos run "show the size of the folder ~/Projects/myapp"
tyranos run "what is the total size of all files in ~/Downloads"
```

---

## System information

### Disk usage

```bash
tyranos run "show disk usage on /"
tyranos run "check how much space is available on /home"
tyranos run "show disk usage for all mounted drives"
tyranos run "which directories are using the most space in /var"
tyranos run "check disk space on all partitions"
```

### Memory and CPU

```bash
tyranos run "show current memory usage"
tyranos run "how much RAM is being used"
tyranos run "show CPU usage"
tyranos run "display system resource summary"
tyranos run "what percentage of RAM is free"
```

### OS and hardware

```bash
tyranos run "show OS version"
tyranos run "what kernel version is running"
tyranos run "show hostname and IP addresses"
tyranos run "display system uptime"
tyranos run "show CPU model and core count"
tyranos run "list all network interfaces"
```

---

## Process management

### List processes

```bash
tyranos run "show all running processes"
tyranos run "list processes sorted by CPU usage"
tyranos run "show processes using the most memory"
tyranos run "find processes named nginx"
tyranos run "show the top 10 processes by memory"
```

### Kill processes

```bash
tyranos run "kill process named firefox" --safe-mode
tyranos run "stop all processes matching python" --safe-mode
tyranos run "kill the process with PID 1234" --safe-mode
tyranos run "force-kill all zombie processes" --safe-mode
```

> Always use `--safe-mode` when killing processes to get a confirmation prompt before anything is terminated.

---

## Service management

### Start, stop, restart services

```bash
tyranos run "start the nginx service"
tyranos run "stop the postgresql service"
tyranos run "restart the application service"
tyranos run "reload the nginx configuration"
tyranos run "restart all failed services"
```

### Enable and disable on boot

```bash
tyranos run "enable nginx to start on boot"
tyranos run "disable the bluetooth service"
tyranos run "enable postgresql at startup"
```

### Check service status

```bash
tyranos run "check the status of the nginx service"
tyranos run "is postgresql running"
tyranos run "show all failed systemd services"
tyranos run "list all enabled services"
```

---

## User and permission management

### User accounts

```bash
tyranos run "create a user named deploy with a home directory"
tyranos run "add user deploy to the sudo group"
tyranos run "remove user old_account"
tyranos run "list all system users"
tyranos run "show which groups user deploy belongs to"
```

### File permissions

```bash
tyranos run "set permissions on ~/scripts/deploy.sh to executable"
tyranos run "make all .sh files in ~/scripts executable"
tyranos run "set the folder ~/app to be owned by the www-data user"
tyranos run "give read and write permissions to ~/shared to all users"
tyranos run "recursively set correct permissions on /var/www/html"
```

### Scheduled tasks (cron)

```bash
tyranos run "schedule a task to run backup.sh every day at 3am"
tyranos run "add a cron job to delete /tmp files every Sunday at midnight"
tyranos run "schedule cleanup.py to run at 2am on the first of every month"
tyranos run "list all scheduled cron jobs"
```

---

## Package management

### Install packages

```bash
tyranos run "install package vim"
tyranos run "install nginx and curl"
tyranos run "install Python packages requests, httpx, and pydantic"
tyranos run "install npm package express"
tyranos run "install the latest version of git"
tyranos run "install docker"
```

### Search and list

```bash
tyranos run "search for packages matching http client"
tyranos run "search for python packages matching async"
tyranos run "list all installed packages"
tyranos run "list all Python packages installed in this environment"
tyranos run "check if nginx is installed"
```

### Uninstall and update

```bash
tyranos run "uninstall package vim"
tyranos run "remove nginx and purge its config files"
tyranos run "update all system packages"
tyranos run "upgrade pip to the latest version"
tyranos run "update only security packages"
```

---

## Project generation

### Python

```bash
tyranos run "create a Python project named myapi"
tyranos run "generate a Python project with Flask and PostgreSQL"
tyranos run "create a FastAPI project with JWT auth and Docker support"
tyranos run "setup a Django project with REST framework"
tyranos run "create a Python package with tests, CI, and a README"
tyranos run "generate a Python CLI tool named myscript"
```

### Python virtual environment

```bash
tyranos run "create a virtual environment in ~/Projects/myapp"
tyranos run "setup a venv named .venv in the current directory"
tyranos run "create a virtualenv and install requirements.txt"
```

### C and C++

```bash
tyranos run "create a C project named calculator"
tyranos run "generate a C program named sorter that sorts an array"
tyranos run "create a C hello world program"
tyranos run "create a C++ project named image-processor with CMake"
```

### Java

```bash
tyranos run "create a Java project named inventory-system"
tyranos run "generate a Java Maven project named backend-api"
tyranos run "create a Spring Boot project named user-service"
```

### Hello World in any language

```bash
tyranos run "create a hello world program in Python"
tyranos run "create a hello world program in C"
tyranos run "create a hello world program in Go"
tyranos run "generate a hello world in Rust"
tyranos run "create a hello world in JavaScript"
```

### Node.js / JavaScript / TypeScript

```bash
tyranos run "create a Node.js Express API server"
tyranos run "generate a React app named my-dashboard"
tyranos run "create a React application with TypeScript and Jest"
tyranos run "setup a Next.js project with TailwindCSS"
tyranos run "create a Vue 3 project with Vite"
tyranos run "generate a Node.js CLI tool"
```

### Data science and analysis

```bash
tyranos run "create a data analysis project with pandas and matplotlib"
tyranos run "generate a machine learning project with scikit-learn"
tyranos run "create a Jupyter notebook project for EDA"
tyranos run "setup a data science environment with numpy, pandas, and seaborn"
```

### Web scraping

```bash
tyranos run "create a web scraping project using BeautifulSoup"
tyranos run "generate a Scrapy project for crawling product pages"
tyranos run "create a scraper project with Playwright and Python"
```

### With specific features

```bash
tyranos run "create a Python project with Redis caching, Celery workers, and Docker Compose"
tyranos run "generate a REST API with OpenAPI docs, database migrations, and pytest"
tyranos run "create a full-stack project with React frontend and FastAPI backend"
```

---

## Document generation

> Requires core dependencies (`python-docx`, `python-pptx`, `openpyxl`, `reportlab` — all included in the base install).

### Word documents (.docx)

```bash
tyranos run "create a Word document named quarterly-report.docx"
tyranos run "generate a Word document named meeting-agenda.docx with a title and bullet points"
tyranos run "create a Word document named proposal with an introduction and three sections"
tyranos run "write a Word document named contract.docx in ~/Documents"
tyranos run "generate a formatted Word report with headings and a table"
```

### PowerPoint presentations (.pptx)

```bash
tyranos run "create a PowerPoint presentation about AI trends"
tyranos run "generate a 5-slide presentation named company-intro.pptx"
tyranos run "create a PowerPoint deck with a title slide and 4 content slides"
tyranos run "make a presentation named sales-q1.pptx with charts and bullet points"
tyranos run "generate a product pitch deck in PowerPoint format"
```

### Excel spreadsheets (.xlsx)

```bash
tyranos run "create an Excel spreadsheet with columns for name, date, and amount"
tyranos run "generate an Excel file named sales-data.xlsx with sample rows"
tyranos run "create a budget spreadsheet with income and expense columns"
tyranos run "make an Excel worksheet with a header row and 10 data rows"
tyranos run "create an Excel report with summary and detail sheets"
tyranos run "generate a timesheet template in Excel format"
```

### PDF documents

```bash
tyranos run "generate a PDF invoice named invoice-001.pdf"
tyranos run "create a PDF report with a title and three sections"
tyranos run "generate a PDF resume template"
tyranos run "create a PDF with a cover page and table of contents"
```

### Save content to a document

```bash
tyranos run "save the text 'Project started on 2024-01-01' to a Word document named project-log.docx"
tyranos run "append a new row containing 'Alice, 2024-03, 5000' to sales.xlsx"
tyranos run "write the system info output to a Word document named system-report.docx"
```

---

## DevOps and infrastructure

### Docker

```bash
tyranos run "create a Dockerfile for my Python Flask app"
tyranos run "create a Dockerfile for a Node.js application"
tyranos run "generate a multi-stage Dockerfile for a Go binary"
tyranos run "create a Dockerfile that runs a FastAPI app on port 8000"
```

### Docker Compose

```bash
tyranos run "generate a docker-compose.yml with nginx, postgres, and redis"
tyranos run "create a docker-compose.yml with a web service and a PostgreSQL database"
tyranos run "add a Redis cache service to my docker-compose.yml"
tyranos run "create a docker-compose file for a full-stack app with a React frontend and a Node backend"
```

### Kubernetes

```bash
tyranos run "create a Kubernetes deployment YAML for my API service"
tyranos run "generate a Kubernetes service and ingress for my web app"
tyranos run "create a Kubernetes deployment with resource limits and readiness probes"
tyranos run "generate a Kubernetes ConfigMap and Secret for my app"
tyranos run "create a Helm chart for my microservice"
```

### CI/CD pipelines

```bash
tyranos run "configure a GitHub Actions CI pipeline for a Python project"
tyranos run "create a GitHub Actions workflow that runs tests on every push"
tyranos run "generate a GitLab CI pipeline with build, test, and deploy stages"
tyranos run "create a Jenkins pipeline for my Node.js app"
tyranos run "setup automated deployment to AWS on tag push using GitHub Actions"
```

### Terraform

```bash
tyranos run "generate Terraform config for an AWS EC2 instance"
tyranos run "create a Terraform file for an S3 bucket with versioning enabled"
tyranos run "generate Terraform config for a GCP Cloud Run service"
tyranos run "create a Terraform module for a VPC with public and private subnets"
```

### Monitoring

```bash
tyranos run "setup monitoring for my web application"
tyranos run "configure Prometheus and Grafana for my services"
tyranos run "create a health check script for my API endpoints"
tyranos run "setup log aggregation with the ELK stack"
tyranos run "generate alerting rules for high CPU and memory usage"
```

### Deploy and release

```bash
tyranos run "deploy the app"
tyranos run "release version 1.2.0"
tyranos run "publish the package to PyPI"
tyranos run "ship the latest build to production"
tyranos run "deploy the Docker image to the staging environment"
```

---

## Cloud deployment

### AWS

```bash
tyranos run "deploy the app to AWS"
tyranos run "deploy to AWS Elastic Beanstalk"
tyranos run "push the Docker image to AWS ECR"
tyranos run "create an S3 bucket named my-artifacts and upload the build"
tyranos run "deploy a Lambda function from lambda.zip"
```

### Google Cloud

```bash
tyranos run "deploy the application to GCP"
tyranos run "push the image to Google Container Registry"
tyranos run "deploy to Cloud Run with 2 replicas"
tyranos run "upload build artifacts to Google Cloud Storage"
```

### Azure

```bash
tyranos run "deploy the app to Azure"
tyranos run "push the Docker image to Azure Container Registry"
tyranos run "deploy to Azure App Service"
```

### Heroku

```bash
tyranos run "deploy the app to Heroku"
tyranos run "create a new Heroku app named my-service"
tyranos run "scale the Heroku web dyno to 2"
tyranos run "set the Heroku environment variable DATABASE_URL"
```

---

## Browser automation

> Requires `[web]` extras: `pip install -e ".[web]"` (Selenium + Playwright).

### Open and navigate

```bash
tyranos run "open https://example.com in a browser"
tyranos run "navigate to https://myapp.local/dashboard"
tyranos run "open https://example.com in headless Chrome"
```

### Interact with page elements

```bash
tyranos run "click the button with text 'Submit' on https://example.com/form"
tyranos run "fill in the username field on the login page with 'admin'"
tyranos run "type 'search query' into the search box on https://example.com"
tyranos run "click the first link in the navigation menu"
tyranos run "check the checkbox labelled 'Accept terms'"
tyranos run "select 'Option 2' from the dropdown menu"
```

### Take screenshots

```bash
tyranos run "open https://example.com and take a screenshot"
tyranos run "take a screenshot of https://myapp.local/dashboard and save as dashboard.png"
tyranos run "capture the full-page screenshot of https://example.com"
```

### Fill and submit forms

```bash
tyranos run "fill in the login form at https://myapp.local with username admin and password secret"
tyranos run "submit the contact form at https://example.com with name Alice and email alice@example.com"
tyranos run "fill out and submit the registration form at https://example.com/signup"
```

### Close browser

```bash
tyranos run "close the browser"
tyranos run "close all open browser windows"
```

---

## Web scraping

> Requires `beautifulsoup4` (included in base dependencies) and optionally `[web]` for JavaScript-rendered sites.

### Scrape a full page

```bash
tyranos run "scrape https://example.com and save the content"
tyranos run "scrape all text from https://example.com/article"
tyranos run "extract the main article text from https://news.example.com/story"
```

### Extract links

```bash
tyranos run "extract all links from https://example.com"
tyranos run "get all href links on https://example.com/resources"
tyranos run "find all external links on https://example.com"
tyranos run "list all PDF links on https://example.com/downloads"
```

### Extract images

```bash
tyranos run "extract all images from https://example.com"
tyranos run "get all image URLs from https://example.com/gallery"
tyranos run "download all images from the page at https://example.com/photos"
```

### Extract tables

```bash
tyranos run "scrape the first table from https://example.com/data"
tyranos run "extract all tables from https://example.com/stats and save as CSV"
tyranos run "get the pricing table from https://example.com/pricing"
```

### Search and extract

```bash
tyranos run "search example.com for 'python tutorial' and extract the first 5 results"
tyranos run "find all articles tagged 'automation' on https://example.com/blog"
tyranos run "scrape product names and prices from https://shop.example.com"
```

### Extract article content

```bash
tyranos run "extract the article text from https://example.com/post/123"
tyranos run "get the title, author, and body from https://blog.example.com/post"
tyranos run "extract and clean the article at https://news.example.com"
```

---

## File downloads and networking

### Download files

```bash
tyranos run "download https://example.com/file.zip to ~/Downloads"
tyranos run "fetch the file at https://example.com/data.csv and save to ~/data"
tyranos run "download the latest release from https://example.com/releases/latest"
```

### Check connectivity

```bash
tyranos run "check if google.com is reachable"
tyranos run "ping 8.8.8.8 and show the result"
tyranos run "test the connection to https://api.example.com/health"
tyranos run "check if port 5432 is open on localhost"
```

### API testing

```bash
tyranos run "test the GET endpoint https://api.example.com/users and show the response"
tyranos run "send a POST request to https://api.example.com/auth with username and password"
tyranos run "check the response time of https://api.example.com/health"
```

---

## Screenshots and UI control

### Take a screenshot

```bash
tyranos run "take a screenshot and save to ~/screenshots/now.png"
tyranos run "take a screenshot of the current screen"
tyranos run "capture the screen and save as screenshot.png on the Desktop"
```

### UI interaction (desktop)

```bash
tyranos run "click at position 100, 200 on the screen"
tyranos run "type 'hello world' into the currently focused window"
tyranos run "press the Enter key"
tyranos run "scroll down on the current window"
```

> Requires `[gui]` extras: `pip install -e ".[gui]"`. On headless Linux, set `DISPLAY` first.

---

## Security operations

### Vulnerability scanning

```bash
tyranos run "run a security scan on the current project"
tyranos run "scan for vulnerabilities in my Python dependencies"
tyranos run "check for known CVEs in requirements.txt"
tyranos run "run a vulnerability assessment on the application"
```

### SSL and certificates

```bash
tyranos run "setup SSL for my domain example.com"
tyranos run "generate a self-signed SSL certificate for localhost"
tyranos run "check when the SSL certificate for example.com expires"
tyranos run "renew the SSL certificate for my domain"
tyranos run "manage SSL certificates for my web server"
```

### Auditing and compliance

```bash
tyranos run "audit the system for security issues"
tyranos run "run a compliance check against CIS benchmarks"
tyranos run "check file permissions for sensitive configuration files"
tyranos run "audit all user accounts with sudo access"
tyranos run "scan for world-writable files in /etc"
```

### Security hardening

```bash
tyranos run "harden the system security configuration"
tyranos run "disable unused system services for security"
tyranos run "configure the firewall to allow only ports 22, 80, and 443"
tyranos run "enable fail2ban to block brute-force login attempts"
tyranos run "restrict SSH to key-based authentication only"
```

### Firewall management

```bash
tyranos run "configure the firewall to allow port 80"
tyranos run "block incoming connections on port 23"
tyranos run "allow traffic from IP 192.168.1.100"
tyranos run "show current firewall rules"
tyranos run "enable the firewall"
```

---

## Data and analytics

### Data processing

```bash
tyranos run "process the CSV file data.csv and calculate summary statistics"
tyranos run "filter rows in sales.csv where amount is greater than 1000"
tyranos run "merge dataset_a.csv and dataset_b.csv on the user_id column"
tyranos run "clean the data in customers.csv by removing duplicates and nulls"
```

### ETL and pipelines

```bash
tyranos run "setup a data pipeline to ingest CSV files from ~/data/incoming"
tyranos run "create an ETL pipeline that transforms JSON to CSV"
tyranos run "migrate data from the old PostgreSQL database to the new one"
tyranos run "setup a data pipeline from the REST API to a local SQLite database"
```

### Machine learning

```bash
tyranos run "train a classification model on the iris dataset"
tyranos run "run a machine learning pipeline on data.csv to predict churn"
tyranos run "generate a regression model for the housing price dataset"
tyranos run "run feature importance analysis on the training data"
```

### Analytics and visualisation

```bash
tyranos run "run analytics on the sales data and generate a report"
tyranos run "create a bar chart of monthly revenue from sales.csv"
tyranos run "setup a dashboard to visualise system metrics"
tyranos run "generate a summary report of the logs in /var/log/app"
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
tyranos n8n list
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
tyranos n8n create "every morning at 9am, send me an email with today's weather"
tyranos n8n create "every hour, check if the API at /health returns 200 and alert if not"
tyranos n8n create "every Friday afternoon, summarise this week's GitHub issues and post to Slack"
tyranos n8n create "daily at midnight, delete log files older than 7 days"
tyranos n8n create "every Monday morning, email a weekday briefing"
```

**Event-driven:**

```bash
tyranos n8n create "when a file appears in my S3 bucket, send a Slack notification"
tyranos n8n create "when a new row is added to the Google Sheet, create a Jira ticket"
tyranos n8n create "when a form is submitted, add the data to Airtable and send a welcome email"
tyranos n8n create "when a webhook is received from GitHub, run the CI pipeline"
tyranos n8n create "when a new Stripe payment arrives, log it and send a receipt"
```

**Data pipelines:**

```bash
tyranos n8n create "every day, fetch sales data from the API and write it to Google Sheets"
tyranos n8n create "sync new Stripe payments to QuickBooks every hour"
tyranos n8n create "every hour, pull metrics from Prometheus and write to a dashboard"
tyranos n8n create "when a customer signs up, add them to Mailchimp and create a CRM record"
```

### Trigger a workflow manually

```bash
tyranos n8n run <workflow-id>
```

### Check status

```bash
tyranos n8n status <workflow-id>
```

### Full lifecycle example

```bash
# 1. Create the workflow
tyranos n8n create "every day at midnight, archive old log files"

# 2. Note the ID printed, e.g. YUnR6qxyj0FveVOU
# 3. Test-trigger manually
tyranos n8n run YUnR6qxyj0FveVOU

# 4. Check the result
tyranos n8n status YUnR6qxyj0FveVOU

# 5. Activate in the n8n UI for recurring execution
```

---

## Custom Linux distro builder

> Requires Linux, root access, and `pip install -e ".[distro]"`.
> See [SETUP.md](SETUP.md) for host tool installation.

### List available profiles

```bash
tyranos distro profiles
```

### Estimate before building

Always estimate first — builds can take 20–60 min and use several GB of disk:

```bash
tyranos distro estimate --profile minimal
tyranos distro estimate --profile debian_base
```

### Build from a named profile

```bash
# Minimal headless Debian server
sudo tyranos distro build --profile minimal --output ~/isos/

# Full Debian base
sudo tyranos distro build --profile debian_base --output ~/isos/

# Custom output name
sudo tyranos distro build --profile debian_base --name "MyServer-1.0" --output ~/isos/
```

### Build from natural language

```bash
sudo tyranos distro build --nl "minimal Debian ISO with nginx and ssh, no GUI" --output ~/isos/
sudo tyranos distro build --nl "Arch Linux with KDE Plasma and gaming packages" --output ~/isos/
sudo tyranos distro build --nl "tiny headless Debian for a Raspberry Pi" --output ~/isos/
sudo tyranos distro build --nl "Debian server with Docker, Kubernetes tools, and Prometheus" --output ~/isos/
sudo tyranos distro build --nl "minimal buildroot image for an embedded ARM device" --output ~/isos/
```

### What gets built (10 stages)

1. Validate environment and check host tools
2. Fetch kernel source (cached in `~/.tyranos/kernel_cache`)
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
tyranos batch setup_workspace.txt
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
tyranos batch cleanup.txt --safe-mode
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
tyranos batch morning.txt
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
tyranos batch new_project.txt
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
tyranos batch monthly_reports.txt
```

### Batch run options

```bash
tyranos batch tasks.txt --stop-on-error    # halt on first failure
tyranos batch cleanup.txt --safe-mode      # confirm destructive steps
tyranos batch tasks.txt --debug            # verbose per-step output
tyranos --log-file ~/batch.jsonl batch tasks.txt  # structured log
```

---

## Chatbot / multi-turn mode

```bash
tyranos chatbot
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

Per-command flags (on `tyranos run` only):

| Flag | Description |
|------|-------------|
| `--safe-mode` | Override for this command |
| `--debug` | Override for this command |
| `--model` / `-m MODEL_ID` | Force a specific AI model |

### Examples

```bash
# Debug any subcommand
tyranos --debug run "create folder test"
tyranos --debug n8n list
tyranos --debug distro profiles

# Log everything to a file
tyranos --log-file ~/tyranos.jsonl batch morning.txt

# Safe mode for an entire batch run
tyranos --safe-mode batch cleanup.txt

# Force a specific model for one command
tyranos run "write a technical summary" -m openai/gpt-4o

# Combine multiple flags
tyranos --debug --safe-mode --log-file /tmp/tyranos.jsonl run "delete old backups"
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
tyranos run "create a folder named test"
tyranos run "make a directory named test"
tyranos run "mkdir test"
tyranos run "new folder test"
tyranos run "please create a folder called test"
tyranos run "can you create a directory called test"
```

---

## Tips

**Combine `--safe-mode` with batch files** for any workflow that touches important files or processes:

```bash
tyranos batch restore_prod.txt --safe-mode
```

**Use `--log-file` for auditing** — the JSON log contains every action taken:

```bash
tyranos --log-file ~/audit.jsonl batch production_tasks.txt
python -m json.tool < ~/audit.jsonl   # pretty-print
grep '"level":"ERROR"' ~/audit.jsonl  # filter errors only
```

**Explore interactively first, then automate** — use `tyranos chatbot` to validate sequences, then copy them into a batch file:

```bash
tyranos chatbot
# test your commands one by one
# then copy them into a batch file for repeatable execution
```

**Model selection** — Tyranos auto-picks the best free model. Override only when you need a specific capability:

```bash
tyranos run "translate this to French" -m openai/gpt-4o
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
