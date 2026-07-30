# Lab 1: SLO & Error Budget Dashboard \- Complete AWS Implementation Guide

## **Overview**

In this project, you'll deploy a containerized web application on AWS, instrument it with monitoring tools, define SLOs, and build a real-time dashboard to track reliability using SRE principles.

## **Architecture Diagram**

```
┌─────────────────────────────────────────────────────────┐
│                    AWS Region                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │   EC2       │  │   EC2       │  │   Security      │ │
│  │  Instance   │  │  Instance   │  │     Group       │ │
│  │  (App +     │  │ (Monitoring)│  │ (Firewall Rules)│ │
│  │   Node      │◄─┼─┤             │◄─┼─┤               │ │
│  │  Exporter)  │  │             │  │                 │ │
│  └──────┬──────┘  └──────┬──────┘  └─────────────────┘ │
│         │                │                             │
│  ┌──────▼──────┐  ┌──────▼──────┐                     │
│  │   Docker    │  │   Docker    │                     │
│  │  Container  │  │  Containers │                     │
│  │   (App)     │  │ (Prometheus,│                     │
│  │             │  │   Grafana)  │                     │
│  └─────────────┘  └─────────────┘                     │
└─────────────────────────────────────────────────────────┘
         │                         │
    HTTP/Health              Metrics Scraping
         │                         │
    ┌────▼─────────────────────────▼────┐
    │           Internet User           │
    └───────────────────────────────────┘
```

## **Prerequisites**

- AWS Account (Free Tier eligible)
- Basic understanding of Linux commands
- Docker basics
- SSH client (for Mac/Linux: built-in, for Windows: PuTTY or WSL)

---

## **Phase 1: AWS Infrastructure Setup**

### **Step 1.1: Create Security Group**

**Purpose:** Configure firewall rules for our instances.

1. **Log into AWS Console**
    - Navigate to <https://console.aws.amazon.com>
    - Select your preferred region (us-east-1 recommended for free tier)
2. **Create Security Group**
    - Go to **EC2** → **Security Groups** → **Create security group**
    - Name: `sre-project-sg`
    - Description: `Security group for SRE Project 1`
    - VPC: Use default VPC
3. **Add Inbound Rules:**

```
Type            Protocol    Port Range    Source          Description
────────────────────────────────────────────────────────────────
SSH             TCP         22            0.0.0.0/0       Admin access
Custom TCP      TCP         3000          0.0.0.0/0       Grafana UI
Custom TCP      TCP         9090          0.0.0.0/0       Prometheus UI
Custom TCP      TCP         9100          0.0.0.0/0       Node Exporter
Custom TCP      TCP         8080          0.0.0.0/0       Sample App
HTTP            TCP         80            0.0.0.0/0       Web access
All Traffic     All         All           sg-xxxx         Internal SG
```
    - **Note:** For production, restrict IP ranges. For learning, 0.0.0.0/0 is fine.
4. Click **Create security group**

### **Step 1.2: Launch EC2 Instance for Application**

**Purpose:** Host our containerized application and Node Exporter.

1. **Navigate to EC2 Dashboard**
    - Click **Launch Instance**
2. **Configure Instance:**
    - **Name:** `sre-app-server`
    - **AMI:** Ubuntu Server 22.04 LTS (Free Tier eligible)
    - **Instance type:** t2.micro (Free Tier eligible)
    - **Key pair:** Create new or use existing
        - Key pair name: `sre-project-key`
        - Download .pem file and secure it: `chmod 400 sre-project-key.pem`
    - **Network settings:**
        - VPC: Default
        - Subnet: No preference
        - Auto-assign public IP: Enable
        - Firewall: Select existing security group → Choose `sre-project-sg`
    - **Configure storage:** 8GB gp2 (Free Tier: 30GB free)
3. **Launch Instance**
    - Click **Launch Instance**
    - Note the **Public IPv4 DNS** (e.g., `ec2-xx-xx-xx-xx.compute-1.amazonaws.com`)

### **Step 1.3: Launch EC2 Instance for Monitoring Stack**

**Purpose:** Host Prometheus and Grafana.

1. **Repeat Step 1.2 with these changes:**
    - **Name:** `sre-monitoring-server`
    - **Instance type:** t2.small (better performance for monitoring)
    - **Key pair:** Use same `sre-project-key`
    - **Security group:** Same `sre-project-sg`
    - **Storage:** 16GB gp2
