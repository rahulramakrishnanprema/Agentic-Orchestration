#!/bin/bash
# GCP Setup Script for Aristote-I Project
# Run this script to set up your GCP environment automatically

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="aristote-i"
PROJECT_NAME="Aristote-I"
REGION="us-central1"
SERVICE_ACCOUNT_NAME="gitlab-deployer"
REPOSITORY_NAME="aristotlei"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Aristote-I GCP Setup Script                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Project ID: ${PROJECT_ID}"
echo "Project Name: ${PROJECT_NAME}"
echo "Region: ${REGION}"
echo ""

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

# Function to print info
print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install it first."
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi
print_success "gcloud CLI found"

# Login check
print_info "Checking authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q "@"; then
    print_info "Please login to gcloud..."
    gcloud auth login
fi
print_success "Authenticated"

# Create project
print_info "Creating GCP project: ${PROJECT_ID}..."
if gcloud projects describe ${PROJECT_ID} &>/dev/null; then
    print_success "Project already exists: ${PROJECT_ID}"
else
    gcloud projects create ${PROJECT_ID} --name="${PROJECT_NAME}"
    print_success "Project created: ${PROJECT_ID}"
fi

# Set project
gcloud config set project ${PROJECT_ID}
print_success "Project set to: ${PROJECT_ID}"

# Enable billing (you need to do this manually if not already done)
print_info "Note: Make sure billing is enabled for this project"
print_info "Visit: https://console.cloud.google.com/billing/linkedaccount?project=${PROJECT_ID}"

# Enable APIs
print_info "Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable compute.googleapis.com
print_success "APIs enabled"

# Create service account
print_info "Creating service account..."
if gcloud iam service-accounts describe ${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com &>/dev/null; then
    print_success "Service account already exists"
else
    gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
        --description="GitLab CI/CD Deployer" \
        --display-name="GitLab Deployer"
    print_success "Service account created"
fi

# Grant permissions
print_info "Granting permissions to service account..."
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/run.admin" \
    --quiet

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/artifactregistry.admin" \
    --quiet

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/iam.serviceAccountUser" \
    --quiet

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/storage.admin" \
    --quiet

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/cloudbuild.builds.editor" \
    --quiet

print_success "Permissions granted"

# Create service account key
print_info "Creating service account key..."
KEY_FILE="gitlab-deployer-key.json"
gcloud iam service-accounts keys create ${KEY_FILE} \
    --iam-account=${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com
print_success "Service account key created: ${KEY_FILE}"

# Create Artifact Registry repository
print_info "Creating Artifact Registry repository..."
if gcloud artifacts repositories describe ${REPOSITORY_NAME} --location=${REGION} &>/dev/null; then
    print_success "Repository already exists"
else
    gcloud artifacts repositories create ${REPOSITORY_NAME} \
        --repository-format=docker \
        --location=${REGION} \
        --description="Aristotle-I Docker Images"
    print_success "Repository created"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Setup Complete! ✅                                         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Copy the service account key to GitLab:"
echo "   File: ${KEY_FILE}"
echo "   Location: $(pwd)/${KEY_FILE}"
echo ""
echo "2. Add to GitLab CI/CD Variables:"
echo "   Settings → CI/CD → Variables → Add variable"
echo ""
echo "   Variable 1:"
echo "   Key:   GCP_PROJECT_ID"
echo "   Value: ${PROJECT_ID}"
echo ""
echo "   Variable 2:"
echo "   Key:   GCP_REGION"
echo "   Value: ${REGION}"
echo ""
echo "   Variable 3:"
echo "   Key:   GCP_SERVICE_ACCOUNT_KEY"
echo "   Value: <paste entire content of ${KEY_FILE}>"
echo ""
echo "3. View the service account key:"
echo "   cat ${KEY_FILE}"
echo ""
echo "4. Push to GitLab and watch the pipeline run!"
echo ""
echo "🔗 Useful Links:"
echo "   GCP Console: https://console.cloud.google.com/home/dashboard?project=${PROJECT_ID}"
echo "   Cloud Run: https://console.cloud.google.com/run?project=${PROJECT_ID}"
echo "   Artifact Registry: https://console.cloud.google.com/artifacts?project=${PROJECT_ID}"
echo ""
echo "⚠️  IMPORTANT: Keep ${KEY_FILE} secure! Add it to .gitignore"
echo ""

