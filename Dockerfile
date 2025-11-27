FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Cloud Run sets PORT env var, default 8080)
ENV PORT=8080
EXPOSE 8080

# Run Streamlit
CMD streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0