2. **Wait for both instances to show status "2/2 checks passed"**

---

## **Phase 2: Application Setup & Containerization**

### **Step 2.1: SSH to App Server**

```bash
# On your local machine
ssh -i "sre-project-key.pem" ubuntu@<APP_SERVER_PUBLIC_DNS>
```

### **Step 2.2: Install Docker on App Server**

Update the server

```
# Update system
sudo apt update && sudo apt upgrade -y
```

Install docker

```bash
# Install Docker
sudo apt install ca-certificates curl gnupg lsb-release -y
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y

# Add user to docker group (avoid sudo for docker commands)
sudo usermod -aG docker ubuntu
exit
```

### **Step 2.3: Create Sample Application**

**Purpose:** Build a simple Python web app with Prometheus metrics.

1. SSH back into the instance

```
ssh -i "sre-project-key.pem" ubuntu@<APP_SERVER_PUBLIC_DNS>
```

1. **Create application directory:**

```bash
mkdir -p /home/ubuntu/sre-app && cd /home/ubuntu/sre-app
```

1. **Create **`app.py`:

```
vi app.py
```

1. Copy and paste the content below into the `app.py` file

```py
#!/usr/bin/env python3
from flask import Flask, Response
from prometheus_client import generate_latest, Counter, Histogram, Gauge
import random
import time
import os

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status_code'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['endpoint'])
ERROR_COUNT = Counter('http_errors_total', 'Total HTTP Errors', ['endpoint'])
APP_VERSION = Gauge('app_version', 'Application version info', ['version'])
HEALTH = Gauge('app_health', 'Application health status')

# Set version from environment or default
version = os.getenv('APP_VERSION', '1.0.0')
APP_VERSION.labels(version=version).set(1)
HEALTH.set(1)  # Start healthy

@app.route('/')
def hello():
    with REQUEST_LATENCY.labels(endpoint='/').time():
        # Simulate occasional errors (5% error rate)
        if random.random() < 0.05:
            ERROR_COUNT.labels(endpoint='/').inc()
            REQUEST_COUNT.labels(method='GET', endpoint='/', status_code='500').inc()
            return "Internal Server Error", 500
        
        # Simulate variable latency (50-200ms)
        time.sleep(random.uniform(0.05, 0.2))
        
        REQUEST_COUNT.labels(method='GET', endpoint='/', status_code='200').inc()
        return f"""
        <h1>Cloud Engineering Sample App</h1>
        <p>Version: {version}</p>
        <p>This is a sample application for SRE training.</p>
        <ul>
            <li><a href="/metrics">Metrics</a></li>
            <li><a href="/health">Health Check</a></li>
            <li><a href="/slow">Slow Endpoint</a></li>
            <li><a href="/error">Error Endpoint</a></li>
        </ul>
        """

@app.route('/slow')
def slow():
    with REQUEST_LATENCY.labels(endpoint='/slow').time():
        # Simulate slow response (1-3 seconds)
        time.sleep(random.uniform(1, 3))
        REQUEST_COUNT.labels(method='GET', endpoint='/slow', status_code='200').inc()
        return "Slow endpoint response (simulated latency)"

@app.route('/error')
def error():
    with REQUEST_LATENCY.labels(endpoint='/error').time():
        ERROR_COUNT.labels(endpoint='/error').inc()
        REQUEST_COUNT.labels(method='GET', endpoint='/error', status_code='500').inc()
        return "Simulated Error", 500

@app.route('/health')
def health():
    REQUEST_COUNT.labels(method='GET', endpoint='/health', status_code='200').inc()
    return "OK", 200

@app.route('/metrics')
def metrics():
    REQUEST_COUNT.labels(method='GET', endpoint='/metrics', status_code='200').inc()
    return Response(generate_latest(), mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

1. **Create **`requirements.txt`:

```
vi requirements.txt
```

1. Copy and paste the content below into the `requirements.txt` file

```txt
flask>=2.0.0
prometheus-client>=0.12.0
```

1. **Create **`Dockerfile`:

```
vi Dockerfile
```

1. Copy and paste the content below into the `Dockerfile` file

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

EXPOSE 8080

ENV APP_VERSION=1.0.0

CMD ["python", "app.py"]
```

