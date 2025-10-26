// MongoDB Initialization Script for Aristotle-I
// This script runs when MongoDB starts for the first time

// Select the aristotlei database
db = db.getSiblingDB('aristotlei');

// Create collections for performance tracking
db.createCollection('performance_matrix');
db.createCollection('agent_perf');
db.createCollection('reviewer_results');

// Create indexes for better query performance
db.performance_matrix.createIndex({ timestamp: 1 });
db.performance_matrix.createIndex({ agent_type: 1, timestamp: -1 });

db.agent_perf.createIndex({ agent_name: 1 });
db.agent_perf.createIndex({ execution_date: 1 });
db.agent_perf.createIndex({ status: 1 });

db.reviewer_results.createIndex({ review_date: 1 });
db.reviewer_results.createIndex({ project_key: 1, review_date: -1 });

// Create feedback database and collections
db = db.getSiblingDB('feedback_db');
db.createCollection('dev_feedback');
db.createCollection('assembler_feedback');

db.dev_feedback.createIndex({ created_at: 1 });
db.dev_feedback.createIndex({ agent_id: 1, created_at: -1 });

db.assembler_feedback.createIndex({ created_at: 1 });
db.assembler_feedback.createIndex({ agent_id: 1, created_at: -1 });

print("✓ MongoDB collections initialized successfully");
version: '3.8'

# Docker Compose for Aristotle-I - Local Development and Testing
# Usage: docker-compose up -d
# Access: http://localhost:8080

services:
  # Main Aristotle-I Application
  aristotlei:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: aristotlei
    ports:
      - "8080:8080"
      - "5173:5173"
    environment:
      # Core Configuration
      MAX_REBUILD_ATTEMPTS: 3
      REVIEW_THRESHOLD: 0.75
      GOT_SCORE_THRESHOLD: 0.70
      HITL_TIMEOUT_SECONDS: 300

      # UI Configuration
      UI_HOST: 0.0.0.0
      UI_PORT: 8080
      REACT_DEV_PORT: 5173
      DEBUG: "false"
      LOG_LEVEL: INFO

      # MongoDB Configuration
      MONGODB_CONNECTION_STRING: mongodb://mongo:27017/aristotlei
      MONGODB_DATABASE: aristotlei
      MONGODB_ENABLED: "true"
      MONGODB_COLLECTION_MATRIX: performance_matrix
      MONGODB_PERFORMANCE_DATABASE: performance_db
      MONGODB_AGENT_PERFORMANCE: agent_perf
      MONGODB_REVIEWER_COLLECTION: reviewer_results
      MONGODB_FEEDBACK_DATABASE: feedback_db
      DEVELOPER_AGENT_FEEDBACK: dev_feedback
      ASSEMBLER_FEEDBACK: assembler_feedback

      # Other Configuration
      REVIEW_BRANCH_NAME: ai-review
      STANDARDS_FOLDER: ./standards

    env_file:
      - .env

    depends_on:
      mongo:
        condition: service_healthy

    volumes:
      - ./logs:/app/logs
      - ./data:/app/data

    restart: unless-stopped

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

    networks:
      - aristotlei-network

    # Limit resources for development
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  # MongoDB Database
  mongo:
    image: mongo:7.0
    container_name: aristotlei-mongodb

    environment:
      MONGO_INITDB_ROOT_USERNAME: root
      MONGO_INITDB_ROOT_PASSWORD: password
      MONGO_INITDB_DATABASE: aristotlei

    ports:
      - "27017:27017"

    volumes:
      - mongodb_data:/data/db
      - mongodb_config:/data/configdb
      - ./scripts/init-mongo.js:/docker-entrypoint-initdb.d/init-mongo.js:ro

    restart: unless-stopped

    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongosh localhost:27017/test --quiet
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 20s

    networks:
      - aristotlei-network

  # MongoDB Express - Web UI for MongoDB (Optional)
  mongo-express:
    image: mongo-express:latest
    container_name: aristotlei-mongo-express

    environment:
      ME_CONFIG_MONGODB_ADMINUSERNAME: root
      ME_CONFIG_MONGODB_ADMINPASSWORD: password
      ME_CONFIG_MONGODB_URL: mongodb://root:password@mongo:27017/
      ME_CONFIG_BASICAUTH_USERNAME: admin
      ME_CONFIG_BASICAUTH_PASSWORD: password

    ports:
      - "8081:8081"

    depends_on:
      - mongo

    restart: unless-stopped

    networks:
      - aristotlei-network

  # Optional: Redis for caching (uncomment if needed)
  # redis:
  #   image: redis:7-alpine
  #   container_name: aristotlei-redis
  #   ports:
  #     - "6379:6379"
  #   volumes:
  #     - redis_data:/data
  #   restart: unless-stopped
  #   networks:
  #     - aristotlei-network

# Volumes for data persistence
volumes:
  mongodb_data:
    driver: local
  mongodb_config:
    driver: local
  # redis_data:
  #   driver: local

# Networks
networks:
  aristotlei-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.28.0.0/16

