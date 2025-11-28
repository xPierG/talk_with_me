#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Talk With Me - Personal Deployment (API Key) ===${NC}"

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed.${NC}"
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

# Configuration
if [ -z "$PROJECT_ID" ]; then
    read -p "Enter your GCP Project ID: " PROJECT_ID
fi

if [ -z "$REGION" ]; then
    read -p "Enter GCP Region (default: us-central1): " REGION
    REGION=${REGION:-us-central1}
fi

if [ -z "$SECRET_NAME" ]; then
    read -p "Enter Secret Name for API Key (default: gemini-api-key): " SECRET_NAME
    SECRET_NAME=${SECRET_NAME:-gemini-api-key}
fi

if [ -z "$PROJECT_ID" ] || [ -z "$SECRET_NAME" ]; then
    echo -e "${RED}Error: Project ID and Secret Name are required.${NC}"
    exit 1
fi

# Setup Project
echo -e "\n${YELLOW}--- Setting up Project ---${NC}"
gcloud config set project "$PROJECT_ID"

echo "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com

# Verify Secret
echo -e "\n${YELLOW}--- Verifying Secret ---${NC}"
if ! gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" &>/dev/null; then
    echo -e "${RED}Error: Secret '$SECRET_NAME' not found.${NC}"
    echo "Please create it manually:"
    echo "echo -n \"YOUR_API_KEY\" | gcloud secrets create $SECRET_NAME --data-file=-"
    exit 1
fi

# Grant Access
echo -e "\n${YELLOW}--- Granting Permissions ---${NC}"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

if gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor" \
    --project="$PROJECT_ID" > /dev/null 2>&1; then
    echo -e "${GREEN}Access granted to Service Account.${NC}"
else
    echo -e "${YELLOW}Warning: Could not grant access. Ensure Service Account has access manually.${NC}"
fi

# Build & Deploy
echo -e "\n${YELLOW}--- Building & Deploying ---${NC}"
IMAGE_NAME="gcr.io/$PROJECT_ID/talk-with-me"
SERVICE_NAME="talk-with-me-personal"

gcloud builds submit --tag "$IMAGE_NAME" .

gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_NAME" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars "GEMINI_MODEL_NAME=gemini-2.5-flash,USE_VERTEX_AI=false" \
    --set-secrets "GOOGLE_API_KEY=$SECRET_NAME:latest"

echo -e "\n${GREEN}=== Deployment Complete! ===${NC}"
