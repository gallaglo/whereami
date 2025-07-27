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
- Provide real-time weather information for any location
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
gcloud projects add-iam-policy-binding ${PROJECT_ID}   --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"   --role="roles/compute.viewer"

# Grant Service Usage Viewer role
gcloud projects add-iam-policy-binding ${PROJECT_ID}   --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"   --role="roles/serviceusage.serviceUsageViewer"
```

### Deploy to Cloud Run

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
  --set-env-vars OPENWEATHER_API_KEY=${OPENWEATHER_API_KEY}  # Optional for weather features
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

## Local Development

For local development and testing, you can run the application tests during the Docker build process:

```bash
# Run tests during Docker build
docker build --env GOOGLE_ACCESS_TOKEN=$(gcloud auth print-access-token) --env PROJECT_ID=logan-gallagher --target test -t whereami .
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
