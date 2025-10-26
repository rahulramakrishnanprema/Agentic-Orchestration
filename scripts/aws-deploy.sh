#!/bin/bash

# AWS ECS Deployment Script for Aristotle-I
# This script automates the deployment of Aristotle-I to Amazon ECS
# Prerequisites: AWS CLI installed and configured

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:-}"
REPOSITORY_NAME="aristotlei"
SERVICE_NAME="aristotlei-service"
CLUSTER_NAME="aristotlei"
TASK_FAMILY="aristotlei"
IMAGE_TAG="latest"

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

    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install it first."
        exit 1
    fi

    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Please install it first."
        exit 1
    fi

    print_success "Prerequisites check passed"
}

validate_aws_credentials() {
    if [ -z "$AWS_ACCOUNT_ID" ]; then
        print_error "AWS_ACCOUNT_ID environment variable not set"
        echo "Usage: AWS_ACCOUNT_ID=123456789012 aws-deploy.sh"
        exit 1
    fi

    # Verify AWS credentials work
    if ! aws sts get-caller-identity &>/dev/null; then
        print_error "AWS credentials not configured or invalid"
        exit 1
    fi

    print_success "AWS Account ID: $AWS_ACCOUNT_ID"
    print_success "AWS Region: $AWS_REGION"
}

setup_ecr_repository() {
    print_info "Setting up ECR Repository..."

    local repository_uri="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPOSITORY_NAME}"

    # Check if repository exists
    if aws ecr describe-repositories \
        --repository-names "$REPOSITORY_NAME" \
        --region "$AWS_REGION" &>/dev/null; then
        print_success "ECR repository already exists: $repository_uri"
    else
        print_info "Creating ECR repository..."
        aws ecr create-repository \
            --repository-name "$REPOSITORY_NAME" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true \
            --image-tag-mutability MUTABLE
        print_success "ECR repository created"
    fi

    # Get login token and configure Docker
    print_info "Configuring Docker authentication with ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin "$repository_uri"

    print_success "Docker authentication configured"

    echo "$repository_uri"
}

build_and_push_image() {
    local repository_uri=$1

    print_info "Building Docker image..."

    local image_uri="${repository_uri}:${IMAGE_TAG}"

    docker build -t "$image_uri" .

    print_success "Image built: $image_uri"

    print_info "Pushing image to ECR..."
    docker push "$image_uri"

    print_success "Image pushed successfully"

    echo "$image_uri"
}

create_ecs_cluster() {
    print_info "Checking/Creating ECS Cluster..."

    if aws ecs describe-clusters \
        --clusters "$CLUSTER_NAME" \
        --region "$AWS_REGION" | grep -q "\"status\": \"ACTIVE\""; then
        print_success "ECS cluster already exists: $CLUSTER_NAME"
    else
        print_info "Creating ECS cluster..."
        aws ecs create-cluster \
            --cluster-name "$CLUSTER_NAME" \
            --region "$AWS_REGION" \
            --default-capacity-provider-strategy capacityProvider=FARGATE
        print_success "ECS cluster created"
    fi
}

register_task_definition() {
    local image_uri=$1

    print_info "Registering ECS Task Definition..."

    # Create task definition JSON
    cat > /tmp/task-definition.json <<EOF
{
  "family": "$TASK_FAMILY",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "containerDefinitions": [
    {
      "name": "$TASK_FAMILY",
      "image": "$image_uri",
      "portMappings": [
        {
          "containerPort": 8080,
          "hostPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "UI_PORT",
          "value": "8080"
        },
        {
          "name": "REACT_DEV_PORT",
          "value": "5173"
        },
        {
          "name": "LOG_LEVEL",
          "value": "INFO"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/$TASK_FAMILY",
          "awslogs-region": "$AWS_REGION",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8080/api/health || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ],
  "executionRoleArn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/ecsTaskExecutionRole",
  "tags": [
    {
      "key": "Name",
      "value": "aristotlei"
    }
  ]
}
EOF

    # Register task definition
    local task_def_arn=$(aws ecs register-task-definition \
        --cli-input-json file:///tmp/task-definition.json \
        --region "$AWS_REGION" \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text)

    print_success "Task definition registered: $task_def_arn"

    rm /tmp/task-definition.json

    echo "$task_def_arn"
}

create_cloudwatch_log_group() {
    print_info "Creating CloudWatch Log Group..."

    local log_group="/ecs/$TASK_FAMILY"

    if aws logs describe-log-groups \
        --log-group-name-prefix "$log_group" \
        --region "$AWS_REGION" | grep -q "logGroupName"; then
        print_success "Log group already exists: $log_group"
    else
        aws logs create-log-group \
            --log-group-name "$log_group" \
            --region "$AWS_REGION"

        aws logs put-retention-policy \
            --log-group-name "$log_group" \
            --retention-in-days 30 \
            --region "$AWS_REGION"

        print_success "Log group created: $log_group"
    fi
}

create_or_update_ecs_service() {
    local task_def_arn=$1

    print_info "Creating/Updating ECS Service..."

    # Check if service exists
    if aws ecs describe-services \
        --cluster "$CLUSTER_NAME" \
        --services "$SERVICE_NAME" \
        --region "$AWS_REGION" | grep -q "\"serviceName\": \"$SERVICE_NAME\""; then

        print_info "Service exists, updating..."

        aws ecs update-service \
            --cluster "$CLUSTER_NAME" \
            --service "$SERVICE_NAME" \
            --task-definition "$task_def_arn" \
            --region "$AWS_REGION" \
            --force-new-deployment

        print_success "Service updated"
    else
        print_info "Creating new ECS service..."

        aws ecs create-service \
            --cluster "$CLUSTER_NAME" \
            --service-name "$SERVICE_NAME" \
            --task-definition "$task_def_arn" \
            --desired-count 2 \
            --launch-type FARGATE \
            --network-configuration "awsvpcConfiguration={subnets=[subnet-12345678],securityGroups=[sg-12345678],assignPublicIp=ENABLED}" \
            --region "$AWS_REGION"

        print_success "Service created"
    fi
}

get_service_info() {
    print_info "Retrieving service information..."

    print_success "Deployment initiated successfully!"
    echo ""
    echo "Service Details:"
    echo "  Cluster: $CLUSTER_NAME"
    echo "  Service: $SERVICE_NAME"
    echo "  Task Family: $TASK_FAMILY"
    echo "  Region: $AWS_REGION"
    echo ""
    echo "Next steps:"
    echo "1. Monitor service: aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $AWS_REGION"
    echo "2. View logs: aws logs tail /ecs/$TASK_FAMILY --follow --region $AWS_REGION"
    echo "3. Scale service: aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 3 --region $AWS_REGION"
}

main() {
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║     Aristotle-I - AWS ECS Deployment Script                   ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""

    check_prerequisites
    validate_aws_credentials

    local repository_uri
    repository_uri=$(setup_ecr_repository)

    local image_uri
    image_uri=$(build_and_push_image "$repository_uri")

    create_ecs_cluster
    create_cloudwatch_log_group

    local task_def_arn
    task_def_arn=$(register_task_definition "$image_uri")

    create_or_update_ecs_service "$task_def_arn"

    get_service_info
}

# Run main function
main "$@"

