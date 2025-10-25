# Aristotle-I: Autonomous AI Workflow Platform

[![Status](https://img.shields.io/badge/status-active-success.svg)](https://github.com/your-repo)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Code Quality](https://img.shields.io/badge/code%20quality-A-brightgreen.svg)](docs/QUALITY.md)

**Aristotle-I** is an intelligent multi-agent system that orchestrates AI-powered workflows across your software development lifecycle. It integrates seamlessly with Jira, GitHub, and SonarQube to automate planning, code generation, quality review, and documentation—while maintaining human oversight at every critical step.

## 🎯 Why Aristotle-I?

| Challenge | Solution |
|-----------|----------|
| Repetitive coding tasks | Autonomous code generation with quality gates |
| Inconsistent code quality | Multi-dimensional automated reviews |
| Documentation debt | Auto-generated technical documentation |
| Planning complexity | AI-powered task decomposition |
| Knowledge gaps | Integrated coding standards library |

## ✨ Key Features

### 🤖 Intelligent Multi-Agent Architecture
- **Planner Agent**: Breaks down complex requirements using Graph of Thought (GOT) methodology
- **Developer Agent**: Generates production-ready code with comprehensive tests
- **Reviewer Agent**: Analyzes code across completeness, security, and standards dimensions
- **Assembler Agent**: Creates deployment artifacts and technical documentation
- **SonarQube Integration**: Advanced static code analysis and quality metrics

### 🔗 Seamless Integrations
- **JIRA**: Automatic issue ingestion and task management
- **GitHub**: Branch creation, commits, and pull requests
- **SonarQube**: Code quality and security scanning
- **Multiple LLMs**: OpenAI, OpenRouter, local models, or any OpenAI-compatible API

### 🎛️ Human-in-the-Loop Control
- Strategic approval checkpoints for plans and code
- Intuitive web dashboard for monitoring and intervention
- Granular feedback mechanism for agent improvements
- Complete audit trail for compliance

### 📊 Enterprise Features
- Role-based access control (Admin, Reviewer, Developer)
- Comprehensive audit logging
- Performance tracking and cost monitoring
- Kubernetes-ready deployment
- Disaster recovery and high availability

## 🚀 Quick Start

### Prerequisites
- **Python** 3.9+ with pip
- **Node.js** 18+ with npm  
- **Docker** & **Docker Compose** (recommended)
- **MongoDB** (local or Atlas)
- API credentials:
  - GitHub Personal Access Token
  - Jira API token
  - LLM API key (OpenRouter, OpenAI, etc.)
  - SonarQube token (optional)

### Installation (Local Development)

#### 1. Clone Repository
```bash
git clone https://github.com/your-org/aristotle-i.git
cd aristotle-i
```

#### 2. Python Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 3. React UI Setup
```bash
cd Agentic_UI
npm install
cd ..
```

#### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials
```

#### 5. Run System
```bash
python main.py
```

The UI will automatically open at `http://localhost:5173`

### Docker Quick Start
```bash
# Using Docker Compose (includes all services)
docker-compose up -d

# View logs
docker-compose logs -f aristotle-i

# Stop services
docker-compose down
```

## ⚙️ Configuration Guide

### Essential Environment Variables

```bash
# LLM Configuration (choose one provider)
LLM_API_KEY=your-api-key-here
LLM_API_URL=https://api.openrouter.ai/api/v1  # or your provider's URL

# Model Selection (per agent)
PLANNER_LLM_MODEL=meta-llama/llama-2-70b-chat
DEVELOPER_LLM_MODEL=gpt-4
REVIEWER_LLM_MODEL=claude-3-opus
ASSEMBLER_LLM_MODEL=gpt-3.5-turbo

# GitHub Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
GITHUB_REPO_OWNER=your-org
GITHUB_REPO_NAME=your-repo

# JIRA Configuration  
JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_TOKEN=your-jira-api-token
PROJECT_KEY=YOUR_PROJECT

# MongoDB
MONGODB_CONNECTION_STRING=mongodb://localhost:27017
MONGODB_DATABASE=aristotle_db

# SonarQube (Optional)
SONAR_TOKEN=squ_xxxxxxxxxxxx
SONAR_HOST_URL=https://sonar.example.com
SONAR_PROJECT_KEY=your-project-key

# System Tuning
MAX_REBUILD_ATTEMPTS=3
REVIEW_THRESHOLD=70
GOT_SCORE_THRESHOLD=7.0
HITL_TIMEOUT_SECONDS=300
```

See [Configuration Reference](docs/CONFIGURATION.md) for all available options.

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [DESIGN.md](DESIGN.md) | System architecture and design decisions |
| [API.md](docs/API.md) | REST API reference |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment guide |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development guidelines |

## 📁 Project Structure

```
aristotle-i/
├── agents/                      # Core agent implementations
│   ├── core_planner_agent.py   # High-level planner logic
│   ├── core_developer_agent.py # Code generation engine
│   ├── core_reviewer_agent.py  # Quality review orchestrator
│   ├── core_assembler_agent.py # Documentation generator
│   └── sonarcube_review.py     # SonarQube integration
│
├── core/                        # System infrastructure
│   ├── graph.py                # LangGraph workflow orchestration
│   ├── router.py               # System initialization and routing
│   ├── hitl.py                 # Human-in-the-loop management
│   └── logging.py              # Centralized logging
│
├── tools/                       # Agent tools and utilities
│   ├── planner_tools.py        # Task decomposition utilities
│   ├── developer_tool.py       # Code generation helpers
│   ├── reviewer_tool.py        # Review analysis tools
│   ├── jira_client.py          # JIRA API wrapper
│   └── utils.py                # Common utilities
│
├── services/                    # External service integrations
│   ├── llm_service.py          # Multi-provider LLM abstraction
│   ├── github_service.py       # GitHub API client
│   └── performance_tracker.py  # Metrics and analytics
│
├── config/                      # Configuration management
│   └── settings.py             # Settings loader
│
├── prompts/                     # LLM prompt templates
│   ├── planner_*.md            # Planner prompts
│   ├── developer_*.md          # Developer prompts
│   ├── reviewer_*.md           # Reviewer prompts
│   └── assembler_*.md          # Assembler prompts
│
├── standards/                   # Coding standards library
│   ├── python.md               # Python guidelines
│   ├── javascript.md           # JavaScript guidelines
│   ├── security_guidelines.md  # Security best practices
│   └── coding_standards.md     # General standards
│
├── Agentic_UI/                 # React web interface
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   ├── pages/              # Page components
│   │   ├── services/           # API clients
│   │   └── App.tsx             # Root component
│   └── package.json            # NPM dependencies
│
├── tests/                       # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # End-to-end tests
│
├── docs/                        # Documentation
├── k8s/                         # Kubernetes manifests
├── DESIGN.md                    # System design document
├── README.md                    # This file
├── main.py                      # Application entry point
└── requirements.txt             # Python dependencies
```

## 🔄 Workflow Overview

```
User Creates Issue in JIRA
        ↓
Planner Agent Decomposes Task
        ↓
Human Reviews & Approves Plan
        ↓
Developer Agent Generates Code
        ↓
Reviewer Agent Analyzes Quality
        ↓
[Code OK?] → [No] → Developer Rebui (max 3 attempts)
        ↓     ↑_____|
       Yes
        ↓
Human Final Approval
        ↓
Code Pushed to GitHub PR
        ↓
SonarQube Analysis (if configured)
        ↓
Assembler Generates Documentation
        ↓
Workflow Complete ✓
```

## 🚢 Deployment

### Local Development
```bash
python main.py  # Starts system with UI
```

### Docker Compose
```bash
docker-compose up -d
```

### Kubernetes
```bash
# See DEPLOYMENT.md for full instructions
kubectl apply -f k8s/
```

### Cloud Platforms
- [GCP Deployment](docs/GCP_DEPLOYMENT.md)
- [AWS Deployment](docs/AWS_DEPLOYMENT.md)
- [Azure Deployment](docs/AZURE_DEPLOYMENT.md)

## 📊 Monitoring & Metrics

### Key Metrics
- **Task Throughput**: Tasks completed per hour
- **Quality Score**: Average review score (0-100)
- **Time to Approval**: Median time from creation to approval
- **Success Rate**: Percentage of tasks completed without human intervention
- **LLM Cost**: Total API spend tracked per provider

### Access Metrics
1. **Web Dashboard**: `http://localhost:5173/metrics`
2. **Logs**: Check `logs/` directory
3. **MongoDB**: Query collections directly

## 🔒 Security Best Practices

### Secret Management
- ✅ Never commit `.env` files
- ✅ Use secrets manager for production (Vault, AWS Secrets Manager)
- ✅ Rotate API tokens regularly
- ✅ Use short-lived tokens where possible

### Code Review
- All changes go through automated review
- Human approval required before merge
- Security scanning via SonarQube
- Audit trail maintained for all changes

### Access Control
- RBAC implemented at all levels
- GitHub token with minimal required permissions
- JIRA service account with project-level access
- LLM API usage monitored and throttled

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup
```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linting
pylint agents/ core/ services/ tools/

# Format code
black .
```

## 🐛 Troubleshooting

### Common Issues

**"Failed to initialize router system"**
→ Verify all required environment variables are set

**"LLM API Error"**  
→ Check API key validity and rate limits

**"MongoDB Connection Error"**
→ Ensure MongoDB is running and connection string is correct

**"UI not starting"**
→ Check port 5173 availability and run `npm install` in Agentic_UI

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more solutions.

## 📈 Performance Optimization

### Tips
- Use model-specific LLMs for each agent
- Configure appropriate review thresholds
- Adjust worker pool size based on load
- Enable response caching for similar prompts
- Monitor and optimize database queries

## 🔐 Compliance

- ✅ SOC 2 Type II compliance
- ✅ GDPR data protection
- ✅ PII automatic redaction
- ✅ Audit trail for all actions
- ✅ Data retention policies

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with:
- [LangGraph](https://github.com/langchain-ai/langgraph) - Workflow orchestration
- [React](https://react.dev/) - UI framework
- [Vite](https://vitejs.dev/) - Build tool
- [MongoDB](https://www.mongodb.com/) - Database
- [OpenAI](https://openai.com/) & [OpenRouter](https://openrouter.ai/) - LLM providers

## 📧 Support & Community

- **Issues**: [GitHub Issues](https://github.com/your-org/aristotle-i/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/aristotle-i/discussions)
- **Email**: support@your-org.com
- **Documentation**: [Docs Site](https://docs.your-org.com/aristotle-i)

---

**⚠️ Important**: Always review AI-generated code before deploying to production. This system is a development assistant, not a replacement for human judgment.

**Last Updated**: October 25, 2025  
**Version**: 1.0  
**Maintainer**: Debabrata Das
