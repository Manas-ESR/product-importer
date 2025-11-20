FROM python:3.12-slim

# System deps for psycopg2 and building wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Environment
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Ensure our start script is executable
RUN chmod +x /app/start.sh

# Run both Celery worker and Uvicorn from the same container
CMD ["/app/start.sh"]
