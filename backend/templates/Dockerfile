# Multi-stage build for optimized Lambda container
# Stage 1: Build environment
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    cmake \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir --target /build/python -r requirements.txt

# Stage 2: Lambda runtime
FROM public.ecr.aws/lambda/python:3.11

# Copy installed packages from builder
COPY --from=builder /build/python ${LAMBDA_TASK_ROOT}
COPY --from=builder /build/python /opt/python

# Copy model and handler
COPY model.pkl /opt/ml/model.pkl
COPY handler.py ${LAMBDA_TASK_ROOT}/

# Set environment variables
ENV MODEL_PATH=/opt/ml/model.pkl
ENV PYTHONPATH=${LAMBDA_TASK_ROOT}:${PYTHONPATH}:/opt/python

# Command for Lambda
CMD ["handler.lambda_handler"]