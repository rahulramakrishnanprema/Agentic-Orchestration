# Aristotle-I Deployment Package - Quick Reference Card

## 📚 Documentation Files (Minimal Set)

| File | Purpose | Read When |
|------|---------|-----------|
| **START.md** | Quick start for all platforms | First thing! |
| **DEPLOYMENT.md** | Complete reference guide | You need details |
| **CONSOLIDATION_SUMMARY.md** | What was consolidated | You're curious |

---

## 🚀 Deploy in 4 Steps

### 1. Get Credentials
- LLM API key (OpenAI, OpenRouter, etc.)
- GitHub token
- Jira credentials
- SonarQube token
- MongoDB connection string

### 2. Configure Environment
```bash
cp .env.example .env
nano .env  # Add your credentials
```

### 3. Choose Your Platform

**Local (5 min)**
```bash
docker-compose up -d
curl http://localhost:8080/api/health
```

**GCP Cloud Run (10 min)**
```bash
export GCP_PROJECT_ID=your-project
cp .env.example .env.cloud.gcp
nano .env.cloud.gcp
./scripts/gcp-deploy.sh
```

**AWS ECS (15 min)**
```bash
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-east-1
cp .env.example .env.cloud.aws
nano .env.cloud.aws
./scripts/aws-deploy.sh
```

**Kubernetes (20 min)**
```bash
./scripts/k8s-manifest-generator.sh ./k8s image:tag
kubectl edit secret aristotlei-secrets
kubectl apply -k ./k8s
```

### 4. Verify
```bash
curl http://your-url/api/health
```

---

## 📂 File Structure

```
aristotlei/
├── Dockerfile              ← Container definition
├── docker-compose.yml      ← Local dev environment
├── .env.example            ← Configuration template
│
├── START.md               ← 🎯 START HERE!
├── DEPLOYMENT.md          ← Complete guide
├── CONSOLIDATION_SUMMARY.md ← What was changed
│
└── scripts/
    ├── gcp-deploy.sh      ← GCP automation
    ├── aws-deploy.sh      ← AWS automation
    ├── k8s-manifest-generator.sh ← K8s
    └── README.md          ← Scripts help
```

---

## ⚡ Common Commands

**Build Docker image:**
```bash
docker build -t aristotlei:latest .
```

**Start local environment:**
```bash
docker-compose up -d
```

**View logs:**
```bash
docker-compose logs -f aristotlei
```

**Deploy to GCP:**
```bash
GCP_PROJECT_ID=project ./scripts/gcp-deploy.sh
```

**Deploy to AWS:**
```bash
AWS_ACCOUNT_ID=12345 AWS_REGION=us-east-1 ./scripts/aws-deploy.sh
```

---

## 🆘 Need Help?

| Problem | Solution |
|---------|----------|
| Don't know where to start | Open **START.md** |
| Need detailed instructions | Open **DEPLOYMENT.md** |
| Docker questions | See DEPLOYMENT.md Docker section |
| Script issues | Check **scripts/README.md** |
| Troubleshooting | DEPLOYMENT.md → Troubleshooting |

---

## ✅ Success Checklist

- [ ] Gathered credentials (LLM, GitHub, Jira, SonarQube, MongoDB)
- [ ] Created .env file
- [ ] Tested locally with docker-compose
- [ ] Built and deployed to cloud
- [ ] Verified health endpoint
- [ ] Checked logs for errors

---

**Quick Start**: `cat START.md` then copy commands for your platform.

**Status**: ✅ Production Ready | **Updated**: October 26, 2025

