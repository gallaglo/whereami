# Builder stage - install dependencies and copy source code
FROM python:3.12.1-slim AS builder

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy all source code
COPY app.py ./
COPY chat_service.py ./
COPY gcp_tools.py ./
COPY weather_tools.py ./
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
