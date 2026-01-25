FROM python:3.12-slim

WORKDIR /app

# Install PostgreSQL client (optional, for debugging)
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .

# Make script executable
RUN chmod +x app.py

# Expose port
EXPOSE 8001

# Run the application
CMD ["python3", "app.py"]
