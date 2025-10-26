#!/bin/bash

# Kubernetes Manifest Generator for Aristotle-I
# This script generates Kubernetes manifests for deployment
# Usage: ./k8s-manifest-generator.sh <output-dir> <image-uri>

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Functions
print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Configuration
OUTPUT_DIR="${1:-.}"
IMAGE_URI="${2:-aristotlei:latest}"
NAMESPACE="default"
APP_NAME="aristotlei"
REPLICAS="2"

# Validate arguments
if [ ! -d "$OUTPUT_DIR" ]; then
    print_error "Output directory does not exist: $OUTPUT_DIR"
    exit 1
fi

# Create ConfigMap
print_info "Generating ConfigMap..."
cat > "$OUTPUT_DIR/configmap.yaml" <<'EOF'
apiVersion: v1
kind: ConfigMap
metadata:
  name: aristotlei-config
  labels:
    app: aristotlei
data:
  UI_PORT: "8080"
  REACT_DEV_PORT: "5173"
  LOG_LEVEL: "INFO"
  DEBUG: "false"
  REVIEW_THRESHOLD: "0.75"
  GOT_SCORE_THRESHOLD: "0.70"
  MAX_REBUILD_ATTEMPTS: "3"
  HITL_TIMEOUT_SECONDS: "300"
  REVIEW_BRANCH_NAME: "ai-review"
  STANDARDS_FOLDER: "./standards"
  PLANNER_LLM_TEMPERATURE: "0.3"
  DEVELOPER_LLM_TEMPERATURE: "0.3"
  REVIEWER_LLM_TEMPERATURE: "0.3"
  ASSEMBLER_LLM_TEMPERATURE: "0.3"
  MONGODB_ENABLED: "true"
EOF
print_success "ConfigMap generated"

# Create Secret
print_info "Generating Secret template..."
cat > "$OUTPUT_DIR/secret.yaml" <<'EOF'
apiVersion: v1
kind: Secret
metadata:
  name: aristotlei-secrets
  labels:
    app: aristotlei
type: Opaque
stringData:
  MONGODB_CONNECTION_STRING: "mongodb+srv://user:password@cluster.mongodb.net/aristotlei"
  GITHUB_TOKEN: "ghp_YOUR_GITHUB_TOKEN"
  GITHUB_REPO_OWNER: "your-org"
  GITHUB_REPO_NAME: "your-repo"
  JIRA_SERVER: "https://your-instance.atlassian.net"
  JIRA_EMAIL: "your-email@company.com"
  JIRA_TOKEN: "your-jira-api-token"
  PROJECT_KEY: "PROJ"
  SONAR_HOST_URL: "https://your-sonarqube-instance.com"
  SONAR_TOKEN: "your-sonarqube-token"
  SONAR_ORG: "your-org"
  SONAR_PROJECT_KEY: "your-project-key"
  PLANNER_LLM_KEY: "sk-your-openai-key"
  DEVELOPER_LLM_KEY: "sk-your-openai-key"
  REVIEWER_LLM_KEY: "sk-your-openai-key"
  ASSEMBLER_LLM_KEY: "sk-your-openai-key"
  PLANNER_LLM_MODEL: "gpt-4"
  DEVELOPER_LLM_MODEL: "gpt-4"
  REVIEWER_LLM_MODEL: "gpt-4"
  ASSEMBLER_LLM_MODEL: "gpt-4"
  MONGODB_DATABASE: "aristotlei"
  MONGODB_COLLECTION_MATRIX: "performance_matrix"
  MONGODB_PERFORMANCE_DATABASE: "performance_db"
  MONGODB_AGENT_PERFORMANCE: "agent_perf"
  MONGODB_REVIEWER_COLLECTION: "reviewer_results"
  MONGODB_FEEDBACK_DATABASE: "feedback_db"
  DEVELOPER_AGENT_FEEDBACK: "dev_feedback"
  ASSEMBLER_FEEDBACK: "assembler_feedback"
EOF
print_success "Secret template generated"

# Create Deployment
print_info "Generating Deployment..."
cat > "$OUTPUT_DIR/deployment.yaml" <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $APP_NAME
  labels:
    app: $APP_NAME
    version: v1
spec:
  replicas: $REPLICAS
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: $APP_NAME
  template:
    metadata:
      labels:
        app: $APP_NAME
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "8000"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: $APP_NAME
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: $APP_NAME
        image: $IMAGE_URI
        imagePullPolicy: Always
        ports:
        - containerPort: 8080
          name: http
          protocol: TCP
        - containerPort: 8000
          name: metrics
          protocol: TCP
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
          timeoutSeconds: 10
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8080
          initialDelaySeconds: 20
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: false
          runAsNonRoot: true
          capabilities:
            drop:
              - ALL
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /home/aristotlei/.cache
      volumes:
      - name: tmp
        emptyDir: {}
      - name: cache
        emptyDir: {}
      affinity:
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            podAffinityTerm:
              labelSelector:
                matchExpressions:
                - key: app
                  operator: In
                  values:
                  - $APP_NAME
              topologyKey: kubernetes.io/hostname
EOF
print_success "Deployment generated"

# Create Service
print_info "Generating Service..."
cat > "$OUTPUT_DIR/service.yaml" <<EOF
apiVersion: v1
kind: Service
metadata:
  name: $APP_NAME-service
  labels:
    app: $APP_NAME
spec:
  type: LoadBalancer
  selector:
    app: $APP_NAME
  ports:
  - name: http
    port: 80
    targetPort: 8080
    protocol: TCP
  - name: metrics
    port: 8000
    targetPort: 8000
    protocol: TCP
  sessionAffinity: None
