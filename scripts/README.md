# Deployment Scripts

This directory contains automated deployment scripts for Aristotle-I on various cloud platforms and Kubernetes environments.

## Available Scripts

### 1. GCP Cloud Run Deployment
**File**: `gcp-deploy.sh`

Automates deployment to Google Cloud Run, the serverless container platform.

**Prerequisites**:
- Google Cloud SDK (gcloud) installed and configured
- Docker installed
- GCP project with billing enabled
- Required APIs enabled (Cloud Run, Artifact Registry)

**Usage**:
```bash
GCP_PROJECT_ID=my-project ./gcp-deploy.sh
```

**Features**:
- Automatic Artifact Registry setup
- Docker image build and push
- Cloud Run service deployment
- Environment variable configuration
- Service URL retrieval

**Configuration**:
Create `.env.cloud.gcp` with your environment variables before running.

---

### 2. AWS ECS Deployment
**File**: `aws-deploy.sh`

Automates deployment to Amazon ECS (Elastic Container Service) with Fargate.

**Prerequisites**:
- AWS CLI installed and configured
- Docker installed
- AWS account with ECR and ECS permissions
- CloudWatch Logs permissions

**Usage**:
```bash
AWS_ACCOUNT_ID=123456789012 AWS_REGION=us-east-1 ./aws-deploy.sh
```

**Features**:
- Automatic ECR repository setup
- Docker image build and push
- ECS cluster creation
- CloudWatch log group setup
- Task definition registration
- ECS service creation/update
- Health check configuration

**Configuration**:
The script creates a CloudWatch log group at `/ecs/aristotlei` with 30-day retention.

---

### 3. Kubernetes Manifest Generator
**File**: `k8s-manifest-generator.sh`

Generates complete Kubernetes manifests for deployment to any Kubernetes cluster.

**Prerequisites**:
- kubectl installed
- Access to Kubernetes cluster (GKE, EKS, AKS, or self-hosted)

**Usage**:
```bash
./k8s-manifest-generator.sh /path/to/output my-registry.azurecr.io/aristotlei:latest
```

**Features**:
- ConfigMap for non-sensitive configuration
- Secret template (requires manual credential entry)
- Deployment with resource limits and health checks
- Service (LoadBalancer or ClusterIP)
- Horizontal Pod Autoscaler (HPA)
- ServiceAccount and RBAC
- NetworkPolicy for security
- Ingress configuration (optional)
- Kustomization support

**Generated Files**:
- `configmap.yaml` - Non-sensitive configuration
- `secret.yaml` - Secrets template (⚠️ must be filled with credentials)
- `deployment.yaml` - Main deployment specification
- `service.yaml` - Kubernetes service
- `hpa.yaml` - Horizontal Pod Autoscaler
- `serviceaccount.yaml` - Service account and RBAC
- `networkpolicy.yaml` - Network policies
- `ingress.yaml` - Ingress configuration
- `kustomization.yaml` - Kustomize configuration file
- `DEPLOYMENT_INSTRUCTIONS.md` - Deployment guide

**Deployment**:
```bash
# Apply all manifests
kubectl apply -k /path/to/output

# Check status
kubectl get pods -l app=aristotlei
kubectl logs -l app=aristotlei --tail=100 -f
```

---

## Quick Start by Platform

### Google Cloud Platform (GCP)

#### Option 1: Cloud Run (Easiest)
```bash
# 1. Set your GCP project
export GCP_PROJECT_ID=your-project-id

# 2. Copy environment file
cp .env.example .env.cloud.gcp
# Edit .env.cloud.gcp with your credentials

# 3. Deploy
./scripts/gcp-deploy.sh

# 4. Access your application at the provided URL
```

#### Option 2: GKE (Google Kubernetes Engine)
```bash
# 1. Create cluster
gcloud container clusters create aristotlei \
  --zone us-central1-a \
  --num-nodes 2

# 2. Generate manifests
./scripts/k8s-manifest-generator.sh ./k8s us-central1-docker.pkg.dev/PROJECT/aristotlei/app:latest

# 3. Edit secrets and deploy
kubectl apply -k ./k8s
```

### Amazon Web Services (AWS)

