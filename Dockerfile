FROM python:3.12-slim

WORKDIR /app

# Copy requirements first for better layer caching
COPY server/requirements.txt /app/requirements.txt

# Add pgvector dependency for PostgreSQL vector support
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create directory for history database
RUN mkdir -p /app/history

# Copy server files
COPY server/ .

# Railway dynamically assigns a port, so we'll use whatever is provided in $PORT
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Use CMD with brackets for better signal handling
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
