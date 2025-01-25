# whereami

A containerized application that displays environmental details about its cloud runtime environment. The app can be deployed on Google Cloud Platform services like Cloud Run or Google Kubernetes Engine (GKE).

Key features:
- Displays region, zone and cluster information 
- Integrates with Gemini API to provide interesting facts about the cloud region's location
- Production-ready container image used in other projects like [Multi-region Cloud Run Deployment](https://github.com/gallaglo/gcp-demos-notes-and-tricks/tree/main/run/multi-region)

> This repo is a fork of the GCP [whereami](https://github.com/GoogleCloudPlatform/kubernetes-engine-samples/tree/main/quickstarts/whereami) project. I have extended application functionality to serve a webpage with information about the runtime environment.

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- [Docker](https://docs.docker.com/get-docker/)
- Active Google Cloud Project

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
  --set-env-vars PROJECT_ID=${PROJECT_ID}
  ```

### Deploy to GKE

> GKE cluster must have [Workload Identity](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity) enabled for the whereami app to call the Gemini API.

```bash
# Set cluster details
export CLUSTER_NAME=<your-cluster>
export NAMESPACE=<your-namespace>

# Bind KSA to GCP SA
gcloud iam service-accounts add-iam-policy-binding ${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:${PROJECT_ID}.svc.id.goog[${NAMESPACE}/whereami]"

# Get cluster credentials
gcloud container clusters get-credentials ${CLUSTER_NAME} --region ${REGION} --project ${PROJECT_ID}

# Apply manifests with kustomize
kustomize build . | PROJECT_ID=${PROJECT_ID} envsubst | kubectl apply -f - -n ${NAMESPACE}
```

## Repository Structure

- [`/examples`](https://github.com/gallaglo/whereami/tree/main/examples) - Example Kustomize overlays and gRPC configurations
- [`/helm-chart`](https://github.com/gallaglo/whereami/tree/main/helm-chart) - Helm chart for deploying the service
- [`/k8s-manifests`](https://github.com/gallaglo/whereami/tree/main/k8s-manifests) - Base Kubernetes manifests

- [`/protos`](https://github.com/gallaglo/whereami/tree/main/protos) - Protocol Buffer definitions
- [`/templates`](https://github.com/gallaglo/whereami/tree/main/templates) - HTML templates for the web interface

## TODO

* Publish image to [GH Packages and Docker Hub](https://docs.github.com/en/actions/use-cases-and-examples/publishing-packages/publishing-docker-images#publishing-images-to-github-packages)