1. **Create **`docker-compose.yml` for app and Node Exporter:

```
vi docker-compose.yml
```

1. Copy and paste the content below into the `docker-compose.yml` file

```yaml
version: '3.8'

services:
  webapp:
    build: .
    container_name: sre-webapp
    ports:
      - "8080:8080"
    environment:
      - APP_VERSION=1.0.0
    restart: unless-stopped
    networks:
      - monitoring

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter
    command:
      - '--path.rootfs=/host'
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    ports:
      - "9100:9100"
    restart: unless-stopped
    networks:
      - monitoring

networks:
  monitoring:
    driver: bridge
```

### **Step 2.4: Build and Deploy Application**

```bash
# Build Docker image
docker build -t sre-webapp .

# Deploy with Docker Compose
docker compose up -d

# Verify containers are running
docker ps
```

### **Step 2.5: Test the application**

```
curl http://localhost:8080
curl http://localhost:8080/health
curl http://localhost:8080/metrics
```

---

## **Phase 3: Monitoring Stack Setup**

### **Step 3.1: SSH to Monitoring Server**

```bash
# Open new terminal
ssh -i "sre-project-key.pem" ubuntu@<MONITORING_SERVER_PUBLIC_DNS>
```

### **Step 3.2: Install Docker on Monitoring Server**

Update the server

```
# Update system
sudo apt update && sudo apt upgrade -y
```

Install docker

```bash
# Install Docker
sudo apt install ca-certificates curl gnupg lsb-release -y
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y

# Add user to docker group (avoid sudo for docker commands)
sudo usermod -aG docker ubuntu
exit
```

### **Step 3.3: Create Prometheus Configuration**

1. SSH back into the instance

```
ssh -i "sre-project-key.pem" ubuntu@<MONITORING_SERVER_PUBLIC_DNS>
```

1. **Create directory structure:**

```bash
mkdir -p /home/ubuntu/monitoring && cd /home/ubuntu/monitoring
```

1. **Create **`prometheus.yml`:

```
vi prometheus.yml
```

1. Copy and paste the content below into the `prometheus.yml` file

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

# SLO Configuration
rule_files:
  - "slo_rules.yml"

# Alerting configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets: []

scrape_configs:
  # Monitor Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Monitor the web application
  - job_name: 'webapp'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['<APP_SERVER_PRIVATE_IP>:8080']
        labels:
          service: 'sample-app'
          environment: 'learning'

  # Monitor node metrics from app server
  - job_name: 'node-app-server'
    static_configs:
      - targets: ['<APP_SERVER_PRIVATE_IP>:9100']
        labels:
          service: 'sample-app'
          environment: 'learning'
          instance: 'app-server'

  # Monitor node metrics from monitoring server
  - job_name: 'node-monitoring-server'
    static_configs:
      - targets: ['localhost:9100']
        labels:
          service: 'monitoring'
          environment: 'learning'
          instance: 'monitoring-server'
```

**Important:** Replace `<APP_SERVER_PRIVATE_IP>` with your app server's private IP.  
Find it with: In AWS Console → EC2 → Instances → sre-app-server → Details → Private IPv4 addresses.

1. **Create **`slo_rules.yml`:

```
vi slo_rules.yml
```

1. Copy and paste the content below into the `slo_rules.yml` file

```yaml
groups:
  - name: slo_rules
    interval: 1m
    rules:
      # Record availability SLI (28-day rolling window)
      - record: slo:availability_28d
        expr: >
          sum(rate(http_requests_total{job="webapp", status_code=~"2.."}[28d]))
          /
          sum(rate(http_requests_total{job="webapp"}[28d]))
      
      # Record availability SLI (1-hour window for testing)
      - record: slo:availability_1h
        expr: >
          sum(rate(http_requests_total{job="webapp", status_code=~"2.."}[1h]))
          /
          sum(rate(http_requests_total{job="webapp"}[1h]))
      
      # Error budget (99.5% SLO)
      - record: slo:error_budget_remaining_28d
        expr: (1 - (1 - slo:availability_28d) / (1 - 0.995))
      
      # Error budget burn rate (5-minute)
      - record: slo:error_budget_burn_rate_5m
        expr: >
          (1 - slo:availability_1h)
          /
          (1 - 0.995)
      
      # Latency SLI (p95 under 500ms)
      - record: slo:latency_p95_1h
        expr: >
          histogram_quantile(0.95,
            sum(rate(http_request_duration_seconds_bucket{job="webapp"}[1h]))
            by (le))
