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

# Default command: run the web app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
