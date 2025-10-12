# Agent-Flow - AI-Powered Development System

An intelligent AI development system using LangChain, LangGraph, MongoDB, and React UI for automated code generation, review, and deployment workflows.

## 🌟 Features

- **Automated Code Generation**: AI-powered code generation from JIRA issues
- **Multi-Agent System**: Planner, Developer, Reviewer, and Assembler agents
- **Code Quality Analysis**: Integration with SonarQube and Pylint
- **GitHub Integration**: Automatic PR creation and management
- **MongoDB Tracking**: Performance metrics and analytics
- **React UI**: Real-time monitoring and control dashboard
- **HITL (Human-in-the-Loop)**: Manual validation for critical decisions

## 📋 Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Local Development Setup](#local-development-setup)
- [GCP Deployment](#gcp-deployment)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     React UI (Port 5173)                │
│              Real-time Monitoring & Control             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              Main API Server (Port 8080)                │
│                   Router & Workflow                      │
└─┬──────────┬──────────┬──────────┬──────────┬──────────┘
  │          │          │          │          │
┌─▼────┐ ┌──▼─────┐ ┌──▼──────┐ ┌─▼────────┐ ┌▼─────────┐
│Planner│ │Developer│ │Reviewer │ │Assembler│ │SonarQube│
│Agent  │ │Agent    │ │Agent    │ │Agent    │ │Review   │
└───────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘
    │          │          │           │           │
    └──────────┴──────────┴───────────┴───────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
    ┌───▼────┐              ┌────▼─────┐
    │MongoDB │              │  GitHub  │
    │Atlas   │              │  & JIRA  │
    └────────┘              └──────────┘
```

## 📦 Prerequisites

### Local Development
- Python 3.11 or higher
- Node.js 18+ (for React UI)
- MongoDB (local or Atlas)
- Git
- Docker & Docker Compose (optional)

### GCP Deployment
- Google Cloud SDK (gcloud)
- Docker
- GCP Project with billing enabled
- MongoDB Atlas account (recommended for production)

## 🚀 Local Development Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/Agent-flow.git
cd Agent-flow
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
# Copy the example file
cp .env.example .env

# Edit .env with your credentials
# Required: OPENROUTE_API_KEY, GITHUB_TOKEN, JIRA credentials, MongoDB connection string
```

### 4. Start the Application
```bash
# Start with Python
python main.py

# Or use Docker Compose (includes MongoDB)
docker-compose up -d
```

### 5. Access the Application
- **API Server**: http://localhost:8080
- **React UI**: http://localhost:5173
- **Health Check**: http://localhost:8080/api/health

## ☁️ GCP Deployment

### Quick Start (Cloud Run - Recommended)

#### Using Automated Script (Windows)
```powershell
# Set your GCP project ID
$env:GCP_PROJECT_ID = "your-project-id"

# Run deployment script
.\deploy-gcp.ps1 -ProjectId "your-project-id" -DeploymentType CloudRun
```

#### Using Automated Script (Linux/Mac)
```bash
# Set your GCP project ID
export GCP_PROJECT_ID="your-project-id"

# Make script executable
chmod +x deploy-gcp.sh

# Run deployment script
./deploy-gcp.sh
```

#### Manual Deployment Steps

1. **Set up GCP Project**
```bash
gcloud config set project YOUR_PROJECT_ID
gcloud auth login
```

2. **Enable Required APIs**
```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

3. **Create Secrets from .env**
```bash
# Example for creating secrets
gcloud secrets create OPENROUTE_API_KEY --data-file=<(echo -n "your_key")
gcloud secrets create GITHUB_TOKEN --data-file=<(echo -n "your_token")
gcloud secrets create JIRA_TOKEN --data-file=<(echo -n "your_token")
gcloud secrets create MONGODB_CONNECTION_STRING --data-file=<(echo -n "your_uri")
# ... repeat for all secrets
```

4. **Deploy to Cloud Run**
```bash
# Build and deploy using Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Or deploy manually
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/agent-flow
gcloud run deploy agent-flow \
  --image gcr.io/YOUR_PROJECT_ID/agent-flow \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 2Gi \
  --cpu 2
```

### Alternative GCP Deployment Options

#### Google Kubernetes Engine (GKE)
```bash
# Create cluster
gcloud container clusters create agent-flow-cluster \
  --num-nodes=3 \
  --machine-type=e2-standard-4 \
  --region=us-central1

# Deploy
kubectl apply -f k8s/
```

#### App Engine
```bash
gcloud app deploy app.yaml
```

#### Compute Engine VM
```bash
gcloud compute instances create agent-flow-vm \
  --machine-type=e2-standard-4 \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --zone=us-central1-a
```

📚 **See [GCP_DEPLOYMENT.md](./GCP_DEPLOYMENT.md) for detailed deployment instructions and troubleshooting.**

## ⚙️ Configuration

All configuration is managed through environment variables in the `.env` file:

### Required Configuration

```env
# LLM Configuration (Required)
OPENROUTE_API_KEY=your_api_key
LLM_MODEL=deepseek/deepseek-v3:free

# GitHub Configuration (Required)
GITHUB_TOKEN=your_github_token
GITHUB_REPO_OWNER=your_username
GITHUB_REPO_NAME=your_repo

# JIRA Configuration (Required)
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your_email@example.com
JIRA_TOKEN=your_jira_token
PROJECT_KEY=YOUR_KEY

# MongoDB Configuration (Required)
MONGODB_CONNECTION_STRING=mongodb+srv://user:pass@cluster.mongodb.net/
```

### Optional Configuration

```env
# UI Settings
UI_HOST=localhost
UI_PORT=8080
REACT_DEV_PORT=5173

# Review Thresholds
REVIEW_THRESHOLD=70
GOT_SCORE_THRESHOLD=7.0
MAX_REBUILD_ATTEMPTS=3

# SonarQube (Optional)
SONAR_TOKEN=your_token
SONAR_ORG=your_org
SONAR_PROJECT_KEY=your_key
```

## 📖 Usage

### Starting a Workflow

1. **Via React UI** (Recommended)
   - Open http://localhost:5173
   - Click "Start Automation"
   - Select JIRA issue or enter task details
   - Monitor progress in real-time

2. **Via API**
```bash
curl -X POST http://localhost:8080/api/start-automation \
  -H "Content-Type: application/json" \
  -d '{"issue_key": "IPM-123"}'
```

### Monitoring

- **System Status**: GET `/api/status`
- **Statistics**: GET `/api/stats`
- **Activity Log**: GET `/api/activity`
- **Health Check**: GET `/api/health`

## 🔌 API Documentation

### Health Check
```bash
GET /api/health
Response: {"status": "healthy", "timestamp": "..."}
```

### Start Automation
```bash
POST /api/start-automation
Body: {"issue_key": "IPM-123"}
Response: {"success": true, "message": "..."}
```

### Get System Status
```bash
GET /api/status
Response: {
  "status": "running",
  "current_task": "...",
  "agents_active": [...]
}
```

### Get Statistics
```bash
GET /api/stats
Response: {
  "tasks_completed": 10,
  "success_rate": 85.5,
  "tokens_used": 125000
}
```

### Performance Data
```bash
GET /api/performance-data
Response: {"performance_data": [...]}
```

## 📁 Project Structure

```
Agent-flow/
├── agents/              # Agent implementations
│   ├── planner_agent.py
│   ├── developer_agent.py
│   ├── reviewer.py
│   └── sonarcube_review.py
├── config/              # Configuration management
│   ├── settings.py      # Centralized config
│   └── logging_config.py
├── core/                # Core system components
│   ├── graph.py
│   ├── router.py
│   └── hitl.py
├── tools/               # Agent tools
│   ├── planner_tools.py
│   ├── developer_tool.py
│   ├── reviewer_tool.py
│   └── jira_client.py
├── services/            # External services
│   ├── github_service.py
│   └── performance_tracker.py
├── ui/                  # Backend UI handler
│   └── ui.py
├── Agentic_UI/          # React frontend
├── prompts/             # AI prompts
├── standards/           # Coding standards
├── k8s/                 # Kubernetes configs
├── main.py             # Application entry point
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose setup
├── cloudbuild.yaml     # GCP Cloud Build config
├── app.yaml            # App Engine config
├── deploy-gcp.sh       # GCP deployment script (Linux/Mac)
├── deploy-gcp.ps1      # GCP deployment script (Windows)
└── requirements.txt    # Python dependencies
```

## 🔧 Troubleshooting

### Common Issues

**Port Already in Use**
```bash
# Windows
netstat -ano | findstr :8080
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8080
kill -9 <PID>
```

**MongoDB Connection Error**
- Verify MongoDB is running
- Check connection string in `.env`
- For Atlas: Ensure IP whitelist is configured

**LLM API Errors**
- Verify API key in `.env`
- Check rate limits
- Ensure model name is correct

**GCP Deployment Issues**
- Verify all secrets are created
- Check service logs: `gcloud run logs read agent-flow`
- Ensure billing is enabled
- Verify API quotas

### Getting Help

- **Logs**: Check `logs/` directory
- **Health Check**: `curl http://localhost:8080/api/health`
- **Docker Logs**: `docker-compose logs -f`
- **GCP Logs**: `gcloud logging read`

## 🔐 Security Best Practices

1. **Never commit `.env` file** - Use `.env.example` as template
2. **Use Secret Manager** - For production deployments (GCP Secret Manager, etc.)
3. **Rotate credentials** - Regularly update API keys and tokens
4. **Limit permissions** - Use minimal required permissions for service accounts
5. **HTTPS only** - Always use HTTPS in production
6. **Regular updates** - Keep dependencies updated

## 📊 Monitoring & Performance

- **MongoDB Performance Tracking**: Real-time metrics stored in MongoDB
- **Cloud Monitoring**: GCP native monitoring and alerting
- **Custom Dashboards**: React UI with live performance data
- **Log Aggregation**: Centralized logging with Cloud Logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🙏 Acknowledgments

- LangChain & LangGraph for agent orchestration
- OpenRouter for LLM API access
- MongoDB Atlas for database hosting
- Google Cloud Platform for infrastructure

## 📞 Support

For issues and questions:
- GitHub Issues: [Your repo issues URL]
- Documentation: See `GCP_DEPLOYMENT.md` for deployment details
- Configuration: See `CONFIG_REFACTORING_SUMMARY.md` for config details

---

**Version**: 3.0.0  
**Last Updated**: October 10, 2025  
**Status**: Production Ready ✅