```

1. **Create **`docker-compose.yml` for monitoring stack:

```
vi docker-compose.yml
```

1. Copy and paste the content below into the `docker-compose.yml` file

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./slo_rules.yml:/etc/prometheus/slo_rules.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=15d'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    restart: unless-stopped
    networks:
      - monitoring

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    ports:
      - "3000:3000"
    restart: unless-stopped
    networks:
      - monitoring

  node-exporter:
    image: prom/node-exporter:latest
    container_name: node-exporter-monitoring
    command:
      - '--path.rootfs=/host'
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    ports:
      - "9100:9100"
    restart: unless-stopped
    networks:
      - monitoring

volumes:
  prometheus_data:
  grafana_data:

networks:
  monitoring:
    driver: bridge
```

### **Step 3.4: Start Monitoring Stack**

```bash
# Deploy monitoring stack
docker compose up -d

# Verify all containers are running
docker ps
```

### **Step 3.5: Check Prometheus targets (should see webapp and node exporters)**

```
# Wait 30 seconds, then check:
curl http://localhost:9090/api/v1/targets | python3 -m json.tool
```

---

## **Phase 4: Configure Datasource on Grafana**

### **Step 4.1: Access Grafana**

1. **Open browser and go to:**

```
http://<MONITORING_SERVER_PUBLIC_DNS>:3000
```
2. **Login:**
    - Username: `admin`
    - Password: `admin123`

### **Step 4.2: Add Prometheus Data Source**

1. **Navigate to:**
    - Connections (gear icon) → Data Sources → Add data source
2. **Select Prometheus**
3. **Configure:**
    - Name: `Prometheus`
    - URL: `<http://prometheus:9090`\> (container-to-container communication)
    - Click **Save & Test** (should show "Data source is working")

## **Phase 5: Configure Grafana Dashboard**

## Approach 1: Build the SRE Dashboard via Grafana UI (Step-by-Step)

### Create a new dashboard

1. In Grafana, left sidebar → **“+ Create” → “Dashboard”**.
2. Click **“Add Visualization”**.
3. Select your data source - **prometheus**

### Panel 1 – Availability (28d) vs SLO (stat gauge)

**Goal:** Show long-window availability SLI against the 99.5% SLO.

1. Panel title: `Availability (28d)`.
2. Data source: **your Prometheus datasource**.
3. Query:

```
slo:availability_28d
```
4. Change **Panel type** → **Stat** (or Gauge, your choice).
5. Under **Field → Standard options**:
    - Unit: `percent (0-1)` (or `percentunit` depending on Grafana version).
    - Min: `0`
    - Max: `1`
6. Under **Thresholds** (so you can see SLO visually):
    - Add step: `0` → red
    - Add step: `0.995` → orange (your SLO)
    - Add step: `0.999` → green
7. Save panel.
8. Give your dashboard a name like SLO DASHBOARD

This panel answers: **“Are we above 99.5% over the last 28 days?”**

### Panel 2 – Availability SLI (1h rolling) with SLO line

**Goal:** Short-window SLI to see current behaviour vs target.

1. Add another panel → title: `Availability (1h rolling)`.
2. Panel type: **Time series**.
3. Queries:
    - A – 1h availability:

```
slo:availability_1h
```
    - B – SLO line:

```
0.995
```
4. Legend: set A = `1h SLI`, B = `SLO 99.5%`.
5. Field → Unit: `percent (0-1)`; Min = 0, Max = 1.
6. Thresholds (optional, same as Panel 1).
7. Save.

This panel shows **how your availability is trending hourly against the SLO**.

### Panel 3 – Error Budget Remaining (28d)

**Goal:** Track how much of the error budget is left.

1. Add panel → title: `Error Budget Remaining (28d)`.
2. Type: **Stat**.
3. Query:

```
1 - (1 - slo:availability_28d) / (1 - 0.995)
```
4. Unit: `percent (0-1)`.
5. Threshold examples:
    - 0 → red
    - 0.25 → orange (only 25% budget left)
    - 0.5 → green (healthy).
