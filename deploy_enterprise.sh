#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Talk With Me - Enterprise Deployment (Vertex AI) ===${NC}"

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

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Project ID is required.${NC}"
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
    aiplatform.googleapis.com

# IAM Info
echo -e "\n${YELLOW}--- IAM Permissions Info ---${NC}"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "The Cloud Run Service Account is: $SERVICE_ACCOUNT"
echo "Ensure this account has the 'Vertex AI User' role (roles/aiplatform.user)."
echo "You can grant it via console or ask your admin."
echo ""
read -p "Press Enter to continue..."

# Build & Deploy
echo -e "\n${YELLOW}--- Building & Deploying ---${NC}"
IMAGE_NAME="gcr.io/$PROJECT_ID/talk-with-me-enterprise"
SERVICE_NAME="talk-with-me-enterprise"

gcloud builds submit --tag "$IMAGE_NAME" .

gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_NAME" \
    --region "$REGION" \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars "GEMINI_MODEL_NAME=gemini-2.5-flash,USE_VERTEX_AI=true,PROJECT_ID=$PROJECT_ID,LOCATION=$REGION"

echo -e "\n${GREEN}=== Deployment Complete! ===${NC}"
