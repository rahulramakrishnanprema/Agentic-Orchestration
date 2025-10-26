# 🚀 Aristotle-I Deployment - Quick Start

## Choose Your Deployment Path

### 1️⃣ Local Development (5 minutes)
```bash
cp .env.example .env
nano .env              # Edit with your credentials
docker-compose up -d
curl http://localhost:8080/api/health
```
**Includes**: Application, MongoDB, MongoDB Express UI

**Access**:
- App: http://localhost:8080
- MongoDB UI: http://localhost:8081
- API Health: http://localhost:8080/api/health

---

### 2️⃣ GCP Cloud Run (10 minutes) ⭐ EASIEST
```bash
export GCP_PROJECT_ID=my-project
cp .env.example .env.cloud.gcp
nano .env.cloud.gcp    # Edit with credentials
./scripts/gcp-deploy.sh
```
**Features**: Serverless, auto-scaling, no ops overhead

---

### 3️⃣ AWS ECS (15 minutes)
```bash
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-east-1
cp .env.example .env.cloud.aws
nano .env.cloud.aws    # Edit with credentials
./scripts/aws-deploy.sh
```
**Features**: Managed containers, CloudWatch logs, auto-scaling

---

### 4️⃣ Kubernetes (20 minutes)
```bash
./scripts/k8s-manifest-generator.sh ./k8s my-registry/aristotlei:latest
kubectl edit secret aristotlei-secrets
kubectl apply -k ./k8s
kubectl get pods -l app=aristotlei
```
**Features**: Maximum control, multi-cloud, enterprise-ready

---

## 📋 Required Credentials

Before starting, gather:
- **LLM**: API keys (OpenAI, OpenRouter, or compatible)
- **GitHub**: Personal access token
- **Jira**: Email and API token
- **SonarQube**: Token and host URL
- **MongoDB**: Connection string

See `.env.example` for all 50+ configuration variables.

---

## 📂 Key Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Container definition |
| `docker-compose.yml` | Local dev environment |
| `.env.example` | Configuration template |
| `DEPLOYMENT.md` | Complete guide for all platforms |
| `scripts/*.sh` | Automation scripts |

---

## 🆘 Need Help?

- **Getting started**: This file
- **Detailed instructions**: Read `DEPLOYMENT.md`
- **Docker specifics**: See Docker section in `DEPLOYMENT.md`
- **Troubleshooting**: `DEPLOYMENT.md` → Troubleshooting section
- **Script help**: `scripts/README.md`

---

## ✅ Success Checklist

- [ ] Gathered all required credentials
- [ ] Created `.env` or `.env.cloud.{platform}` file
- [ ] Started deployment (docker-compose or script)
- [ ] Verified health endpoint responds
- [ ] Checked logs for errors

---

**Next Step**: Choose your platform above and follow the commands, or read `DEPLOYMENT.md` for detailed instructions.