6. Save.

This gives a **single number between 0 and 1** = fraction of budget remaining.

### Panel 4 – Error Budget Burn Rate (5m / 28d)

**Goal:** Burn rate monitoring.

1. Add panel → title: `Error Budget Burn Rate (5m / 28d)`.
2. Type: **Time series**.
3. Queries:
    - A:

```
slo:error_budget_burn_rate_5m
```
    - B: steady burn line (1x)

```
1
```
    - C: fast burn line (2x)

```
2
```
4. Unit: `none`.
5. Thresholds:
    - \< 1 → green
    - 1–2 → orange
    - 2 → red
6. Save.

Now you can answer: **“Are we burning error budget too fast?”**

### Panel 5 – Latency SLI (p95)

1. Add panel → title: `Latency p95 (1h)`.
2. Type: **Time series**.
3. Queries:
    - A:

```
slo:latency_p95_1h
```
    - B: SLO line for 500ms:

```
0.5
```
4. Unit: `seconds`.
5. Thresholds:
    - 0 → green
    - 0.5 → orange
    - 1 → red
6. Save the panel and then **Save Dashboard**.

You now have an SRE dashboard covering:

- **Availability SLI** (28d + 1h)
- **SLO (99.5%)** visualized
- **Error budget remaining**
- **Burn rate**
- **Latency SLI (p95)**

---

## Approach 2: Use a Complete Dashboard JSON (Import in Grafana)

Below is a **ready-to-import dashboard JSON** that creates those panels for you.

Before importing, replace `“uid“: “YOUR_PROM_DS_UID“`with your Prometheus datasource UID in Grafana (or edit easch panel’s datasource after import).

### 1. How to import

1. In Grafana, left sidebar → **Dashboards**.
2. Click **“New” → “Import”**.
3. In the **“Import via JSON” **section.
4. Paste the JSON below.
5. Click **“Load”**, then select your Prometheus datasource if Grafana prompts.
6. Then click **Import.**

---

### 2. Dashboard JSON

