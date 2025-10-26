# Deployment Guide for Aristotle-I

Complete deployment guide for Aristotle-I on **GCP, AWS, Azure, Kubernetes, and Local Docker**.

**Quick Links**:
- 🏃 **Quick Start**: See `START.md`
- 🐳 **Local Docker**: Jump to [Local Docker Deployment](#local-docker-deployment)
- ☁️ **Cloud Deployment**: Choose [GCP](#gcp-deployment), [AWS](#aws-deployment), or [Azure](#azure-deployment)
- 🐳 **Kubernetes**: Jump to [Kubernetes sections](#kubernetes-deployment)

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Docker & Local Setup](#docker--local-setup)
3. [GCP Deployment](#gcp-deployment)
4. [AWS Deployment](#aws-deployment)
5. [Azure Deployment](#azure-deployment)
6. [Kubernetes Deployment](#kubernetes-deployment)
7. [Configuration Reference](#configuration-reference)
8. [Security Best Practices](#security-best-practices)
9. [Monitoring & Logging](#monitoring--logging)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before deploying Aristotle-I, ensure you have the following:

### Required Tools
- **Docker** (version 20.10+)
- **Cloud SDK** (gcloud for GCP, aws-cli for AWS, or az for Azure)
- **kubectl** (v1.24+ for Kubernetes deployments)
- **Git** (for version control)

### Required Credentials
- LLM API keys (OpenAI, OpenRouter, or compatible service)
- GitHub token with repo access
- Jira credentials (email and API token)
- SonarQube token and host URL
- MongoDB connection string (Atlas or self-hosted)
- Cloud platform credentials (GCP/AWS/Azure)

### Required Environment Variables
See [Configuration](#configuration) section for complete list.

---

## Docker Build

### Build Locally

```bash
# Build the Docker image
docker build -t aristotlei:latest .

# Run locally to test
docker run -p 8080:8080 \
  -e MONGODB_CONNECTION_STRING="your-connection-string" \
  -e GITHUB_TOKEN="your-github-token" \
  -e LLM_API_KEY="your-llm-key" \
  aristotlei:latest
```

### Build with Custom Tags

```bash
# Tag for specific version
docker build -t aristotlei:v1.0.0 .

# Tag for registry push
docker build -t gcr.io/my-project/aristotlei:latest .
docker build -t my-registry.azurecr.io/aristotlei:latest .
docker build -t 123456789012.dkr.ecr.us-east-1.amazonaws.com/aristotlei:latest .
```

---

## GCP Deployment

### Option 1: Cloud Run (Recommended for Serverless)

#### Prerequisites
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

#### Step 1: Build and Push to Artifact Registry

```bash
# Create a repository (one-time setup)
gcloud artifacts repositories create aristotlei \
  --repository-format=docker \
  --location=us-central1 \
  --description="Aristotle-I Container Repository"

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build and push image
docker build -t us-central1-docker.pkg.dev/YOUR_PROJECT_ID/aristotlei/app:latest .
docker push us-central1-docker.pkg.dev/YOUR_PROJECT_ID/aristotlei/app:latest
```

#### Step 2: Deploy to Cloud Run

```bash
gcloud run deploy aristotlei \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT_ID/aristotlei/app:latest \
  --platform=managed \
  --region=us-central1 \
  --port=8080 \
  --memory=4Gi \
  --cpu=2 \
  --timeout=3600 \
  --allow-unauthenticated \
  --set-env-vars=UI_PORT=8080,REACT_DEV_PORT=5173 \
  --update-env-vars-from-file=.env.cloud.gcp
```

#### .env.cloud.gcp Example

```env
# Core Configuration
MAX_REBUILD_ATTEMPTS=3
REVIEW_THRESHOLD=0.75
GOT_SCORE_THRESHOLD=0.70
HITL_TIMEOUT_SECONDS=300

# LLM Configuration
PLANNER_LLM_MODEL=gpt-4
DEVELOPER_LLM_MODEL=gpt-4
REVIEWER_LLM_MODEL=gpt-4
ASSEMBLER_LLM_MODEL=gpt-4
PLANNER_LLM_KEY=sk-...
DEVELOPER_LLM_KEY=sk-...
REVIEWER_LLM_KEY=sk-...
ASSEMBLER_LLM_KEY=sk-...

# UI Configuration
UI_HOST=0.0.0.0
UI_PORT=8080
REACT_DEV_PORT=5173
DEBUG=false
LOG_LEVEL=INFO

# GitHub Configuration
GITHUB_TOKEN=ghp_...
GITHUB_REPO_OWNER=your-org
GITHUB_REPO_NAME=your-repo

# Jira Configuration
JIRA_SERVER=https://your-instance.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_TOKEN=your-api-token
PROJECT_KEY=PROJ

# SonarQube Configuration
SONAR_HOST_URL=https://your-sonarqube-instance.com
SONAR_TOKEN=your-token
SONAR_ORG=your-org
SONAR_PROJECT_KEY=your-project

# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb+srv://user:pass@cluster.mongodb.net/aristotlei?retryWrites=true&w=majority
MONGODB_DATABASE=aristotlei
MONGODB_ENABLED=true
MONGODB_COLLECTION_MATRIX=performance_matrix
MONGODB_PERFORMANCE_DATABASE=performance_db
MONGODB_AGENT_PERFORMANCE=agent_perf
MONGODB_REVIEWER_COLLECTION=reviewer_results
MONGODB_FEEDBACK_DATABASE=feedback_db
DEVELOPER_AGENT_FEEDBACK=dev_feedback
ASSEMBLER_FEEDBACK=assembler_feedback

# Other Configuration
REVIEW_BRANCH_NAME=ai-review
STANDARDS_FOLDER=./standards
```

#### Step 3: Configure Environment Variables in Cloud Run

```bash
gcloud run services update aristotlei \
  --region=us-central1 \
  --update-env-vars KEY1=value1,KEY2=value2
```

### Option 2: GKE (Google Kubernetes Engine)

#### Prerequisites
```bash
gcloud services enable container.googleapis.com
```

#### Step 1: Create GKE Cluster

```bash
gcloud container clusters create aristotlei-cluster \
  --zone=us-central1-a \
  --num-nodes=2 \
  --machine-type=n1-standard-2 \
  --enable-autoscaling \
  --min-nodes=2 \
  --max-nodes=10 \
  --enable-stackdriver-kubernetes
```

#### Step 2: Deploy with Kubernetes

Create `k8s-deployment.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: aristotlei-config
data:
  UI_PORT: "8080"
  REACT_DEV_PORT: "5173"
  LOG_LEVEL: "INFO"
  REVIEW_THRESHOLD: "0.75"
  GOT_SCORE_THRESHOLD: "0.70"
  MAX_REBUILD_ATTEMPTS: "3"
  HITL_TIMEOUT_SECONDS: "300"

---
apiVersion: v1
kind: Secret
metadata:
  name: aristotlei-secrets
type: Opaque
stringData:
  MONGODB_CONNECTION_STRING: your-connection-string
  GITHUB_TOKEN: your-github-token
  LLM_API_KEY: your-llm-key
  PLANNER_LLM_KEY: your-key
  DEVELOPER_LLM_KEY: your-key
  REVIEWER_LLM_KEY: your-key
  ASSEMBLER_LLM_KEY: your-key
  JIRA_TOKEN: your-token
  SONAR_TOKEN: your-token

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: aristotlei
  labels:
    app: aristotlei
spec:
  replicas: 2
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: aristotlei
  template:
    metadata:
      labels:
        app: aristotlei
    spec:
      containers:
      - name: aristotlei
        image: us-central1-docker.pkg.dev/YOUR_PROJECT_ID/aristotlei/app:latest
        ports:
        - containerPort: 8080
          name: http
        envFrom:
        - configMapRef:
            name: aristotlei-config
        - secretRef:
            name: aristotlei-secrets
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 20
          periodSeconds: 10

---
apiVersion: v1
kind: Service
metadata:
  name: aristotlei-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8080
    protocol: TCP
  selector:
    app: aristotlei

---
apiVersion: autoscaling.k8s.io/v2
kind: HorizontalPodAutoscaler
metadata:
  name: aristotlei-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: aristotlei
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

Deploy to GKE:

```bash
gcloud container clusters get-credentials aristotlei-cluster --zone=us-central1-a
kubectl apply -f k8s-deployment.yaml
kubectl get services
```

---

## AWS Deployment

### Option 1: Amazon ECS (Elastic Container Service)

#### Prerequisites
```bash
aws configure
aws ecs create-cluster --cluster-name aristotlei
```

#### Step 1: Push Image to ECR (Elastic Container Registry)

```bash
# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

# Create repository
aws ecr create-repository --repository-name aristotlei --region us-east-1

# Tag and push image
docker tag aristotlei:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/aristotlei:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/aristotlei:latest
```

#### Step 2: Create ECS Task Definition

Create `ecs-task-definition.json`:

```json
{
  "family": "aristotlei",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "aristotlei",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/aristotlei:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "hostPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "UI_PORT",
          "value": "8080"
        },
        {
          "name": "REACT_DEV_PORT",
          "value": "5173"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "secrets": [
        {
          "name": "MONGODB_CONNECTION_STRING",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:aristotlei/mongodb:MONGODB_CONNECTION_STRING"
        },
        {
          "name": "GITHUB_TOKEN",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:aristotlei/github:GITHUB_TOKEN"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/aristotlei",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/api/health || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

Register task definition:

```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json --region us-east-1
```

#### Step 3: Create ECS Service

```bash
aws ecs create-service \
  --cluster aristotlei \
  --service-name aristotlei-service \
  --task-definition aristotlei \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345678],securityGroups=[sg-12345678],assignPublicIp=ENABLED}" \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/aristotlei/abc123,containerName=aristotlei,containerPort=8080 \
  --region us-east-1
```

### Option 2: Amazon EKS (Elastic Kubernetes Service)

#### Prerequisites
```bash
aws eks create-cluster --name aristotlei --version 1.27 --roleArn arn:aws:iam::123456789012:role/eks-service-role
```

#### Deploy to EKS

Use the Kubernetes deployment YAML from GKE section, then:

```bash
aws eks update-kubeconfig --region us-east-1 --name aristotlei
kubectl apply -f k8s-deployment.yaml
```

---

## Azure Deployment

### Option 1: Azure Container Instances (ACI)

```bash
az group create --name aristotlei-rg --location eastus

az container create \
  --resource-group aristotlei-rg \
  --name aristotlei \
  --image myregistry.azurecr.io/aristotlei:latest \
  --port 8080 \
  --environment-variables UI_PORT=8080 REACT_DEV_PORT=5173 \
  --registry-login-server myregistry.azurecr.io \
  --registry-username <username> \
  --registry-password <password> \
  --secure-environment-variables MONGODB_CONNECTION_STRING=your-connection-string GITHUB_TOKEN=your-token \
  --cpu 2 \
  --memory 4
```

### Option 2: Azure Kubernetes Service (AKS)

```bash
# Create cluster
az aks create \
  --resource-group aristotlei-rg \
  --name aristotlei-cluster \
  --node-count 2 \
  --vm-set-type VirtualMachineScaleSets \
  --load-balancer-sku standard

# Get credentials
az aks get-credentials --resource-group aristotlei-rg --name aristotlei-cluster

# Deploy using same Kubernetes YAML
kubectl apply -f k8s-deployment.yaml
```

### Option 3: Azure App Service (Docker)

```bash
# Create App Service Plan
az appservice plan create \
  --name aristotlei-plan \
  --resource-group aristotlei-rg \
  --sku B2 \
  --is-linux

# Create Web App
az webapp create \
  --resource-group aristotlei-rg \
  --plan aristotlei-plan \
  --name aristotlei-app \
  --deployment-container-image-name myregistry.azurecr.io/aristotlei:latest

# Configure container settings
az webapp config container set \
  --name aristotlei-app \
  --resource-group aristotlei-rg \
  --docker-custom-image-name myregistry.azurecr.io/aristotlei:latest \
  --docker-registry-server-url https://myregistry.azurecr.io \
  --docker-registry-server-user <username> \
  --docker-registry-server-password <password>

# Set environment variables
az webapp config appsettings set \
  --resource-group aristotlei-rg \
  --name aristotlei-app \
  --settings UI_PORT=8080 REACT_DEV_PORT=5173
```

---

## Local Docker Deployment

### Single Container

```bash
# Build image
docker build -t aristotlei:latest .

# Create .env file
cat > .env << EOF
# Core Configuration
MAX_REBUILD_ATTEMPTS=3
REVIEW_THRESHOLD=0.75
GOT_SCORE_THRESHOLD=0.70
HITL_TIMEOUT_SECONDS=300

# LLM Configuration
PLANNER_LLM_MODEL=gpt-4
DEVELOPER_LLM_MODEL=gpt-4
REVIEWER_LLM_MODEL=gpt-4
ASSEMBLER_LLM_MODEL=gpt-4
PLANNER_LLM_KEY=sk-...
DEVELOPER_LLM_KEY=sk-...
REVIEWER_LLM_KEY=sk-...
ASSEMBLER_LLM_KEY=sk-...

# UI Configuration
UI_HOST=0.0.0.0
UI_PORT=8080
REACT_DEV_PORT=5173
DEBUG=false
LOG_LEVEL=INFO

# GitHub Configuration
GITHUB_TOKEN=ghp_...
GITHUB_REPO_OWNER=your-org
GITHUB_REPO_NAME=your-repo

# Jira Configuration
JIRA_SERVER=https://your-instance.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_TOKEN=your-api-token
PROJECT_KEY=PROJ

# SonarQube Configuration
SONAR_HOST_URL=https://your-sonarqube-instance.com
SONAR_TOKEN=your-token
SONAR_ORG=your-org
SONAR_PROJECT_KEY=your-project

# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb+srv://user:pass@cluster.mongodb.net/aristotlei
MONGODB_DATABASE=aristotlei
MONGODB_ENABLED=true
MONGODB_COLLECTION_MATRIX=performance_matrix
MONGODB_PERFORMANCE_DATABASE=performance_db
MONGODB_AGENT_PERFORMANCE=agent_perf
MONGODB_REVIEWER_COLLECTION=reviewer_results
MONGODB_FEEDBACK_DATABASE=feedback_db
DEVELOPER_AGENT_FEEDBACK=dev_feedback
ASSEMBLER_FEEDBACK=assembler_feedback

# Other Configuration
REVIEW_BRANCH_NAME=ai-review
STANDARDS_FOLDER=./standards
EOF

# Run container
docker run -p 8080:8080 --env-file .env aristotlei:latest
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  aristotlei:
    build: .
    container_name: aristotlei
    ports:
      - "8080:8080"
      - "5173:5173"
    env_file:
      - .env
    environment:
      - UI_HOST=0.0.0.0
      - UI_PORT=8080
      - REACT_DEV_PORT=5173
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  mongodb:
    image: mongo:7.0
    container_name: aristotlei-mongodb
    environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: password
    volumes:
      - mongodb_data:/data/db
    ports:
      - "27017:27017"
    restart: unless-stopped

volumes:
  mongodb_data:
```

Run with Docker Compose:

```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

---

## Configuration

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| **Core Configuration** |
| MAX_REBUILD_ATTEMPTS | Yes | - | Max number of rebuild attempts |
| REVIEW_THRESHOLD | Yes | - | Minimum quality score threshold (0-1) |
| GOT_SCORE_THRESHOLD | Yes | - | Graph of Thought minimum score (0-1) |
| HITL_TIMEOUT_SECONDS | Yes | - | Human-in-the-loop timeout in seconds |
| **LLM Configuration** |
| PLANNER_LLM_MODEL | Yes | - | Model name for planner agent |
| DEVELOPER_LLM_MODEL | Yes | - | Model name for developer agent |
| REVIEWER_LLM_MODEL | Yes | - | Model name for reviewer agent |
| ASSEMBLER_LLM_MODEL | Yes | - | Model name for assembler agent |
| PLANNER_LLM_KEY | Yes | - | API key for planner LLM |
| DEVELOPER_LLM_KEY | Yes | - | API key for developer LLM |
| REVIEWER_LLM_KEY | Yes | - | API key for reviewer LLM |
| ASSEMBLER_LLM_KEY | Yes | - | API key for assembler LLM |
| PLANNER_LLM_URL | No | - | Custom LLM endpoint URL |
| DEVELOPER_LLM_URL | No | - | Custom LLM endpoint URL |
| REVIEWER_LLM_URL | No | - | Custom LLM endpoint URL |
| ASSEMBLER_LLM_URL | No | - | Custom LLM endpoint URL |
| **UI Configuration** |
| UI_HOST | Yes | 0.0.0.0 | Host binding for UI server |
| UI_PORT | Yes | 8080 | Port for UI server |
| REACT_DEV_PORT | No | 5173 | Port for React dev server (dev only) |
| DEBUG | No | false | Enable debug mode |
| LOG_LEVEL | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| **GitHub Configuration** |
| GITHUB_TOKEN | Yes | - | GitHub personal access token |
| GITHUB_REPO_OWNER | Yes | - | GitHub repository owner |
| GITHUB_REPO_NAME | Yes | - | GitHub repository name |
| **Jira Configuration** |
| JIRA_SERVER | Yes | - | Jira instance URL |
| JIRA_EMAIL | Yes | - | Jira user email |
| JIRA_TOKEN | Yes | - | Jira API token |
| PROJECT_KEY | Yes | - | Jira project key |
| **SonarQube Configuration** |
| SONAR_HOST_URL | Yes | - | SonarQube server URL |
| SONAR_TOKEN | Yes | - | SonarQube authentication token |
| SONAR_ORG | Yes | - | SonarQube organization |
| SONAR_PROJECT_KEY | Yes | - | SonarQube project key |
| **MongoDB Configuration** |
| MONGODB_CONNECTION_STRING | Yes | - | MongoDB connection string |
| MONGODB_DATABASE | No | aristotlei | Database name |
| MONGODB_ENABLED | No | true | Enable MongoDB integration |
| MONGODB_COLLECTION_MATRIX | No | - | Collection for performance matrix |
| MONGODB_PERFORMANCE_DATABASE | No | - | Database for performance metrics |
| MONGODB_AGENT_PERFORMANCE | No | - | Collection for agent performance |
| MONGODB_REVIEWER_COLLECTION | No | - | Collection for review results |
| MONGODB_FEEDBACK_DATABASE | No | - | Database for feedback |
| DEVELOPER_AGENT_FEEDBACK | No | - | Collection for developer feedback |
| ASSEMBLER_FEEDBACK | No | - | Collection for assembler feedback |
| **Other Configuration** |
| REVIEW_BRANCH_NAME | No | ai-review | Branch name for reviews |
| STANDARDS_FOLDER | No | ./standards | Path to coding standards |

### Creating Environment Files

#### production.env
```env
# Production settings
DEBUG=false
LOG_LEVEL=WARNING
MAX_REBUILD_ATTEMPTS=3
REVIEW_THRESHOLD=0.80
HITL_TIMEOUT_SECONDS=600
```

#### staging.env
```env
# Staging settings
DEBUG=true
LOG_LEVEL=INFO
MAX_REBUILD_ATTEMPTS=5
REVIEW_THRESHOLD=0.75
HITL_TIMEOUT_SECONDS=300
```

---

## Security Best Practices

### 1. Secrets Management

#### Using AWS Secrets Manager
```bash
aws secretsmanager create-secret \
  --name aristotlei/mongodb \
  --secret-string '{"username":"user","password":"pass","connection_string":"mongodb://..."}'

aws secretsmanager create-secret \
  --name aristotlei/github \
  --secret-string '{"token":"ghp_..."}'
```

#### Using GCP Secret Manager
```bash
echo -n "sk-..." | gcloud secrets create openai-key --data-file=-
gcloud secrets versions access latest --secret="openai-key"
```

#### Using Azure Key Vault
```bash
az keyvault create --name aristotlei-kv --resource-group aristotlei-rg

az keyvault secret set --vault-name aristotlei-kv \
  --name mongodb-connection-string \
  --value "mongodb+srv://..."
```

### 2. Network Security

#### Docker Network Isolation
```bash
docker network create aristotlei-network
docker run --network aristotlei-network -p 8080:8080 aristotlei:latest
```

#### Kubernetes Network Policy
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: aristotlei-network-policy
spec:
  podSelector:
    matchLabels:
      app: aristotlei
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: ingress-controller
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 27017
```

### 3. Image Security

#### Scan for Vulnerabilities
```bash
# Using Trivy
trivy image aristotlei:latest

# Using Google Cloud vulnerability scanning
gcloud container images scan IMAGE_URL
```

#### Minimal Base Images
- Use `python:3.11-slim` instead of `python:3.11`
- Use `node:20-alpine` instead of `node:20`

### 4. Container Security

#### Run as Non-Root
Already configured in Dockerfile:
```dockerfile
RUN useradd -m -u 1000 aristotlei && chown -R aristotlei:aristotlei /app
USER aristotlei
```

#### Pod Security Policy (Kubernetes)
```yaml
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: aristotlei-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'MustRunAs'
    seLinuxOptions:
      type: confined_t
```

### 5. Data Encryption

#### In Transit
- Use HTTPS/TLS for all connections
- MongoDB Atlas: Enable TLS/SSL
- GitHub: Use HTTPS URLs

#### At Rest
- Enable encryption on MongoDB
- Use encrypted volumes in Kubernetes
- Enable encryption for cloud storage

```bash
# GCP: Enable encryption on disks
gcloud compute disks create aristotlei-disk --type pd-standard --size 100GB

# AWS: Use encrypted volumes
aws ec2 create-volume --size 100 --encrypted --region us-east-1
```

### 6. Access Control

#### RBAC in Kubernetes
```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: aristotlei-role
rules:
- apiGroups: [""]
  resources: ["pods", "pods/logs"]
  verbs: ["get", "list", "watch"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: aristotlei-rolebinding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: aristotlei-role
subjects:
- kind: ServiceAccount
  name: aristotlei
```

---

## Monitoring and Logging

### CloudWatch (AWS)

```python
# Example: Log to CloudWatch
import boto3
import logging
from watchtower import CloudWatchLogHandler

logger = logging.getLogger(__name__)
cloudwatch_handler = CloudWatchLogHandler(
    log_group='/ecs/aristotlei',
    stream_name='aristotlei-stream'
)
logger.addHandler(cloudwatch_handler)
```

### Google Cloud Logging

```python
import logging
from google.cloud import logging as cloud_logging

client = cloud_logging.Client()
client.setup_logging()
logger = logging.getLogger('aristotlei')
```

### Prometheus Metrics

Add to `main.py`:
```python
from prometheus_client import Counter, Histogram, start_http_server

# Metrics
request_count = Counter('aristotlei_requests_total', 'Total requests')
request_duration = Histogram('aristotlei_request_duration_seconds', 'Request duration')

# Start metrics server
start_http_server(8000)
```

### Kubernetes Monitoring

```bash
# Install Prometheus
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/prometheus

# Install Grafana
helm install grafana grafana/grafana
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Container Won't Start

```bash
# Check logs
docker logs aristotlei

# Check with tail
docker logs -f --tail 100 aristotlei

# Kubernetes
kubectl logs deployment/aristotlei
kubectl describe pod <pod-name>
```

#### 2. Environment Variables Not Loaded

```bash
# Verify in running container
docker exec aristotlei env | grep MONGODB

# For Kubernetes
kubectl get configmap aristotlei-config -o yaml
kubectl get secret aristotlei-secrets -o yaml
```

#### 3. Port Already in Use

```bash
# Find process using port
lsof -i :8080

# Use different port
docker run -p 9000:8080 aristotlei:latest
```

#### 4. MongoDB Connection Issues

```bash
# Test connection
python -c "from pymongo import MongoClient; print(MongoClient('your-connection-string').admin.command('ping'))"

# Check network from container
docker exec aristotlei curl -v mongodb://your-host:27017
```

#### 5. Out of Memory

```bash
# Check current usage
docker stats aristotlei

# Increase limits in deployment
docker run -m 8g aristotlei:latest

# Kubernetes
kubectl set resources deployment aristotlei --limits=memory=8Gi
```

#### 6. Health Check Failures

```bash
# Test endpoint directly
curl http://localhost:8080/api/health

# From container
docker exec aristotlei curl http://localhost:8080/api/health

# Increase initial delay
docker run --health-start-period=120s aristotlei:latest
```

### Debug Mode

Enable debug logging:

```bash
docker run -e DEBUG=true -e LOG_LEVEL=DEBUG aristotlei:latest
```

Check specific components:

```bash
# Check GitHub connectivity
python -c "from services.github_service import GithubService; gs = GithubService(); print(gs.verify_credentials())"

# Check Jira connectivity
python -c "from tools.jira_client import JiraClient; jc = JiraClient(); print(jc.test_connection())"
```

### Performance Tuning

```bash
# Increase resources for better performance
docker run -m 8g --cpus 4 aristotlei:latest

# For Kubernetes
kubectl set resources deployment aristotlei \
  --requests=memory=4Gi,cpu=2 \
  --limits=memory=8Gi,cpu=4
```

---

## Next Steps

1. **Review Configuration**: Ensure all environment variables are properly set
2. **Test Health Checks**: Verify the application is running correctly
3. **Setup Monitoring**: Configure CloudWatch, Google Cloud Logging, or Prometheus
4. **Enable Auto-Scaling**: Configure HPA for Kubernetes or auto-scaling groups for VMs
5. **Setup CI/CD**: Automate image builds and deployments
6. **Backup Strategy**: Configure regular database backups
7. **Disaster Recovery**: Plan for failover and recovery scenarios

---

## Support

For issues or questions:
- Check the main [README.md](README.md)
- Review [DESIGN.md](DESIGN.md) for architecture details
- Check [DOCUMENTATION_COMPLETE.md](DOCUMENTATION_COMPLETE.md) for additional information
- Visit the project repository for updates

