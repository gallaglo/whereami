# Builder stage - install dependencies and copy source code
FROM --platform=linux/amd64 python:3.12.1-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Enable system Python for uv
ENV UV_SYSTEM_PYTHON=1

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN uv pip install --no-cache -r requirements.txt

# Copy all source code
COPY app.py ./
COPY chat_service.py ./
COPY gcp_tools.py ./
COPY whereami_pb2.py ./
COPY whereami_pb2_grpc.py ./
COPY whereami_payload.py ./
COPY templates/ ./templates/
COPY regions.json ./
COPY tests/ ./tests/

# Test stage - run tests on the builder stage
FROM builder AS test
RUN python3 tests/run_tests.py

# Production stage - use builder without test artifacts
FROM builder AS production

EXPOSE 8080
ENTRYPOINT ["python3", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]
