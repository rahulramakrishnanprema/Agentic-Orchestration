#!/bin/bash

# GCP Cloud Run Deployment Script for Aristotle-I
# This script automates the deployment of Aristotle-I to Google Cloud Run
# Prerequisites: gcloud CLI installed and authenticated

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="aristotlei"
IMAGE_NAME="app"
REPOSITORY_NAME="aristotlei"
MEMORY="4Gi"
CPU="2"
TIMEOUT="3600"

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

check_prerequisites() {
    print_info "Checking prerequisites..."

    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI not found. Please install it first."
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install it first."
        exit 1
    fi

    print_success "Prerequisites check passed"
}

validate_project_id() {
    if [ -z "$PROJECT_ID" ]; then
        print_error "GCP_PROJECT_ID environment variable not set"
        echo "Usage: GCP_PROJECT_ID=your-project gcp-deploy.sh"
        exit 1
    fi
    print_success "Project ID: $PROJECT_ID"
}

setup_gcp_environment() {
    print_info "Setting up GCP environment..."

    gcloud config set project "$PROJECT_ID"

    print_info "Enabling required APIs..."
    gcloud services enable run.googleapis.com
    gcloud services enable artifactregistry.googleapis.com
    gcloud services enable cloudbuild.googleapis.com

    print_success "GCP environment ready"
}

setup_artifact_registry() {
    print_info "Setting up Artifact Registry..."

    # Check if repository exists
    if gcloud artifacts repositories describe "$REPOSITORY_NAME" \
        --location="$REGION" &>/dev/null; then
        print_success "Repository already exists: $REPOSITORY_NAME"
    else
        print_info "Creating repository: $REPOSITORY_NAME"
        gcloud artifacts repositories create "$REPOSITORY_NAME" \
            --repository-format=docker \
            --location="$REGION" \
            --description="Aristotle-I Container Repository"
        print_success "Repository created"
    fi

    # Configure Docker authentication
    print_info "Configuring Docker authentication..."
    gcloud auth configure-docker "${REGION}-docker.pkg.dev"

    print_success "Artifact Registry configured"
}

build_and_push_image() {
    print_info "Building Docker image..."

    FULL_IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_NAME}/${IMAGE_NAME}:latest"

    docker build -t "$FULL_IMAGE_URI" .

    print_success "Image built: $FULL_IMAGE_URI"

    print_info "Pushing image to Artifact Registry..."
    docker push "$FULL_IMAGE_URI"

    print_success "Image pushed successfully"

    echo "$FULL_IMAGE_URI"
}

deploy_to_cloud_run() {
    local image_uri=$1

    print_info "Deploying to Cloud Run..."

    gcloud run deploy "$SERVICE_NAME" \
        --image="$image_uri" \
        --platform=managed \
        --region="$REGION" \
        --port=8080 \
        --memory="$MEMORY" \
        --cpu="$CPU" \
        --timeout="$TIMEOUT" \
        --allow-unauthenticated \
        --no-gen2 \
        --set-env-vars="UI_PORT=8080,REACT_DEV_PORT=5173"

    print_success "Deployment initiated"
}

update_environment_variables() {
    print_info "Setting environment variables on Cloud Run service..."

    # Check if .env.cloud.gcp exists
    if [ ! -f ".env.cloud.gcp" ]; then
        print_error "File .env.cloud.gcp not found"
        echo "Please create .env.cloud.gcp with your environment variables"
        exit 1
    fi

    # Parse .env.cloud.gcp and set variables
    local env_vars=""
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ "$key" =~ ^[[:space:]]*# ]] && continue
        [[ -z "$key" ]] && continue

        env_vars="${env_vars}${key}=${value},"
    done < .env.cloud.gcp

    # Remove trailing comma
    env_vars="${env_vars%,}"

    if [ -z "$env_vars" ]; then
        print_error "No environment variables found in .env.cloud.gcp"
        exit 1
    fi

    gcloud run services update "$SERVICE_NAME" \
        --region="$REGION" \
        --update-env-vars "$env_vars"

    print_success "Environment variables set"
}

get_service_url() {
    print_info "Retrieving service URL..."

    local service_url=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format='value(status.url)')

    print_success "Service deployed successfully!"
    echo ""
    echo "Service URL: $service_url"
    echo ""
    echo "Next steps:"
    echo "1. Access the application at: $service_url"
    echo "2. Check service status: gcloud run services describe $SERVICE_NAME --region=$REGION"
    echo "3. View logs: gcloud run services logs read $SERVICE_NAME --region=$REGION"
}

main() {
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║     Aristotle-I - GCP Cloud Run Deployment Script             ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""

    check_prerequisites
    validate_project_id
    setup_gcp_environment
    setup_artifact_registry

    local image_uri
    image_uri=$(build_and_push_image)

    deploy_to_cloud_run "$image_uri"

    print_info "Would you like to update environment variables? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        update_environment_variables
    fi

    get_service_url
}

# Run main function
main "$@"

