FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpam0g-dev \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY django-web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY django-web/ .

# Collect static files (skip if settings not configured)
RUN python manage.py collectstatic --noinput || echo "Skipping collectstatic"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/').read()" || exit 1

# Run migrations and start server
CMD sh -c "echo 'Starting Django application...' && \
           python manage.py migrate --noinput || echo 'Migration failed, continuing...' && \
           echo 'Starting server on 0.0.0.0:8000' && \
           python manage.py runserver 0.0.0.0:8000"
