# Aristotle-I: Quick Start Guide

**Get up and running in 5 minutes** ⚡

## Prerequisites Check ✓

```bash
# Verify requirements
python --version          # Should be 3.9+
node --version           # Should be 18+
docker --version         # For containerized setup
```

## Option 1: Docker (Recommended for Most Users)

### Step 1: Prepare Configuration
```bash
# Copy template
cp .env.example .env

# Edit with your credentials
nano .env  # or vim, code, etc.
```

### Step 2: Required Credentials
Get these credentials first:
- **GitHub**: Create PAT at https://github.com/settings/tokens (scopes: repo)
- **JIRA**: Generate API token at https://id.atlassian.com/manage-profile/security/api-tokens
- **LLM API**: Get key from OpenRouter (https://openrouter.ai) or OpenAI
- **MongoDB**: Use cloud.mongodb.com or local instance

### Step 3: Configure .env
```bash
# Minimal working configuration
LLM_API_KEY=your-openrouter-key
LLM_API_URL=https://api.openrouter.ai/api/v1

GITHUB_TOKEN=ghp_xxxxx
GITHUB_REPO_OWNER=your-org
GITHUB_REPO_NAME=your-repo

JIRA_SERVER=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_TOKEN=atcxxxxx

MONGODB_CONNECTION_STRING=mongodb://localhost:27017
```

### Step 4: Start System
```bash
docker-compose up -d
```

### Step 5: Access UI
Open browser: `http://localhost:5173`

## Option 2: Local Development

### Step 1: Clone & Setup
```bash
git clone https://github.com/your-org/aristotle-i.git
cd aristotle-i

# Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install Python deps
pip install -r requirements.txt
```

### Step 2: React UI
```bash
cd Agentic_UI
npm install
cd ..
```

### Step 3: Configure
```bash
cp .env.example .env
# Edit .env with your credentials
```

### Step 4: Start
```bash
python main.py
```

Browser opens automatically at `http://localhost:5173`

## First Workflow: Create Your First Automated Task

### 1. Create JIRA Issue
- Go to your JIRA project
- Create a new issue with:
  - **Summary**: "Add user authentication to login page"
  - **Description**: "Implement OAuth2 with GitHub provider, handle tokens, add security tests"
  - **Status**: "To Do"

### 2. Trigger System
- In Aristotle-I UI, click "Start Automation"
- System fetches your issue automatically

### 3. Review Plan
- **Planner** breaks down the work
- Review the generated plan in UI
- Click ✓ Approve

### 4. Watch Development
- **Developer** generates code
- Real-time logs show progress
- Code pushed to GitHub branch

### 5. Review Quality
- **Reviewer** analyzes code
- Review report shows scores
- Security and standards checks

### 6. Merge & Deploy
- Click ✓ Final Approve
- PR created in GitHub
- You merge to main branch

## Key Environment Variables Explained

| Variable | Example | Purpose |
|----------|---------|---------|
| `LLM_API_KEY` | `your-key-here` | Authentication for LLM |
| `LLM_API_URL` | `https://api.openrouter.ai/api/v1` | LLM provider endpoint |
| `GITHUB_TOKEN` | `ghp_xxxxx` | Git operations |
| `JIRA_SERVER` | `https://your.atlassian.net` | JIRA connection |
| `MONGODB_CONNECTION_STRING` | `mongodb://localhost:27017` | Data storage |
| `MAX_REBUILD_ATTEMPTS` | `3` | Retry limit for failures |

## Useful Commands

### View Logs
```bash
# Docker
docker-compose logs -f aristotle-i

# Local
tail -f logs/app.log
```

### Stop System
```bash
# Docker
docker-compose down

# Local (Ctrl+C in terminal)
```

### Reset Database
```bash
# WARNING: This deletes all data!
docker-compose down -v
docker-compose up -d
```

### Check Health
```bash
# UI Health
curl http://localhost:5173

# API Health (if running)
curl http://localhost:8000/health
```

## Troubleshooting Quick Fixes

### "Connection refused"
```bash
# Make sure MongoDB is running
docker-compose ps

# Restart services
docker-compose restart
```

### "Invalid API key"
- Double-check LLM_API_KEY in .env
- Verify key is copied completely (no extra spaces)
- Test key at provider website

### "GitHub authentication failed"
- Verify GITHUB_TOKEN is correct
- Check token has "repo" scope
- Token not expired

### "JIRA authentication failed"
- JIRA_EMAIL should be your actual email
- JIRA_TOKEN is the API token (not password)
- JIRA_SERVER must include "https://"

### "UI won't load"
```bash
# Port 5173 might be in use
lsof -i :5173  # See what's using it
kill -9 <PID>  # Kill that process

# Restart UI
docker-compose restart web
```

## Next Steps

1. **Read [README.md](README.md)** - Full feature overview
2. **Review [DESIGN.md](DESIGN.md)** - System architecture
3. **Check docs/** - Detailed guides for each component
4. **Join Community** - GitHub Discussions

## Performance Tips

- Use **GPT-4** for Planner/Reviewer (better quality)
- Use **GPT-3.5-turbo** for Developer (faster, cheaper)
- Adjust `REVIEW_THRESHOLD` (higher = stricter)
- Monitor costs with dashboard metrics

## Common Questions

**Q: Can I use a different LLM provider?**  
A: Yes! Configure `LLM_API_URL` to any OpenAI-compatible API. Tested with OpenRouter, OpenAI, and local models.

**Q: What's the minimum compute needed?**  
A: 2GB RAM, 4GB storage. 8GB+ recommended for production.

**Q: Can I run this on my laptop?**  
A: Yes! Docker Desktop includes everything needed.

**Q: Is this production-ready?**  
A: Yes, with proper configuration (secrets management, backups, monitoring).

**Q: How do I customize prompts?**  
A: Edit files in `prompts/` directory. Changes apply immediately.

## Getting Help

- 🐛 **Bugs**: GitHub Issues
- 💬 **Questions**: GitHub Discussions  
- 📖 **Docs**: See [README.md](README.md)
- 🔧 **Configuration**: See docs/CONFIGURATION.md

---

**Stuck?** Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for detailed solutions.

**Ready?** Start your first automation! 🚀

