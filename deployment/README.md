# 🚀 Aristotle-I Deployment Files

This folder contains **ALL** files needed to deploy the Aristotle-I application to Google Cloud Run with a two-server architecture (Frontend + Backend).

---

## 📁 Files in This Folder

### **1. Docker Configuration Files**

| File | Purpose | Size | Description |
|------|---------|------|-------------|
| `Dockerfile` | Backend image | 78 lines | Multi-stage build for Python backend with embedded React frontend |
| `Dockerfile.frontend` | Frontend image | 26 lines | Nginx-based frontend serving React + proxying API calls |
| `nginx.conf` | Nginx config | 58 lines | Reverse proxy configuration with CORS headers |

### **2. Deployment Scripts**

| File | Purpose | Platform | Description |
|------|---------|----------|-------------|
| `deploy-gcp.ps1` | Automated deployment | GCP | PowerShell script to deploy both services to Cloud Run |
| `.gitlab-ci.yml` | CI/CD pipeline | GitLab | Automated build and deployment on git push |

### **3. Configuration Files**

| File | Purpose | Description |
|------|---------|-------------|
| `cloudrun-service.yaml` | Backend config | Complete Cloud Run service configuration with all environment variables |

### **4. Documentation**

| File | Purpose |
|------|---------|
| `COMPLETE_DEPLOYMENT_GUIDE.md` | Comprehensive deployment guide with all commands and configurations |

---

## 🎯 Current Deployment Status

**✅ LIVE SERVICES:**

| Service | URL | Status |
|---------|-----|--------|
| **Frontend (UI)** | https://aristotlei-frontend-996829013147.us-central1.run.app | 🟢 Running |
| **Backend (API)** | https://aristotlei-996829013147.us-central1.run.app | 🟢 Running |

**Custom Domain (Optional):**
- Frontend: `app.aristotlei.com` (if configured)
- Backend: `api.aristotlei.com` (if configured)

---

## 🚀 Quick Deployment

### **Option 1: Automated Script (Recommended)**

```powershell
# Navigate to project root
cd C:\Users\Rahul\multy-agent\aristotlei

# Run deployment script
powershell -ExecutionPolicy Bypass -File deployment\deploy-gcp.ps1
```

**What it does:**
1. ✅ Checks Docker is running
2. ✅ Verifies gcloud authentication
3. ✅ Configures Docker for Artifact Registry
4. ✅ Builds Backend Docker image
5. ✅ Pushes Backend to GCP
6. ✅ Deploys Backend service
7. ✅ Builds Frontend Docker image
8. ✅ Pushes Frontend to GCP
9. ✅ Deploys Frontend service
10. ✅ Shows both service URLs

**Time:** ~10-15 minutes

---

### **Option 2: GitLab CI/CD (Automatic on Push)**

1. **Set up GitLab variables:**
   - Go to: https://gitlab.com/aristotlei/aristotlei/-/settings/ci_cd
   - Add variable: `GCP_SERVICE_ACCOUNT_KEY`
   - Value: Content of service account JSON key file
   - Type: File
   - Protected: Yes
   - Masked: Yes

2. **Push to main branch:**
   ```powershell
   git add .
   git commit -m "Deploy to production"
   git push origin main
   ```

3. **Monitor pipeline:**
   - Pipeline will automatically build and deploy both services
   - Check: https://gitlab.com/aristotlei/aristotlei/-/pipelines

**Time:** ~15-20 minutes (automated)

---

### **Option 3: Manual Step-by-Step**

#### **A. Deploy Backend**

```powershell
# Navigate to project root
cd C:\Users\Rahul\multy-agent\aristotlei

# Build backend image
docker build -t us-central1-docker.pkg.dev/aristote-i/aristotlei/aristotlei:latest .

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/aristote-i/aristotlei/aristotlei:latest

# Deploy using YAML config
gcloud run services replace deployment\cloudrun-service.yaml --region=us-central1
```

#### **B. Deploy Frontend**

```powershell
# Build frontend image
docker build -f deployment\Dockerfile.frontend -t us-central1-docker.pkg.dev/aristote-i/aristotlei/aristotlei-frontend:latest .

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/aristote-i/aristotlei/aristotlei-frontend:latest

# Deploy to Cloud Run
gcloud run deploy aristotlei-frontend --image=us-central1-docker.pkg.dev/aristote-i/aristotlei/aristotlei-frontend:latest --region=us-central1 --port=8080 --memory=512Mi --cpu=1 --allow-unauthenticated
```

---

## 📋 Prerequisites

### **Required Tools:**
- ✅ Docker Desktop (v20.10+)
- ✅ Google Cloud SDK (gcloud CLI)
- ✅ Git
- ✅ PowerShell (Windows) or Bash (Linux/Mac)

### **Required Access:**
- ✅ GCP Project: `aristote-i`
- ✅ Authenticated gcloud account
- ✅ Permissions:
  - `roles/run.admin`
  - `roles/artifactregistry.writer`
  - `roles/iam.serviceAccountUser`

