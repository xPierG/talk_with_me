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

## Deployment

We provide two automated deployment scripts depending on your environment.

### Option 1: Personal / Demo (API Key)
Use this for personal projects or demos where you can use an API Key.

**Prerequisites:**
1.  Create a Secret in Google Cloud Secret Manager with your API Key:
    ```bash
    echo -n "YOUR_API_KEY" | gcloud secrets create gemini-api-key --data-file=-
    ```

**Deploy:**
```bash
./deploy_personal.sh
```
Follow the prompts to select your Project ID and Region.

### Option 2: Enterprise (Vertex AI + IAM)
Use this for corporate environments where API Keys are restricted. This mode uses **Vertex AI** and **IAM authentication**.

**Prerequisites:**
1.  Ensure the **Cloud Run Service Account** has the `Vertex AI User` role (`roles/aiplatform.user`).
    *   The script will tell you the Service Account email address.
    *   You (or your admin) must grant this role manually via the GCP Console or IAM.

**Deploy:**
```bash
./deploy_enterprise.sh
```
This will enable Vertex AI APIs and deploy the application configured to use IAM for authentication.