```json
{
  "uid": "sre-slo-dashboard",
  "title": "SRE SLO Dashboard",
  "schemaVersion": 39,
  "version": 1,
  "time": { "from": "now-30d", "to": "now" },
  "timepicker": {},
  "timezone": "",
  "editable": true,
  "graphTooltip": 0,
  "annotations": {
    "list": [
      {
        "builtIn": 1,
        "datasource": { "type": "grafana", "uid": "-- Grafana --" },
        "enable": true,
        "hide": true,
        "iconColor": "rgba(0, 211, 255, 1)",
        "name": "Annotations & Alerts",
        "type": "dashboard"
      }
    ]
  },
  "templating": { "list": [] },
  "panels": [
    {
      "id": 1,
      "type": "stat",
      "title": "Availability (28d)",
      "datasource": { "type": "prometheus", "uid": "YOUR_PROM_DS_UID" },
      "gridPos": { "h": 6, "w": 6, "x": 0, "y": 0 },
      "options": {
        "reduceOptions": { "calcs": ["lastNotNull"], "fields": "", "values": false },
        "orientation": "horizontal",
        "colorMode": "value",
        "graphMode": "none",
        "justifyMode": "auto",
        "textMode": "auto"
      },
      "fieldConfig": {
        "defaults": {
          "unit": "percentunit",
          "min": 0,
          "max": 1,
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "red", "value": 0 },
              { "color": "orange", "value": 0.995 },
              { "color": "green", "value": 0.999 }
            ]
          }
        },
        "overrides": []
      },
      "targets": [
        {
          "expr": "slo:availability_28d",
          "legendFormat": "28d availability",
          "refId": "A"
        }
      ]
    },
    {
      "id": 3,
      "type": "stat",
      "title": "Error Budget Remaining (28d)",
      "datasource": { "type": "prometheus", "uid": "YOUR_PROM_DS_UID" },
      "gridPos": { "h": 6, "w": 6, "x": 6, "y": 0 },
      "options": {
        "reduceOptions": { "calcs": ["lastNotNull"], "fields": "", "values": false },
        "orientation": "horizontal",
        "colorMode": "value",
        "graphMode": "none",
        "justifyMode": "auto",
        "textMode": "auto"
      },
      "fieldConfig": {
        "defaults": {
          "unit": "percentunit",
          "min": 0,
          "max": 1,
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "red", "value": 0 },
              { "color": "orange", "value": 0.25 },
              { "color": "green", "value": 0.5 }
            ]
          }
        },
        "overrides": []
      },
      "targets": [
        {
          "expr": "1 - (1 - slo:availability_28d) / (1 - 0.995)",
          "legendFormat": "Error budget remaining",
          "refId": "A"
        }
      ]
    },
    {
      "id": 2,
      "type": "timeseries",
      "title": "Availability (1h rolling)",
      "datasource": { "type": "prometheus", "uid": "YOUR_PROM_DS_UID" },
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 6 },
      "fieldConfig": {
        "defaults": {
          "unit": "percentunit",
          "min": 0,
          "max": 1,
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "red", "value": 0 },
              { "color": "orange", "value": 0.995 },
              { "color": "green", "value": 0.999 }
            ]
          }
        },
        "overrides": []
      },
      "options": {
        "legend": { "displayMode": "table", "placement": "bottom" },
        "tooltip": { "mode": "single", "sort": "none" }
      },
      "targets": [
        {
          "expr": "slo:availability_1h",
          "legendFormat": "1h SLI",
          "refId": "A"
        },
        {
          "expr": "0.995",
          "legendFormat": "SLO 99.5%",
          "refId": "B"
        }
      ]
    },
    {
      "id": 4,
      "type": "timeseries",
      "title": "Error Budget Burn Rate (5m / 28d)",
      "datasource": { "type": "prometheus", "uid": "YOUR_PROM_DS_UID" },
      "gridPos": { "h": 8, "w": 12, "x": 12, "y": 6 },
      "fieldConfig": {
        "defaults": {
          "unit": "none",
          "min": 0,
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "green", "value": 0 },
              { "color": "orange", "value": 1 },
              { "color": "red", "value": 2 }
            ]
          }
        },
        "overrides": []
      },
      "options": {
        "legend": { "displayMode": "table", "placement": "bottom" },
        "tooltip": { "mode": "single", "sort": "none" }
      },
      "targets": [
        {
          "expr": "slo:error_budget_burn_rate_5m",
          "legendFormat": "5m burn rate",
          "refId": "A"
        },
        {
          "expr": "1",
          "legendFormat": "steady burn",
          "refId": "B"
        },
        {
          "expr": "2",
          "legendFormat": "fast burn (x2)",
          "refId": "C"
        }
      ]
    },
    {
      "id": 5,
      "type": "timeseries",
      "title": "Latency p95 (1h)",
      "datasource": { "type": "prometheus", "uid": "YOUR_PROM_DS_UID" },
      "gridPos": { "h": 8, "w": 12, "x": 0, "y": 14 },
      "fieldConfig": {
        "defaults": {
          "unit": "s",
          "min": 0,
          "thresholds": {
            "mode": "absolute",
            "steps": [
              { "color": "green", "value": 0 },
              { "color": "orange", "value": 0.5 },
              { "color": "red", "value": 1 }
            ]
          }
        },
        "overrides": []
      },
      "options": {
        "legend": { "displayMode": "table", "placement": "bottom" },
        "tooltip": { "mode": "single", "sort": "none" }
      },
      "targets": [
        {
          "expr": "slo:latency_p95_1h",
          "legendFormat": "p95 latency",
          "refId": "A"
        },
        {
          "expr": "0.5",
          "legendFormat": "SLO 500ms",
          "refId": "B"
        }
      ]
    }
  ]
}
```

---

## **Phase 6: Testing & Validation**

### **Step 6.1: Generate Traffic to Test SLOs**

**On your local machine, run these tests:**

1. **Basic Health Check:**

```bash
APP_URL="http://<APP_SERVER_PUBLIC_DNS>:8080"
curl $APP_URL/health
```

1. **Generate Normal Traffic:**

```bash
# Using hey tool (install: go install github.com/rakyll/hey@latest)
hey -z 300s -c 5 $APP_URL

# Or using simple loop
for i in {1..100}; do
  curl -s $APP_URL > /dev/null
  sleep 1
done
```

1. **Generate Errors (Consume Error Budget):**

```bash
# Hit error endpoint
for i in {1..50}; do
  curl -s $APP_URL/error > /dev/null
  sleep 0.5
done
```