### **Check Prerequisites:**
```powershell
# Check Docker
docker --version
docker info

# Check gcloud
gcloud --version
gcloud config get-value project
gcloud auth list

# Check Git
git --version
```

---

## 🏗️ Architecture

### **Two-Server Deployment:**

```
┌──────────────────────────────┐     ┌─────────────────────────┐
│  Frontend Service (Nginx)    │     │  Backend Service (Python)│
│  aristotlei-frontend         │────▶│  aristotlei             │
│                              │ API │                         │
│  - Serves React UI           │Proxy│  - Handles /api/*       │
│  - Proxies /api/* to backend │     │  - MongoDB, LLMs, etc.  │
│  - Port 8080                 │     │  - Port 8080            │
│  - 512Mi RAM, 1 CPU          │     │  - 4Gi RAM, 2 CPU       │
└──────────────────────────────┘     └─────────────────────────┘
```

**Why Two Services?**
- Matches local development (Vite + Python)
- Independent scaling
- Better resource allocation
- Cleaner separation of concerns

---

## 📝 File Descriptions

### **Dockerfile** (Backend)
Multi-stage Docker build:
1. **Stage 1:** Builds React frontend using Node.js
2. **Stage 2:** Sets up Python backend and copies built frontend

**Key Features:**
- Python 3.11 slim base
- Installs all Python dependencies from `requirements.txt`
- Copies frontend build to `/app/static`
- Creates non-root user for security
- Exposes port 8080
- Includes health check

### **Dockerfile.frontend** (Frontend)
Nginx-based frontend service:
1. **Stage 1:** Builds React app with Node.js
2. **Stage 2:** Serves from Nginx

**Key Features:**
- Node.js 20 Alpine for building
- Nginx Alpine for serving
- Copies nginx.conf for configuration
- Optimized for production

### **nginx.conf**
Nginx reverse proxy configuration:
- Serves static files from `/usr/share/nginx/html`
- Proxies `/api/*` requests to backend service
- Adds CORS headers for cross-origin requests
- Handles React Router (SPA routing)
- Caches static assets
- Listens on port 8080

### **cloudrun-service.yaml**
Complete Cloud Run service specification:
- Service name: `aristotlei`
- Region: `us-central1`
- Resources: 4Gi RAM, 2 CPU
- Auto-scaling: 0-10 instances
- All 50+ environment variables configured
- Timeout: 3600 seconds (1 hour)

### **deploy-gcp.ps1**
Automated PowerShell deployment script:
- 10-step deployment process
- Builds and deploys both services
- Error handling and status messages
- Displays service URLs at completion

### **.gitlab-ci.yml**
GitLab CI/CD pipeline:
- 3 stages: build, deploy, verify
- Separate jobs for backend and frontend
- Automated on push to `main` branch
- Health checks after deployment

---

## ✅ Verification Commands

### **Check Services:**
```powershell
# List Cloud Run services
gcloud run services list --region=us-central1

# Describe backend service
gcloud run services describe aristotlei --region=us-central1

# Describe frontend service
gcloud run services describe aristotlei-frontend --region=us-central1
```

### **Test Endpoints:**
```powershell
# Test backend API
curl https://aristotlei-996829013147.us-central1.run.app/api/health
curl https://aristotlei-996829013147.us-central1.run.app/api/status

# Open frontend in browser
Start-Process https://aristotlei-frontend-996829013147.us-central1.run.app
```

### **View Logs:**
```powershell
# Backend logs
gcloud run services logs read aristotlei --region=us-central1 --limit=50

# Frontend logs
gcloud run services logs read aristotlei-frontend --region=us-central1 --limit=50

# Stream logs in real-time
gcloud run services logs tail aristotlei --region=us-central1 --follow
```

---

## 🔄 Update Deployment

### **Update Backend Only:**
```powershell
cd C:\Users\Rahul\multy-agent\aristotlei

# Make code changes, then:
docker build -t us-central1-docker.pkg.dev/aristote-i/aristotlei/aristotlei:latest .
docker push us-central1-docker.pkg.dev/aristote-i/aristotlei/aristotlei:latest
gcloud run services replace deployment\cloudrun-service.yaml --region=us-central1
```

### **Update Frontend Only:**
```powershell
cd C:\Users\Rahul\multy-agent\aristotlei

# Make code changes to Agentic_UI/src/, then:
docker build -f deployment\Dockerfile.frontend -t us-central1-docker.pkg.dev/aristote-i/aristotlei/aristotlei-frontend:latest .
docker push us-central1-docker.pkg.dev/aristote-i/aristotlei/aristotlei-frontend:latest
gcloud run deploy aristotlei-frontend --region=us-central1 --image=us-central1-docker.pkg.dev/aristote-i/aristotlei/aristotlei-frontend:latest
```

