#!/bin/bash

# ServeML Local Development Setup
# This script sets up a complete local development environment

set -e

echo "================================================"
echo "     ServeML Local Development Setup"
echo "================================================"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not found. Please install Docker Desktop${NC}"
        echo "Visit: https://www.docker.com/products/docker-desktop"
        exit 1
    fi
    
    if ! docker ps &> /dev/null; then
        echo -e "${RED}❌ Docker daemon not running. Please start Docker Desktop${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Docker is running${NC}"
}

# Check Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 not found${NC}"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
}

# Check Node.js
check_node() {
    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ Node.js not found. Please install Node.js 18+${NC}"
        echo "Visit: https://nodejs.org/"
        exit 1
    fi
    
    NODE_VERSION=$(node -v)
    echo -e "${GREEN}✓ Node.js $NODE_VERSION found${NC}"
}

# Create local environment file
create_env_files() {
    echo -e "\n${YELLOW}Creating environment files...${NC}"
    
    # Backend .env
    if [ ! -f backend/.env ]; then
        cat > backend/.env <<EOF
# Local Development Environment
ENV=development
DEBUG=true
LOG_LEVEL=DEBUG

# JWT Settings
SECRET_KEY=local-development-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AWS LocalStack
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
AWS_REGION=us-east-1

# Database
DYNAMODB_ENDPOINT=http://localhost:4566
DYNAMODB_TABLE_PREFIX=serveml-dev-

# S3
S3_BUCKET=serveml-dev-models
S3_ENDPOINT=http://localhost:4566

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
EOF
        echo -e "${GREEN}✓ Created backend/.env${NC}"
    fi
    
    # Frontend .env
    if [ ! -f frontend/.env ]; then
        cat > frontend/.env <<EOF
# Local Development Environment
VITE_API_URL=http://localhost:8000
VITE_AWS_REGION=us-east-1
VITE_S3_BUCKET=serveml-dev-models
VITE_ENVIRONMENT=development
EOF
        echo -e "${GREEN}✓ Created frontend/.env${NC}"
    fi
}

# Start LocalStack
start_localstack() {
    echo -e "\n${YELLOW}Starting LocalStack...${NC}"
    
    # Create docker-compose for local services
    cat > docker-compose.local.yml <<EOF
version: '3.8'

services:
  localstack:
    image: localstack/localstack:latest
    ports:
      - "4566:4566"
      - "4571:4571"
    environment:
      - SERVICES=s3,dynamodb,lambda,ecr,iam,sts,ssm,kms
      - DEBUG=1
      - DATA_DIR=/tmp/localstack/data
      - LAMBDA_EXECUTOR=docker
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
      - "\${TMPDIR:-/tmp}/localstack:/tmp/localstack"
      - "/var/run/docker.sock:/var/run/docker.sock"
    networks:
      - serveml-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - serveml-network

networks:
  serveml-network:
    driver: bridge
EOF
    
    # Start services
    docker-compose -f docker-compose.local.yml up -d
    
    echo -e "${GREEN}✓ LocalStack started${NC}"
    
    # Wait for LocalStack to be ready
    echo -e "${YELLOW}Waiting for LocalStack to be ready...${NC}"
    sleep 10
    
    # Create S3 buckets
    aws --endpoint-url=http://localhost:4566 s3 mb s3://serveml-dev-models || true
    aws --endpoint-url=http://localhost:4566 s3 mb s3://serveml-dev-frontend || true
    
    # Create DynamoDB tables
    aws --endpoint-url=http://localhost:4566 dynamodb create-table \
        --table-name serveml-dev-deployments \
        --attribute-definitions \
            AttributeName=user_id,AttributeType=S \
            AttributeName=deployment_id,AttributeType=S \
        --key-schema \
            AttributeName=user_id,KeyType=HASH \
            AttributeName=deployment_id,KeyType=RANGE \
        --billing-mode PAY_PER_REQUEST || true
    
    aws --endpoint-url=http://localhost:4566 dynamodb create-table \
        --table-name serveml-dev-users \
        --attribute-definitions \
            AttributeName=user_id,AttributeType=S \
            AttributeName=email,AttributeType=S \
        --key-schema \
            AttributeName=user_id,KeyType=HASH \
        --global-secondary-indexes \
            "IndexName=email-index,Keys=[{AttributeName=email,KeyType=HASH}],Projection={ProjectionType=ALL},BillingMode=PAY_PER_REQUEST" \
        --billing-mode PAY_PER_REQUEST || true
    
    echo -e "${GREEN}✓ LocalStack resources created${NC}"
}