#### Option 1: ECS (Recommended)
```bash
# 1. Set AWS credentials
export AWS_ACCOUNT_ID=123456789012
export AWS_REGION=us-east-1

# 2. Copy environment file
cp .env.example .env.cloud.aws
# Edit .env.cloud.aws with your credentials

# 3. Deploy
./scripts/aws-deploy.sh

# 4. Monitor deployment
aws ecs describe-services --cluster aristotlei --services aristotlei-service
```

#### Option 2: EKS (Kubernetes)
```bash
# 1. Create cluster
aws eks create-cluster \
  --name aristotlei \
  --version 1.27 \
  --roleArn arn:aws:iam::ACCOUNT_ID:role/eks-service-role

# 2. Get credentials
aws eks update-kubeconfig --name aristotlei

# 3. Generate and deploy manifests
./scripts/k8s-manifest-generator.sh ./k8s ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/aristotlei:latest
kubectl apply -k ./k8s
```

### Microsoft Azure

#### Option 1: Container Instances (Simple)
```bash
az container create \
  --resource-group aristotlei \
  --name aristotlei \
  --image myregistry.azurecr.io/aristotlei:latest \
  --ports 8080 \
  --environment-variables UI_PORT=8080
```

#### Option 2: AKS (Kubernetes)
```bash
# 1. Create cluster
az aks create --resource-group aristotlei --name aristotlei

# 2. Get credentials
az aks get-credentials --resource-group aristotlei --name aristotlei

# 3. Deploy manifests
./scripts/k8s-manifest-generator.sh ./k8s myregistry.azurecr.io/aristotlei:latest
kubectl apply -k ./k8s
```

### Local/Self-Hosted

```bash
# 1. Build image
docker build -t aristotlei:latest .

# 2. Generate manifests for your cluster
./scripts/k8s-manifest-generator.sh ./k8s aristotlei:latest

# 3. Update secrets with your credentials
kubectl edit secret aristotlei-secrets

# 4. Deploy
kubectl apply -k ./k8s
```

---

## Common Tasks

### View Deployment Logs
```bash
# GCP Cloud Run
gcloud run services logs read aristotlei

# AWS ECS
aws logs tail /ecs/aristotlei --follow

# Kubernetes
kubectl logs -l app=aristotlei --tail=100 -f
```

### Scale Application
```bash
# Kubernetes (manual)
kubectl scale deployment/aristotlei --replicas=5

# Kubernetes (HPA status)
kubectl get hpa aristotlei-hpa
kubectl describe hpa aristotlei-hpa

# AWS ECS
aws ecs update-service --cluster aristotlei --service aristotlei-service --desired-count 5
```

### Update Environment Variables
```bash
# GCP Cloud Run
gcloud run services update aristotlei --update-env-vars KEY=value

# AWS ECS
# Update task definition and restart service

# Kubernetes
kubectl edit configmap aristotlei-config
kubectl restart deployment/aristotlei
```

### Monitor Health
```bash
# All platforms
curl http://your-service-url/api/health

# Kubernetes
kubectl get pods -l app=aristotlei
kubectl describe pod <pod-name>
```

---

## Troubleshooting

### Script Execution Issues

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run with debug output
bash -x scripts/gcp-deploy.sh
```

### Deployment Failures

See the main [DEPLOYMENT.md](../DEPLOYMENT.md) file for comprehensive troubleshooting guide.

### Environment Variables

All scripts expect environment-specific variables to be configured:
- **GCP**: `.env.cloud.gcp`
- **AWS**: `.env.cloud.aws`
- **Kubernetes**: Secret manifest

See `.env.example` for all available configuration options.

---

## Security Notes

1. **Never commit credentials** to version control
2. **Use secret management** services (AWS Secrets Manager, GCP Secret Manager, etc.)
3. **Rotate API keys** regularly
4. **Enable encryption** for data in transit and at rest
5. **Use RBAC** and network policies to restrict access
6. **Scan images** for vulnerabilities before deployment
7. **Enable auditing** and monitoring

---

## Support

For issues or questions:
- Check the main [DEPLOYMENT.md](../DEPLOYMENT.md) for detailed instructions
- Review environment variable configuration in `.env.example`
- Check cloud provider documentation
- See [README.md](../README.md) for general project information

---

## Contributing

To add support for additional platforms or improve existing scripts:
1. Test thoroughly in target environment
2. Follow existing script patterns and conventions
3. Add comprehensive error handling
4. Update this README with new options
5. Submit changes with documentation