### **Update Both Services:**
```powershell
cd C:\Users\Rahul\multy-agent\aristotlei
powershell -ExecutionPolicy Bypass -File deployment\deploy-gcp.ps1
```

---

## 🌐 Custom Domain Setup

To use your `aristotlei.com` domain:

1. **Map domains in GCP Console:**
   - Frontend: https://console.cloud.google.com/run/detail/us-central1/aristotlei-frontend?project=aristote-i
   - Backend: https://console.cloud.google.com/run/detail/us-central1/aristotlei?project=aristote-i
   - Click "INTEGRATIONS" → "MANAGE CUSTOM DOMAINS"
   - Enter: `app.aristotlei.com` and `api.aristotlei.com`

2. **Add DNS records in Hostinger:**
   - Login: https://hpanel.hostinger.com/
   - Go to: Domains → aristotlei.com → DNS
   - Add CNAME records:
     ```
     Type: CNAME, Name: app, Points to: ghs.googlehosted.com
     Type: CNAME, Name: api, Points to: ghs.googlehosted.com
     ```

3. **Wait for DNS propagation** (15-30 minutes)

4. **Test:**
   ```powershell
   Start-Process https://app.aristotlei.com
   ```

**See `CUSTOM_DOMAIN_SETUP.md` for detailed instructions**

---

## 🐛 Troubleshooting

### **Build Fails:**
```powershell
# Clear Docker cache
docker system prune -af

# Rebuild without cache
docker build --no-cache -t <image-tag> .
```

### **Push Fails:**
```powershell
# Re-authenticate
gcloud auth login
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
```

### **Deployment Fails:**
```powershell
# Check logs
gcloud run services logs read <service-name> --region=us-central1 --limit=100

# Check service status
gcloud run services describe <service-name> --region=us-central1
```

### **Frontend Shows White Screen:**
- Check browser console (F12) for errors
- Verify nginx.conf has correct backend URL
- Ensure CORS headers are present

### **API Calls Fail:**
- Verify backend service is running
- Check nginx proxy configuration
- Test backend directly: `curl <backend-url>/api/health`

---

## 💰 Cost Estimate

| Service | Resources | Monthly Cost (Moderate Traffic) |
|---------|-----------|--------------------------------|
| Backend | 4Gi RAM, 2 CPU | ~$10-15 |
| Frontend | 512Mi RAM, 1 CPU | ~$2-5 |
| Artifact Registry | ~20GB storage | ~$0.50 |
| **Total** | | **~$15-20/month** |

*Based on 1000 requests/day with Cloud Run's generous free tier*

---

## 📚 Additional Documentation

- **Full Guide:** `COMPLETE_DEPLOYMENT_GUIDE.md` - Complete step-by-step with all options
- **Main README:** `../README.md` - Project overview and features
- **Scripts README:** `../scripts/README.md` - Alternative deployment scripts

---

## ✅ Deployment Checklist

**Before Deployment:**
- [ ] Docker Desktop installed and running
- [ ] gcloud CLI authenticated
- [ ] GCP project created (aristote-i)
- [ ] Billing enabled
- [ ] Artifact Registry API enabled
- [ ] Cloud Run API enabled

**During Deployment:**
- [ ] Backend image built
- [ ] Backend image pushed
- [ ] Backend deployed to Cloud Run
- [ ] Frontend image built
- [ ] Frontend image pushed
- [ ] Frontend deployed to Cloud Run

**After Deployment:**
- [ ] Both services show "Ready" status
- [ ] Backend API responds to health checks
- [ ] Frontend loads in browser
- [ ] Logo displays correctly
- [ ] Workflow section works (not stuck on "Loading...")
- [ ] No CORS errors in browser console

---

## 🎊 Success Criteria

Your deployment is successful when:

1. ✅ Both services return 200 OK status
2. ✅ Frontend UI loads with all components
3. ✅ Aristotlei logo visible in sidebar
4. ✅ Workflow status loads (not "Loading...")
5. ✅ API calls work from frontend
6. ✅ No errors in browser console
7. ✅ Services accessible via URLs

---

## 📞 Support

**GCP Resources:**
- Cloud Run Console: https://console.cloud.google.com/run?project=aristote-i
- Artifact Registry: https://console.cloud.google.com/artifacts?project=aristote-i
- Logs: https://console.cloud.google.com/logs?project=aristote-i

**GitLab CI/CD:**
- Repository: https://gitlab.com/aristotlei/aristotlei
- Pipelines: https://gitlab.com/aristotlei/aristotlei/-/pipelines
- Settings: https://gitlab.com/aristotlei/aristotlei/-/settings/ci_cd

**DNS/Domain:**
- Hostinger: https://hpanel.hostinger.com/
- DNS Checker: https://dnschecker.org

---

**Last Updated:** October 28, 2025  
**Status:** ✅ Production Ready  
**Deployment Method:** Two-Server Architecture (Frontend + Backend)  
**Platform:** Google Cloud Run

