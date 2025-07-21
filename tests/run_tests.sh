#!/bin/bash

# ServeML Test Runner Script
# This script runs all test suites and generates reports

set -e

echo "ServeML Test Suite Runner"
echo "========================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TEST_ENV=${TEST_ENV:-"local"}
REPORT_DIR="test_reports"
COVERAGE_DIR="coverage"

# Create directories
mkdir -p $REPORT_DIR
mkdir -p $COVERAGE_DIR

# Function to run a test suite
run_test_suite() {
    local suite_name=$1
    local test_path=$2
    
    echo -e "\n${YELLOW}Running $suite_name...${NC}"
    
    if [ "$TEST_ENV" == "ci" ]; then
        # CI mode - fail fast
        pytest $test_path \
            --verbose \
            --junit-xml=$REPORT_DIR/${suite_name}_results.xml \
            --cov=backend \
            --cov-report=html:$COVERAGE_DIR/${suite_name} \
            --cov-report=term
    else
        # Local mode - continue on failure
        pytest $test_path \
            --verbose \
            --junit-xml=$REPORT_DIR/${suite_name}_results.xml \
            --cov=backend \
            --cov-report=html:$COVERAGE_DIR/${suite_name} \
            --cov-report=term \
            --maxfail=5 || true
    fi
}

# Install test dependencies
echo -e "${YELLOW}Installing test dependencies...${NC}"
pip install -r tests/requirements-test.txt

# Generate test data
echo -e "\n${YELLOW}Generating test data...${NC}"
python tests/create_test_models.py

# Run unit tests
run_test_suite "unit_tests" "tests/unit"

# Run integration tests
run_test_suite "integration_tests" "tests/test_api_integration.py"

# Run security tests
run_test_suite "security_tests" "tests/test_security.py"

# Run AWS integration tests (only if AWS credentials are available)
if [ ! -z "$AWS_ACCESS_KEY_ID" ]; then
    echo -e "\n${YELLOW}Running AWS integration tests...${NC}"
    run_test_suite "aws_s3_tests" "tests/aws/test_s3_integration.py"
    run_test_suite "aws_lambda_tests" "tests/aws/test_lambda_integration.py"
    run_test_suite "aws_dynamodb_tests" "tests/aws/test_dynamodb_integration.py"
else
    echo -e "\n${YELLOW}Skipping AWS tests (no credentials found)${NC}"
fi

# Run load tests (only if explicitly requested)
if [ "$RUN_LOAD_TESTS" == "true" ]; then
    echo -e "\n${YELLOW}Running load tests...${NC}"
    cd tests/load
    locust --headless \
        --users 100 \
        --spawn-rate 10 \
        --run-time 60s \
        --host http://localhost:8000 \
        --html ../../$REPORT_DIR/load_test_report.html
    cd ../..
fi

# Run performance benchmarks (only if explicitly requested)
if [ "$RUN_BENCHMARKS" == "true" ]; then
    echo -e "\n${YELLOW}Running performance benchmarks...${NC}"
    python tests/performance/benchmark.py
fi

# Generate combined coverage report
echo -e "\n${YELLOW}Generating combined coverage report...${NC}"
coverage combine
coverage html -d $COVERAGE_DIR/combined
coverage report

# Summary
echo -e "\n${GREEN}Test Summary${NC}"
echo "============"

# Count test results
total_tests=$(find $REPORT_DIR -name "*.xml" -exec grep -h "tests=" {} \; | grep -oP 'tests="\K\d+' | awk '{s+=$1} END {print s}')
failed_tests=$(find $REPORT_DIR -name "*.xml" -exec grep -h "failures=" {} \; | grep -oP 'failures="\K\d+' | awk '{s+=$1} END {print s}')
error_tests=$(find $REPORT_DIR -name "*.xml" -exec grep -h "errors=" {} \; | grep -oP 'errors="\K\d+' | awk '{s+=$1} END {print s}')

echo "Total tests run: $total_tests"
echo "Failed tests: $failed_tests"
echo "Error tests: $error_tests"

# Coverage summary
echo -e "\n${GREEN}Coverage Summary${NC}"
coverage report --skip-covered | tail -n 1

# Report locations
echo -e "\n${GREEN}Reports Generated${NC}"
echo "================"
echo "Test reports: $REPORT_DIR/"
echo "Coverage reports: $COVERAGE_DIR/"

# Exit code
if [ "$failed_tests" -gt 0 ] || [ "$error_tests" -gt 0 ]; then
    echo -e "\n${RED}❌ Some tests failed!${NC}"
    exit 1
else
    echo -e "\n${GREEN}✅ All tests passed!${NC}"
    exit 0
fi