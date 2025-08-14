# whereami

A containerized application that displays environmental details about its cloud runtime environment and provides an intelligent chat interface powered by Gemini AI. The app can be deployed on Google Cloud Platform services like Cloud Run or Google Kubernetes Engine (GKE).

Key features:

- **Interactive Chat Interface** - Chat with an AI assistant specialized in GCP and cloud infrastructure
- **Agentic Tool Integration** - Real-time access to GCP region data, weather information, and web search
- **Environment Detection** - Displays region, zone and cluster information of the runtime environment
- **Streaming Responses** - Real-time chat responses using server-sent events
- **LangChain Integration** - Powered by Gemini 2.5 Flash with structured output and tool calling
- Production-ready container image used in other projects like [Multi-region Cloud Run Deployment](https://github.com/gallaglo/gcp-demos-notes-and-tricks/tree/main/run/multi-region)

## Chat Features

The application includes an intelligent chat interface that can:

- Answer questions about GCP regions, zones, and cloud services
- Provide real-time weather information for any location (requires OpenWeather API key)
- Search the web for current information about cloud infrastructure
- Give recommendations for cloud deployment strategies
- Explain GCP services and their availability across regions

> This repo is a fork of the GCP [whereami](https://github.com/GoogleCloudPlatform/kubernetes-engine-samples/tree/main/quickstarts/whereami) project. I have extended application functionality to serve a webpage with information about the runtime environment.

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- [Docker](https://docs.docker.com/get-docker/)
- Active Google Cloud Project
- (Optional) [OpenWeather API Key](https://openweathermap.org/api) for weather tool functionality

## Setup Instructions

Deploy the app on either Cloud Run (serverless) or GKE (Kubernetes). Instructions for both platforms are provided below.

### Build and push to Artifact Registry:

```bash
# Set project and region
export PROJECT_ID=<your-project>
export REGION=<your-region>

# Create Artifact Registry repository
gcloud artifacts repositories create whereami-app \
   --repository-format=docker \
   --location=${REGION} \
   --description="Whereami container images"

# Configure Docker auth 
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/whereami-app/whereami:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/whereami-app/whereami:latest
```

### OpenWeather API Key Setup (Optional)

To enable weather functionality in the chat interface, you'll need to configure an OpenWeather API key:

1. **Get an API Key:**
   - Sign up at [OpenWeatherMap](https://openweathermap.org/api)
   - Create a free account and generate an API key
   - Note: Free tier allows 1,000 API calls per day

2. **For Cloud Run Deployment (Recommended - Using Secret Manager):**
   ```bash
   # Enable Secret Manager API
   gcloud services enable secretmanager.googleapis.com --project ${PROJECT_ID}
   
   # Create the secret
   echo "your-openweather-api-key-here" | gcloud secrets create openweather-api-key \
     --data-file=- \
     --project ${PROJECT_ID}
   
   # Grant the service account access to the secret
   gcloud secrets add-iam-policy-binding openweather-api-key \
     --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor" \
     --project ${PROJECT_ID}
   ```

3. **For GKE Deployment:**
   ```bash
   # Create a Kubernetes secret
   kubectl create secret generic openweather-secret \
     --from-literal=api-key=your-openweather-api-key-here \
     -n ${NAMESPACE}
   ```

4. **For Local Development:**
   ```bash
   export OPENWEATHER_API_KEY=your-openweather-api-key-here
   ```

**Note:** If no API key is configured, the weather tools will automatically use mock data and log appropriate warnings. The application will continue to function normally with simulated weather responses.

### Create GCP IAM Service Account

```bash
export SA_NAME=whereami-sa

# Create service account
gcloud iam service-accounts create ${SA_NAME} \
  --display-name="Whereami Service Account"

# Grant AI Platform User role
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# Grant GCE Viewer role
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/compute.viewer"

# Grant Service Usage Viewer role
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/serviceusage.serviceUsageViewer"

# Grant Secret Manager access (if using weather features)
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Deploy to Cloud Run

**Option 1: Using Secret Manager (Recommended for Production)**
```bash
gcloud run deploy whereami \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/whereami-app/whereami:latest \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --service-account ${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-env-vars PROJECT_ID=${PROJECT_ID} \
  --set-secrets OPENWEATHER_API_KEY=openweather-api-key:latest
```

**Option 2: Using Environment Variable (for testing only)**
```bash
gcloud run deploy whereami \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/whereami-app/whereami:latest \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --service-account ${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-env-vars PROJECT_ID=${PROJECT_ID} \
  --set-env-vars OPENWEATHER_API_KEY=${OPENWEATHER_API_KEY}
```

**Option 3: Without Weather Features**
```bash
gcloud run deploy whereami \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/whereami-app/whereami:latest \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --service-account ${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-env-vars PROJECT_ID=${PROJECT_ID}
```

### Deploy to GKE

> GKE cluster must have [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity) enabled for the whereami app to call the Gemini API.

```bash
# Set cluster details
export CLUSTER_NAME=<your-cluster>
export NAMESPACE=<your-namespace>
export PROJECT_ID=<your-project-id>
export REGION=<your-region>
export IMAGE_TAG=latest

# Bind KSA to GCP SA
gcloud iam service-accounts add-iam-policy-binding ${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:${PROJECT_ID}.svc.id.goog[${NAMESPACE}/whereami]"

# Get cluster credentials
gcloud container clusters get-credentials ${CLUSTER_NAME} --region ${REGION} --project ${PROJECT_ID}

# Navigate to /k8s-manifests
cd k8s-manifests

# Apply manifests with kustomize
kustomize build . | envsubst | kubectl apply -f - -n ${NAMESPACE}
```

**Note for GKE:** Update your Kubernetes manifests to include the OpenWeather secret:
```yaml
# Add to your deployment manifest
env:
- name: OPENWEATHER_API_KEY
  valueFrom:
    secretKeyRef:
      name: openweather-secret
      key: api-key
```

## Weather Feature Usage

Once deployed with an OpenWeather API key, you can ask the chat interface questions like:

- "What's the weather like in New York?"
- "Give me a 3-day forecast for London"
- "What's the current temperature in Tokyo?"
- "Is it raining in Seattle right now?"

The application will automatically detect if the weather tools have a valid API key and provide either real weather data or mock data with appropriate notifications.

## Troubleshooting Weather Features

**Common Issues:**

1. **Invalid API Key Error:**
   - Check that your OpenWeather API key is correct
   - Verify the secret is properly configured in Secret Manager or Kubernetes
   - Check service account permissions for Secret Manager access

2. **Mock Data Being Used:**
   - The application logs will indicate if mock data is being used
   - Check that the environment variable `OPENWEATHER_API_KEY` is properly set
   - Verify the API key is not set to placeholder values like "placeholder" or "your-api-key-here"

3. **API Rate Limits:**
   - Free OpenWeather accounts have 1,000 calls/day limit
   - Consider upgrading your plan for production use
   - The application will log rate limit errors if encountered

## Local Development

For local development and testing, you can run the application tests during the Docker build process:

```bash
# Run tests during Docker build
docker build --env GOOGLE_ACCESS_TOKEN=$(gcloud auth print-access-token) --env PROJECT_ID=logan-gallagher --target test -t whereami .

# For local development with weather features
export OPENWEATHER_API_KEY=your-api-key-here
export PROJECT_ID=your-project-id
python app.py
```

This command:

- Sets up authentication using your local gcloud credentials
- Configures the project ID for testing
- Builds only to the test stage to run the test suite
- Creates a test image tagged as `whereami`

## Repository Structure

- [`/examples`](https://github.com/gallaglo/whereami/tree/main/examples) - Example Kustomize overlays and gRPC configurations
- [`/helm-chart`](https://github.com/gallaglo/whereami/tree/main/helm-chart) - Helm chart for deploying the service
- [`/k8s-manifests`](https://github.com/gallaglo/whereami/tree/main/k8s-manifests) - Base Kubernetes manifests
- [`/protos`](https://github.com/gallaglo/whereami/tree/main/protos) - Protocol Buffer definitions
- [`/templates`](https://github.com/gallaglo/whereami/tree/main/templates) - HTML templates for the web interface

## TODO

* Publish image to [GH Packages and Docker Hub](https://docs.github.com/en/actions/use-cases-and-examples/publishing-packages/publishing-docker-images#publishing-images-to-github-packages)
