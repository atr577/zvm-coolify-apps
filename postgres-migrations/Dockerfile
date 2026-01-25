FROM python:3.12-slim

WORKDIR /app

# Install PostgreSQL client (optional, for debugging)
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY postgres-migrations/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy migration files
COPY postgres-migrations/run_migrations.py .
COPY postgres-migrations/migrations/ ./migrations/

# Make script executable
RUN chmod +x run_migrations.py

# Run migrations
CMD ["python3", "run_migrations.py"]