EOF
print_success "Service generated"

# Create Horizontal Pod Autoscaler
print_info "Generating HPA..."
cat > "$OUTPUT_DIR/hpa.yaml" <<EOF
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: $APP_NAME-hpa
  labels:
    app: $APP_NAME
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: $APP_NAME
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Max
EOF
print_success "HPA generated"

# Create ServiceAccount and RBAC
print_info "Generating ServiceAccount and RBAC..."
cat > "$OUTPUT_DIR/serviceaccount.yaml" <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: $APP_NAME
  labels:
    app: $APP_NAME

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: $APP_NAME-role
  labels:
    app: $APP_NAME
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list", "watch"]
- apiGroups: [""]
  resources: ["configmaps"]
  verbs: ["get", "list"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: $APP_NAME-rolebinding
  labels:
    app: $APP_NAME
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: $APP_NAME-role
subjects:
- kind: ServiceAccount
  name: $APP_NAME
EOF
print_success "ServiceAccount and RBAC generated"

# Create NetworkPolicy
print_info "Generating NetworkPolicy..."
cat > "$OUTPUT_DIR/networkpolicy.yaml" <<EOF
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: $APP_NAME-network-policy
  labels:
    app: $APP_NAME
spec:
  podSelector:
    matchLabels:
      app: $APP_NAME
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          ingress: "true"
    - podSelector:
        matchLabels:
          app: ingress-nginx
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
    - protocol: TCP
      port: 80
EOF
print_success "NetworkPolicy generated"

# Create Ingress
print_info "Generating Ingress..."
cat > "$OUTPUT_DIR/ingress.yaml" <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: $APP_NAME-ingress
  labels:
    app: $APP_NAME
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - aristotlei.example.com
    secretName: aristotlei-tls
  rules:
  - host: aristotlei.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: $APP_NAME-service
            port:
              number: 80
EOF
print_success "Ingress generated"

# Create kustomization.yaml
print_info "Generating kustomization.yaml..."
cat > "$OUTPUT_DIR/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

namespace: default

resources:
  - configmap.yaml
  - secret.yaml
  - serviceaccount.yaml
  - deployment.yaml
  - service.yaml
  - hpa.yaml
  - networkpolicy.yaml

commonLabels:
  app: $APP_NAME
  environment: production

commonAnnotations:
  managed-by: "kubernetes"

replicas:
- name: $APP_NAME
  count: $REPLICAS
EOF
print_success "kustomization.yaml generated"

# Create deployment instructions
print_info "Generating deployment instructions..."
cat > "$OUTPUT_DIR/DEPLOYMENT_INSTRUCTIONS.md" <<'EOF'
# Kubernetes Deployment Instructions

## Prerequisites

1. Kubernetes cluster running (1.24+)
2. kubectl configured with cluster access
3. All required environment variables available

## Step 1: Update Configuration

Edit the following files with your actual values:

- **secret.yaml**: Replace all placeholder values with actual credentials
- **ingress.yaml**: Update the hostname to your domain
- **kustomization.yaml**: Adjust namespace if needed

```bash
# Edit secret file
kubectl edit secret aristotlei-secrets --record
```

## Step 2: Deploy Using Kustomize

```bash
# Validate manifests
kubectl kustomize ./

# Deploy all resources
kubectl apply -k ./

# Check deployment status
kubectl get deployments
kubectl get pods
kubectl get services
```

## Step 3: Verify Deployment

```bash
# Check pod status
kubectl get pods -l app=aristotlei

# Check logs
kubectl logs -l app=aristotlei --tail=100 -f

# Check service
kubectl get svc aristotlei-service

# Port forward for local testing
kubectl port-forward svc/aristotlei-service 8080:80
```

## Step 4: Check Health

```bash
# Health check endpoint
curl http://localhost:8080/api/health

# Check metrics
curl http://localhost:8000/metrics
```

## Scaling

```bash
# Manual scaling
kubectl scale deployment/aristotlei --replicas=5

# HPA status
kubectl get hpa aristotlei-hpa
kubectl describe hpa aristotlei-hpa
```

## Troubleshooting

```bash
# Get detailed pod information
kubectl describe pod <pod-name>

# Check events
kubectl get events --sort-by='.lastTimestamp'

# View logs
kubectl logs <pod-name>
kubectl logs <pod-name> --previous  # For crashed containers

# Debug with shell
kubectl exec -it <pod-name> -- /bin/bash
```

## Cleanup

```bash
kubectl delete -k ./
```
EOF
print_success "Deployment instructions generated"

# Summary
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║         Kubernetes Manifests Generated Successfully            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Generated files in: $OUTPUT_DIR"
echo ""
echo "Files created:"
echo "  ✓ configmap.yaml"
echo "  ✓ secret.yaml (⚠️  EDIT WITH YOUR CREDENTIALS)"
echo "  ✓ deployment.yaml"
echo "  ✓ service.yaml"
echo "  ✓ hpa.yaml"
echo "  ✓ serviceaccount.yaml"
echo "  ✓ networkpolicy.yaml"
echo "  ✓ ingress.yaml (⚠️  EDIT WITH YOUR DOMAIN)"
echo "  ✓ kustomization.yaml"
echo "  ✓ DEPLOYMENT_INSTRUCTIONS.md"
echo ""
echo "Next steps:"
echo "1. Edit secret.yaml with your credentials"
echo "2. Edit ingress.yaml with your domain"
echo "3. Run: kubectl apply -k ./$OUTPUT_DIR"
echo ""

