# Aristotle-I: Autonomous AI Workflow Platform

Aristotle-I is an autonomous AI workflow platform that orchestrates intelligent multi-agent workflows for software development lifecycle automation. The platform features a task management system with intelligent auto allocation, real-time monitoring, and seamless human oversight capabilities.

## 🚀 Features

- **Multi-Agent Architecture**: Specialized agents for different development tasks
  - **Planner Agent**: Analyzes JIRA tickets and creates execution plans
  - **Developer Agent**: Generates and modifies code based on requirements
  - **Reviewer Agent**: Performs code quality, security, and standards analysis
  - **Assembler Agent**: Coordinates workflow and generates deployment artifacts
  - **SonarQube Agent**: Integrates with SonarQube for advanced code quality analysis

- **JIRA Integration**: Automatically fetches and processes JIRA tickets
- **GitHub Integration**: Creates branches, commits code, and opens pull requests
- **SonarQube Integration**: Comprehensive code quality and security scanning
- **Performance Tracking**: Monitors and stores agent performance metrics
- **React UI**: Modern web interface for system monitoring and configuration
- **Human-in-the-Loop (HITL)**: Interactive approval process for critical decisions
- **Flexible LLM Support**: Works with any OpenAI-compatible API (OpenRouter, OpenAI, local models, etc.)
- **Per-Agent LLM Configuration**: Use different models for different agents

## 📋 Prerequisites

- Python 3.9 or higher
- Node.js 18+ and npm (for the React UI)
- MongoDB (local or Atlas)
- GitHub Personal Access Token
- JIRA account and API token
- LLM API key (OpenRouter, OpenAI, or compatible service)
- SonarQube account (optional, for code quality analysis)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/Agent-flow.git
cd Agent-flow
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Set Up React UI

```bash
cd Agentic_UI
npm install
cd ..
```

### 4. Configure Environment Variables

Copy the `.env.example` file to `.env` and fill in your credentials:

```bash
copy .env .env
```

Edit the `.env` file with your actual values (see Configuration section below).

## ⚙️ Configuration

All configuration is managed through environment variables in the `.env` file. See `.env.example` for a complete template.

### Required Configuration

#### LLM Configuration
- `LLM_API_KEY`: Your LLM API key (e.g., OpenRouter, OpenAI)
- `LLM_API_URL`: API endpoint URL
- `PLANNER_LLM_MODEL`: Model for planning tasks
- `ASSEMBLER_LLM_MODEL`: Model for assembly tasks
- `DEVELOPER_LLM_MODEL`: Model for code generation
- `REVIEWER_LLM_MODEL`: Model for code review

#### GitHub Configuration
- `GITHUB_TOKEN`: GitHub Personal Access Token (with repo permissions)
- `GITHUB_REPO_OWNER`: Repository owner username
- `GITHUB_REPO_NAME`: Repository name

