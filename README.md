# whereami

> This repo is a fork of the GCP [whereami](https://github.com/GoogleCloudPlatform/kubernetes-engine-samples/tree/main/quickstarts/whereami) project. I have extended application functionality to serve a webpage with information about the runtime environment, regardless of the underlying infrastructure (such as GKE or Cloud Run).

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- [Docker](https://docs.docker.com/get-docker/)
- Active Google Cloud Project

## Setup Instructions

Build and push to Artifact Registry:

```bash
# Set project and region
export PROJECT_ID=<your-project>
export REGION=<your-region>

# Configure Docker auth
gcloud auth configure-docker ${REGION}-docker.pkg.dev

# Build and push
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/whereami-app/whereami:latest .
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/whereami-app/whereami:latest
```

Deploy to Cloud Run:
```bash
export SA_NAME=whereami-sa

# Create service account
gcloud iam service-accounts create ${SA_NAME} \
  --display-name="Whereami Service Account"

# Grant AI Platform User role
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud run deploy whereami \
  --image ${REGION}-docker.pkg.dev/${PROJECT_ID}/whereami-app/whereami:latest \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --service-account ${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
  --allow-unauthenticated
  ```

## Repository Structure

- [`/examples`](https://github.com/gallaglo/whereami/tree/main/examples) - Example Kustomize overlays and gRPC configurations
- [`/helm-chart`](https://github.com/gallaglo/whereami/tree/main/helm-chart) - Helm chart for deploying the service
- [`/k8s-manifests`](https://github.com/gallaglo/whereami/tree/main/k8s-manifests) - Base Kubernetes manifests
 - Raw deployment, service, configmap, and KSA definitions
- [`/protos`](https://github.com/gallaglo/whereami/tree/main/protos) - Protocol Buffer definitions
- [`/templates`](https://github.com/gallaglo/whereami/tree/main/templates) - HTML templates for the web interface

## TODO

* Publish image to [GH Packages and Docker Hub](https://docs.github.com/en/actions/use-cases-and-examples/publishing-packages/publishing-docker-images#publishing-images-to-github-packages)