FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt /app/backend_requirements.txt
RUN pip install --no-cache-dir -r /app/backend_requirements.txt

# Copy all project code
COPY . /app

# Pre-train ML model artifacts if not present
RUN python -c "from ml.train_model import train_and_save_model; train_and_save_model()" || true

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