# Setup Python environment
setup_python() {
    echo -e "\n${YELLOW}Setting up Python environment...${NC}"
    
    cd backend
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo -e "${GREEN}✓ Created virtual environment${NC}"
    fi
    
    # Activate and install dependencies
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    
    echo -e "${GREEN}✓ Python dependencies installed${NC}"
    
    cd ..
}

# Setup Node environment
setup_node() {
    echo -e "\n${YELLOW}Setting up Node environment...${NC}"
    
    cd frontend
    
    # Install dependencies
    npm install
    
    echo -e "${GREEN}✓ Node dependencies installed${NC}"
    
    cd ..
}

# Create test data
create_test_data() {
    echo -e "\n${YELLOW}Creating test data...${NC}"
    
    cd tests
    source ../backend/venv/bin/activate
    
    # Install test dependencies
    pip install -r requirements-test.txt
    
    # Generate test models
    python create_test_models.py
    
    echo -e "${GREEN}✓ Test data created${NC}"
    
    cd ..
}

# Start services
start_services() {
    echo -e "\n${YELLOW}Starting services...${NC}"
    
    # Create start script
    cat > start_dev.sh <<'EOF'
#!/bin/bash

# Start backend
echo "Starting backend API..."
cd backend
source venv/bin/activate
uvicorn app:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend
echo "Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "

================================================
ServeML Development Environment Running!
================================================

Backend API: http://localhost:8000
Frontend:    http://localhost:5173
LocalStack:  http://localhost:4566

API Docs:    http://localhost:8000/docs
Health:      http://localhost:8000/health

Press Ctrl+C to stop all services
================================================
"

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID; docker-compose -f docker-compose.local.yml down; exit" INT
wait
EOF
    
    chmod +x start_dev.sh
    
    echo -e "${GREEN}✓ Created start_dev.sh script${NC}"
    echo -e "${YELLOW}Run './start_dev.sh' to start all services${NC}"
}

# Run tests
run_tests() {
    echo -e "\n${YELLOW}Running tests to verify setup...${NC}"
    
    cd backend
    source venv/bin/activate
    
    # Run basic tests
    python -m pytest tests/unit/test_models.py -v || true
    
    cd ..
    
    echo -e "${GREEN}✓ Test run complete${NC}"
}

# Create VS Code workspace
create_vscode_config() {
    echo -e "\n${YELLOW}Creating VS Code configuration...${NC}"
    
    mkdir -p .vscode
    
    cat > .vscode/settings.json <<EOF
{
    "python.defaultInterpreterPath": "\${workspaceFolder}/backend/venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    },
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        "**/venv": true,
        "**/node_modules": true
    }
}
EOF
    
    cat > .vscode/launch.json <<EOF
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Backend API",
            "type": "python",
            "request": "launch",
            "module": "uvicorn",
            "args": ["app:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
            "cwd": "\${workspaceFolder}/backend",
            "env": {
                "PYTHONPATH": "\${workspaceFolder}/backend"
            }
        },
        {
            "name": "Frontend Dev",
            "type": "node",
            "request": "launch",
            "runtimeExecutable": "npm",
            "runtimeArgs": ["run", "dev"],
            "cwd": "\${workspaceFolder}/frontend"
        }
    ]
}
EOF
    
    echo -e "${GREEN}✓ VS Code configuration created${NC}"
}

# Summary
print_summary() {
    echo -e "\n${GREEN}================================================${NC}"
    echo -e "${GREEN}     Local Development Setup Complete!${NC}"
    echo -e "${GREEN}================================================${NC}"
    
    echo -e "\n${YELLOW}Quick Start:${NC}"
    echo "1. Run: ./start_dev.sh"
    echo "2. Open: http://localhost:5173"
    echo "3. API Docs: http://localhost:8000/docs"
    
    echo -e "\n${YELLOW}Test Credentials:${NC}"
    echo "Email: test@serveml.local"
    echo "Password: testpass123"
    
    echo -e "\n${YELLOW}Available Commands:${NC}"
    echo "./start_dev.sh                    - Start all services"
    echo "docker-compose -f docker-compose.local.yml logs -f  - View logs"
    echo "cd backend && ./run_tests.sh      - Run backend tests"
    echo "cd frontend && npm test           - Run frontend tests"
    
    echo -e "\n${YELLOW}VS Code:${NC}"
    echo "Open the project in VS Code for the best experience:"
    echo "code ."
    
    echo -e "\n${YELLOW}Next Steps:${NC}"
    echo "1. Create a test user account"
    echo "2. Upload a sample model"
    echo "3. Test the deployment process"
    echo "4. Explore the API documentation"
}

# Main execution
main() {
    check_docker
    check_python
    check_node
    create_env_files
    start_localstack
    setup_python
    setup_node
    create_test_data
    start_services
    run_tests
    create_vscode_config
    print_summary
}

# Run main
main