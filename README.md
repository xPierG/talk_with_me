# Cloud Native RAG Demo with Gemini API

A "Chat with your Doc" application built with Streamlit and Google's Gemini API, designed for Cloud Run.

## Features
- **Dual RAG Modes**:
    - **Long Context**: Loads entire document into context (best for single complex documents)
    - **File Search Tool**: Uses semantic search with embeddings (best for multiple documents or large corpora)
- **RAG (Retrieval-Augmented Generation)**: Chat with PDF, TXT, and CSV files.
- **Gemini Native**: Uses Gemini's File API and Context Caching (no external vector store).
- **Cloud Native**: Stateless architecture ready for Google Cloud Run.
- **Thinking Mode**: Visualizes the reasoning process of Gemini models.

## Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd talk_with_me
    ```

2.  **Create and activate virtual environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set Environment Variables**:
    Create a `.env` file or export variables:
    ```bash
    export GOOGLE_API_KEY="your_api_key"
    export GEMINI_MODEL_NAME="gemini-1.5-pro-002"
    ```

## Run Locally

Run with a single command (activates venv and runs app):

```bash
source .venv/bin/activate && streamlit run app.py
```

## Run with Docker

1.  **Build the image**:
    ```bash
    docker build -t my-rag-app .
    ```

2.  **Run the container**:
    ```bash
    docker run -p 8080:8080 \
      -e GOOGLE_API_KEY="your_api_key" \
      -e GEMINI_MODEL_NAME="gemini-1.5-pro-002" \
      my-rag-app
    ```

## Deploy to Cloud Run (Automated)

We provide a `deploy.sh` script to automate the deployment process to any Google Cloud project.

1.  **Run the script**:
    ```bash
    ./deploy.sh
    ```

2.  **Follow the prompts**:
    - Enter your **GCP Project ID**.
    - Enter your **Gemini API Key** (input will be hidden).
    - Select a **Region** (default: `us-central1`).

The script will automatically:
- Enable required APIs (Cloud Run, Cloud Build, Artifact Registry).
- Build the Docker image using Cloud Build.
- Deploy the service to Cloud Run.
- Configure environment variables.

## Deploy to Cloud Run (Manual)

If you prefer to deploy manually:

1.  **Build and Push**:
    ```bash
    gcloud builds submit --tag gcr.io/PROJECT_ID/my-rag-app
    ```

2.  **Deploy**:
    ```bash
    gcloud run deploy my-rag-app \
      --image gcr.io/PROJECT_ID/my-rag-app \
      --platform managed \
      --allow-unauthenticated \
      --set-env-vars "GOOGLE_API_KEY=your_key,GEMINI_MODEL_NAME=gemini-2.5-flash"
    ```