#### JIRA Configuration
- `JIRA_SERVER`: JIRA server URL (e.g., https://your-domain.atlassian.net)
- `JIRA_EMAIL`: Your JIRA email
- `JIRA_TOKEN`: JIRA API token
- `PROJECT_KEY`: JIRA project key

#### MongoDB Configuration
- `MONGODB_CONNECTION_STRING`: MongoDB connection string
- `MONGODB_PERFORMANCE_DATABASE`: Database name for performance tracking
- `MONGODB_AGENT_PERFORMANCE`: Collection for agent metrics
- `MONGODB_COLLECTION_MATRIX`: Collection for workflow data
- `MONGODB_REVIEWER_COLLECTION`: Collection for review data

### Optional Configuration

#### SonarQube (for advanced code quality analysis)
- `SONAR_TOKEN`: SonarQube authentication token
- `SONAR_ORG`: SonarQube organization
- `SONAR_PROJECT_KEY`: Project key in SonarQube
- `SONAR_HOST_URL`: SonarQube server URL

#### System Settings
- `MAX_REBUILD_ATTEMPTS`: Maximum code rebuild attempts (default: 3)
- `REVIEW_THRESHOLD`: Code quality threshold (default: 0.7)
- `GOT_SCORE_THRESHOLD`: Planning score threshold (default: 0.8)
- `HITL_TIMEOUT_SECONDS`: Timeout for human approval (default: 300)

## 🚀 Usage

### Start the System

```bash
python main.py
```

This will:
1. Initialize the router and agent system
2. Start the React UI development server
3. Automatically open the UI in your default browser (http://localhost:5173)

### Using the Web Interface

1. **Configure Settings**: Go to the Settings page to verify/update your configuration
2. **Start Workflow**: Click the "Start Automation" button on the home page
3. **Monitor Progress**: Watch real-time logs and status updates
4. **HITL Approval**: Review and approve/reject agent actions when prompted

### Manual Workflow Trigger

The system automatically:
1. Fetches "To Do" issues from JIRA
2. Creates execution plans for each issue
3. Generates code based on requirements
4. Reviews code for quality and security
5. Creates GitHub branches and pull requests
6. Runs SonarQube analysis (if configured)

## 📁 Project Structure

```
Agent-flow/
├── agents/              # Agent implementations
│   ├── planner_agent.py
│   ├── developer_agent.py
│   ├── reviewer.py
│   ├── assembler_agent.py
│   └── sonarcube_review.py
├── core/               # Core system components
│   ├── graph.py        # Workflow orchestration
│   ├── router.py       # System router and initialization
│   ├── hitl.py         # Human-in-the-loop management
│   └── logging.py      # Logging utilities
├── graph/              # Agent-specific graphs
├── services/           # External service integrations
│   ├── llm_service.py
│   ├── github_service.py
│   └── performance_tracker.py
├── tools/              # Agent tools
│   ├── jira_client.py
│   ├── planner_tools.py
│   ├── developer_tool.py
│   └── assembler_tool.py
├── config/             # Configuration management
├── prompts/            # LLM prompts
├── standards/          # Coding standards and guidelines
├── Agentic_UI/         # React web interface
├── k8s/                # Kubernetes deployment files
└── main.py             # Application entry point
```

## 🐳 Docker Deployment

### Using Docker Compose

```bash
docker-compose up -d
```

### Building Docker Image

```bash
docker build -t agent-flow:latest .
```

## ☁️ Cloud Deployment

### Google Cloud Platform (GCP)

See [GCP_DEPLOYMENT.md](GCP_DEPLOYMENT.md) for detailed instructions.

Quick deployment:
```bash
./deploy-gcp.sh
```

### Kubernetes

```bash
# Create namespace and secrets
kubectl apply -f k8s/00-namespace-secrets.yaml

# Update secrets with your values
kubectl edit secret agent-flow-secrets -n agent-flow

# Deploy application
kubectl apply -f k8s/01-deployment.yaml
```

## 📊 Performance Monitoring

The system automatically tracks:
- Agent execution times
- Token usage per agent
- Success/failure rates
- LLM API call statistics
- Code quality metrics

All metrics are stored in MongoDB and can be visualized through the UI or external tools like Grafana.

## 🔧 Troubleshooting

### Common Issues

**1. "Failed to initialize router system"**
- Check that all required environment variables are set
- Verify GitHub token has proper permissions
- Ensure JIRA credentials are correct

**2. "LLM API Error"**
- Verify API key is valid
- Check API URL is correct
- Ensure sufficient API credits

**3. "MongoDB Connection Error"**
- Verify connection string format
- Check network connectivity
- Ensure MongoDB is running

**4. UI Not Starting**
- Check if port 5173 is already in use
- Verify Node.js and npm are installed
- Run `npm install` in the Agentic_UI directory

### Debug Mode

Enable debug logging:
```bash
# In .env file
DEBUG=true
LOG_LEVEL=DEBUG
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

[Add your license here]

## 🙏 Acknowledgments

- Built with [LangGraph](https://github.com/langchain-ai/langgraph)
- UI built with React + TypeScript + Vite
- Uses OpenAI-compatible APIs for LLM integration

## 📧 Support

For issues and questions, please open an issue on GitHub.

---

**Note**: This system is designed for development automation. Always review generated code before merging to production.