### **Step 6.2: Observe Dashboard Changes**

1. **Refresh Grafana dashboard**
2. **Observe:**
    - Availability gauge drops below 99.5%
    - Error budget burn rate increases (turns yellow/red)
    - Error budget remaining decreases
    - Error spikes appear in Request Rate panel

### **Step 6.3: Simulate Service Disruption**

```bash
# SSH to app server
ssh -i "sre-project-key.pem" ubuntu@<APP_SERVER_PUBLIC_DNS>

# Stop the application
docker stop sre-webapp

# Wait 2 minutes, then restart
sleep 120
docker start sre-webapp
```

**Observe in Grafana:**

- Availability drops to 0%
- Error budget burn rate spikes
- All panels show the outage impact

---

## **Phase 7: SLO Documentation**

### **Create SLO Document**

**On monitoring server:**

```bash
cd ~/monitoring
cat > SLO_DOCUMENTATION.md << 'EOF'
# SLO Documentation

## Overview
This document defines the Service Level Indicators (SLIs), Service Level Objectives (SLOs), error budget policy, and monitoring strategy for the application. It also explains how availability, latency, and error budget burn rates are calculated and surfaced through dashboards.

---

## 1. Service Overview
The application exposes HTTP endpoints and exports Prometheus metrics describing request volume, errors, and latency. These metrics allow us to accurately measure and track user experience.

The SRE dashboard monitors:
- **Availability SLI**
- **Latency SLI (p95)**
- **99.5% availability SLO compliance**
- **Error budget remaining**
- **Burn-rate alerts and monitoring**

---

## 2. Service Level Indicators (SLIs)
SLIs are quantitative measures of user experience quality.

### 2.1 Availability SLI
Availability measures the proportion of successful (2xx) HTTP responses out of all received requests.

**Formula:**
```
Availability = Successful Requests (2xx) / Total Requests
```

**PromQL:**
```
sum(rate(http_requests_total{status_code=~"2.."}[5m]))
  /
sum(rate(http_requests_total[5m]))
```

### 2.2 Latency SLI (p95)
Latency measures how long requests take to process. We use the 95th percentile (p95) to reflect user-perceived latency.

**Formula:**
```
p95 = histogram_quantile(0.95, request_duration_histogram)
```

**PromQL:**
```
histogram_quantile(
  0.95,
  sum(rate(http_request_duration_seconds_bucket[1h])) by (le)
)
```

---

## 3. Service Level Objectives (SLOs)
SLOs define the target performance level the service must maintain.

### 3.1 Availability SLO
The service must meet:

**➡️ 99.5% availability over a 28‑day rolling window**

This means:
```
Allowed downtime/unavailability = 0.5%
```

### 3.2 Latency SLO
**➡️ p95 latency must remain below 500ms (0.5s)**

This ensures that 95% of user requests feel fast and responsive.

---

## 4. Error Budget Policy
Because the availability SLO is **99.5%**, the error budget is:

```
Error Budget = 1 - SLO = 0.005 (0.5%)
```

### 4.1 Error Budget Remaining
Shows how much of the error budget is still unused.

**PromQL:**
```
1 - (1 - slo:availability_28d) / (1 - 0.995)
```

### 4.2 Error Budget Consumption Rules
- If **>50% budget remains** → normal feature release velocity.
- If **25–50% remains** → caution; evaluate risky deployments.
- If **<25% remains** → reliability review required.
- If **0% remains** → freeze changes until stability returns.

---

## 5. Burn Rate Monitoring
Burn rate indicates **how quickly** the service is consuming its error budget.

### 5.1 Burn Rate SLI
Calculated over short windows (5m, 1h) to detect rapid degradation.

**PromQL:**
```
slo:error_budget_burn_rate_5m
```

### 5.2 Burn Rate Alert Guidelines
| Burn Rate | Meaning | Action |
|----------|---------|--------|
| <1 | Normal burn | All good |
| 1–2 | Elevated consumption | Investigate ongoing issues |
| >2 | Critical | Immediate mitigation required |

High burn rates can exhaust the entire monthly budget quickly, so rapid response is essential.

---

## 6. Monitoring & Dashboard Panels
The SRE Grafana dashboard surfaces the following panels:

### 6.1 Availability (28d)
Shows long-term SLO performance and compliance.

### 6.2 Availability (1h)
Shows short-term SLI behavior to detect active degradation.

### 6.3 Error Budget Remaining
Indicates whether the service can safely accept new changes.

### 6.4 Burn Rate (5m / 28d)
Detects outages or error spikes early.

### 6.5 Latency p95
Measures user-perceived performance and responsiveness.

---

## 7. Summary
This SLO framework ensures:
- Clear expectations for service reliability
- Objective measurement of user experience
- A balance between innovation and stability using error budgets
- Early detection of incidents using burn-rate monitoring

These SLOs empower engineering teams to maintain a healthy service while moving quickly and safely.

---

## 8. Future Improvements
Potential enhancements include:
- Per-endpoint SLOs
- Multi-window burn rate alerts (5m/30m and 1h/6h)
- Release-impact correlation
- Automatically updated SLO compliance reports

EOF
```

