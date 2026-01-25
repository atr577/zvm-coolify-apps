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

# Expose port (Coolify often uses 3000, but can be configured)
# Using PORT environment variable if set, otherwise default to 8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request, os; port=os.getenv('PORT', '8000'); urllib.request.urlopen(f'http://localhost:{port}/').read()" || exit 1

# Run migrations and start server
# Use PORT env var if set (Coolify may set this), otherwise use 8000
CMD sh -c "PORT=\${PORT:-8000} && \
           echo 'Starting Django application...' && \
           python manage.py migrate --noinput || echo 'Migration failed, continuing...' && \
           echo \"Starting server on 0.0.0.0:\$PORT\" && \
           python manage.py runserver 0.0.0.0:\$PORT"
