#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Talk With Me - GCP Deployment Script ===${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed.${NC}"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check current user
CURRENT_USER=$(gcloud config get-value account 2>/dev/null)
if [ -z "$CURRENT_USER" ]; then
    echo -e "${YELLOW}No active gcloud account found.${NC}"
    echo "Please log in..."
    gcloud auth login
else
    echo -e "Current gcloud user: ${GREEN}$CURRENT_USER${NC}"
    read -p "Do you want to continue with this account? (Y/n): " CONFIRM_USER
    CONFIRM_USER=${CONFIRM_USER:-Y}
    if [[ "$CONFIRM_USER" =~ ^[Nn]$ ]]; then
        echo "Logging in with a new account..."
        gcloud auth login
    fi
fi

# 1. Configuration
echo -e "\n${YELLOW}--- Configuration ---${NC}"

# Project ID
if [ -z "$PROJECT_ID" ]; then
    read -p "Enter your GCP Project ID: " PROJECT_ID
fi

# Region
if [ -z "$REGION" ]; then
    read -p "Enter GCP Region (default: us-central1): " REGION
    REGION=${REGION:-us-central1}
fi

# Gemini API Key
if [ -z "$GEMINI_API_KEY" ]; then
    echo -n "Enter your Gemini API Key (input will be hidden): "
    read -s GEMINI_API_KEY
    echo ""
fi

if [ -z "$PROJECT_ID" ] || [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}Error: Project ID and Gemini API Key are required.${NC}"
    exit 1
fi

# 2. Setup Project
echo -e "\n${YELLOW}--- Setting up Project ---${NC}"
echo "Setting active project to $PROJECT_ID..."
gcloud config set project "$PROJECT_ID"

echo "Enabling required APIs (this may take a moment)..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com

# 3. Setup Secrets
echo -e "\n${YELLOW}--- Setting up Secrets ---${NC}"
SECRET_NAME="gemini-api-key"

# Check if secret exists, create if not
if ! gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo "Creating secret $SECRET_NAME..."
    gcloud secrets create "$SECRET_NAME" --replication-policy="automatic" --project="$PROJECT_ID"
fi

# Add new version
echo "Adding new version to secret $SECRET_NAME..."
echo -n "$GEMINI_API_KEY" | gcloud secrets versions add "$SECRET_NAME" --data-file=- --project="$PROJECT_ID"

# Grant access to Cloud Run Service Account
echo "Granting access to Cloud Run default service account..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Service Account: $SERVICE_ACCOUNT"
gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID" > /dev/null

# 4. Build Container
echo -e "\n${YELLOW}--- Building Container ---${NC}"
IMAGE_NAME="gcr.io/$PROJECT_ID/talk-with-me"
echo "Building image: $IMAGE_NAME"
gcloud builds submit --tag "$IMAGE_NAME" .

# 5. Deploy to Cloud Run
echo -e "\n${YELLOW}--- Deploying to Cloud Run ---${NC}"
SERVICE_NAME="talk-with-me"

gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_NAME" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars "GEMINI_MODEL_NAME=gemini-2.5-flash" \
    --set-secrets "GEMINI_API_KEY=$SECRET_NAME:latest"

echo -e "\n${GREEN}=== Deployment Complete! ===${NC}"
echo "Your app is live. Check the URL above."