---

## **Phase 7: Cleanup (Optional but Important)**

### **To avoid AWS charges:**

```bash
# 1. Stop all Docker containers
# On app server:
docker compose down

# On monitoring server:
docker compose down

# 2. Terminate EC2 instances in AWS Console
# EC2 → Instances → Select instances → Instance state → Terminate

# 3. Delete security group
# EC2 → Security Groups → Select sre-project-sg → Delete

# 4. Delete key pair
# EC2 → Key Pairs → Select sre-project-key → Delete
```

---

## **Troubleshooting Guide**

### **Common Issues:**

1. **Cannot connect to EC2 via SSH:**
    - Verify key permissions: `chmod 400 sre-project-key.pem`
    - Check security group inbound rules
    - Ensure instance is running (2/2 status checks)
2. **Prometheus cannot scrape targets:**
    - Verify IP addresses in prometheus.yml
    - Check app server's security group allows port 8080 from monitoring server
    - Test connectivity: `nc -zv <APP_SERVER_PRIVATE_IP> 8080`
3. **Grafana cannot connect to Prometheus:**
    - Verify Prometheus container is running: `docker ps`
    - Check Prometheus URL in Grafana data source
    - Test: `curl <http://localhost:9090`\> from monitoring server
4. **No metrics appearing:**
    - Wait 1-2 minutes for initial scrape
    - Check Prometheus targets: \<http://\<MONITORING\_SERVER\>\>:9090/targets
    - Verify app exposes metrics: \<http://\<APP\_SERVER\>\>:8080/metrics

### **Useful Commands for Debugging:**

```bash
# Check Docker logs
docker logs sre-webapp
docker logs prometheus
docker logs grafana

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq .

# Force reload Prometheus config
curl -X POST http://localhost:9090/-/reload

# Test application endpoints
curl -v http://localhost:8080/health
curl http://localhost:8080/metrics | head -20

# Monitor real-time logs
docker logs -f prometheus
```

---

## **Learning Outcomes**

By completing this project, you've implemented:

1. ✅ **Infrastructure as Code**: AWS resources via console (next step: Terraform)
2. ✅ **Containerization**: Dockerized application with proper health checks
3. ✅ **Monitoring**: Prometheus metrics collection from application and system
4. ✅ **Observability**: Grafana dashboards for visualization
5. ✅ **SRE Fundamentals**: 
    - Availability SLI
    - Latency SLI (p95)
    - 99.5% availability SLO compliance
    - Error budget remaining
    - Burn-rate alerts and monitoring
6. ✅ **Real-world testing**: Simulated failures and observed impact on SLOs

## **Next Steps for Learners**

1. **Extend**: Add more SLIs (throughput, saturation)
2. **Improve**: Replace manual setup with Terraform/CloudFormation
3. **Scale**: Add a load balancer and multiple app instances
4. **Automate**: Create scripts for automated deployment
5. **Secure**: Implement HTTPS, proper authentication
6. **Alert**: Add Alertmanager for notifications (Project 2)

---

**Estimated Time to Complete:** 2-3 hours    
**AWS Cost (if left running):** \~$0.10-0.15 per day (Free Tier covers most)    
**Real-world Skills Gained:** 8+ critical SRE/DevOps competencies

This detailed guide provides a production-like setup that learners can experiment with, break, and learn from—all within AWS Free Tier limits.
