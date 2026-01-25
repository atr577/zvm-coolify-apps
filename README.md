# Coolify Apps - Monorepo

This repository contains all applications for the Coolify installation:

1. **PostgreSQL Migrations** - Database migration management system
2. **Django Web Interface** - Web admin interface with PAM authentication
3. **Dummy Coolify App** - Python microservice that fetches PostgreSQL table structures

## Project Structure

```
coolify-apps/
├── postgres-migrations/    # Database migration service
│   ├── migrations/         # SQL migration files
│   ├── run_migrations.py  # Migration runner script
│   ├── Dockerfile
│   └── requirements.txt
├── django-web/            # Django web interface
│   ├── coolify_admin/     # Django project
│   ├── apps/              # Django apps
│   ├── templates/         # HTML templates
│   ├── manage.py
│   ├── Dockerfile
│   └── requirements.txt
├── dummy-app/             # Dummy Coolify Python app
│   ├── app.py            # Flask application
│   ├── Dockerfile
│   └── requirements.txt
└── README.md
```

## Architecture Overview

### 1. PostgreSQL Migrations Service

A Python service that manages database schema migrations. Migrations are SQL files named with timestamps: `YYYYMMDDHHMMSS_description.sql`

**Environment Variables:**
- `POSTGRES_HOST` - Database host
- `POSTGRES_PORT` - Database port (default: 5432)
- `POSTGRES_DB` - Database name
- `POSTGRES_USER` - Database user
- `POSTGRES_PASSWORD` - Database password

**Usage:**
The service automatically runs all pending migrations in chronological order and tracks them in a `schema_migrations` table.

### 2. Django Web Interface

A Django web application with PAM (Pluggable Authentication Modules) authentication that allows Ubuntu system users to log in.

**Features:**
- PAM-based authentication (uses system users)
- Sample page with button to trigger dummy app
- Displays results from dummy app

**Environment Variables:**
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` - Database connection
- `DJANGO_SECRET_KEY` - Django secret key (required for production)
- `DEBUG` - Debug mode (default: False)
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `DUMMY_APP_URL` - URL of the dummy app (default: http://localhost:8001)

**Port:** 8000

### 3. Dummy Coolify App

A lightweight Flask web service that connects to PostgreSQL and returns table structure information.

**Endpoints:**
- `GET /` - Service information
- `GET /health` - Health check
- `GET /get_tables` - Returns PostgreSQL table structures as plain text

**Environment Variables:**
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` - Database connection
- `PORT` - Server port (default: 8001)
- `HOST` - Server host (default: 0.0.0.0)
- `DEBUG` - Debug mode (default: False)

**Port:** 8001

## Git Setup for Team Collaboration

### Initial Setup

1. **Initialize Git Repository:**
   ```bash
   cd /home/vimundr/coolify-apps
   git init
   git add .
   git commit -m "Initial commit: Coolify apps setup"
   ```

2. **Add Remote Repository:**
   ```bash
   git remote add origin <your-git-repository-url>
   git branch -M main
   git push -u origin main
   ```

### Recommended Git Workflow

#### Option 1: Monorepo (Recommended for this setup)

**Pros:**
- Single repository for all apps
- Easier dependency management
- Atomic commits across services
- Simpler CI/CD setup

**Branch Strategy:**
- `main` - Production-ready code
- `develop` - Integration branch
- `feature/*` - Feature branches
- `hotfix/*` - Hotfix branches

**Example Workflow:**
```bash
# Create feature branch
git checkout -b feature/add-new-migration

# Make changes
# ... edit files ...

# Commit and push
git add .
git commit -m "Add new migration for user tables"
git push origin feature/add-new-migration

# Create pull request in Git UI
# After review, merge to develop/main
```

#### Option 2: Separate Repositories

If you prefer separate repositories for each app:

1. Create three repositories:
   - `coolify-postgres-migrations`
   - `coolify-django-web`
   - `coolify-dummy-app`

2. Move each app to its own repository:
   ```bash
   # For each app
   cd postgres-migrations
   git init
   git remote add origin <repo-url>
   git add .
   git commit -m "Initial commit"
   git push -u origin main
   ```

**Pros:**
- Independent versioning
- Separate access controls
- Smaller repositories

**Cons:**
- More complex dependency management
- Harder to coordinate changes across services

### Coolify Integration with Git

Coolify can automatically deploy from Git repositories:

1. **In Coolify UI:**
   - Create a new application
   - Select "Git Repository" as source
   - Connect your Git account
   - Select the repository and branch
   - Configure build settings (Dockerfile path, etc.)

2. **Auto-deployment:**
   - Coolify can watch for commits to specific branches
   - Automatically rebuild and redeploy on push
   - Configure webhooks for real-time updates

3. **Environment Variables:**
   - Set environment variables in Coolify UI for each service
   - These override defaults in Dockerfiles

### Best Practices

1. **Environment Variables:**
   - Never commit `.env` files
   - Document required environment variables in README
   - Use Coolify's environment variable management

2. **Database Migrations:**
   - Always test migrations locally first
   - Use descriptive migration names
   - Never modify existing migrations (create new ones)

3. **Docker Images:**
   - Tag images with version numbers
   - Use semantic versioning (v1.0.0, v1.1.0, etc.)
   - Keep Dockerfiles optimized (multi-stage builds if needed)

4. **Code Reviews:**
   - Require pull requests for main/develop branches
   - Review database migrations carefully
   - Test changes in development environment first

## Deployment in Coolify

### 1. PostgreSQL Migrations Service

1. Create new application in Coolify
2. Connect to Git repository (or use local files)
3. Set build context to `postgres-migrations/`
4. Configure environment variables for database connection
5. Set as one-time job or scheduled task

### 2. Django Web Interface

1. Create new application in Coolify
2. Connect to Git repository
3. Set build context to `django-web/`
4. Configure environment variables:
   - Database connection
   - `DJANGO_SECRET_KEY` (generate with: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`)
   - `DUMMY_APP_URL` (e.g., `http://dummy-app:8001` if using service names)
5. Expose port 8000
6. Set up reverse proxy/domain

### 3. Dummy Coolify App

1. Create new application in Coolify
2. Connect to Git repository
3. Set build context to `dummy-app/`
4. Configure environment variables for database connection
5. Expose port 8001
6. Ensure Django app can reach it (use service name or external URL)

## Local Development

### Prerequisites

- Python 3.12+
- Docker and Docker Compose (optional)
- PostgreSQL (or use Docker)

### Running Locally

1. **Start PostgreSQL:**
   ```bash
   docker run -d \
     --name postgres \
     -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=postgres \
     -p 5432:5432 \
     postgres:15
   ```

2. **Run Migrations:**
   ```bash
   cd postgres-migrations
   pip install -r requirements.txt
   export POSTGRES_PASSWORD=postgres
   python run_migrations.py
   ```

3. **Run Dummy App:**
   ```bash
   cd dummy-app
   pip install -r requirements.txt
   export POSTGRES_PASSWORD=postgres
   python app.py
   ```

4. **Run Django App:**
   ```bash
   cd django-web
   pip install -r requirements.txt
   export POSTGRES_PASSWORD=postgres
   export DUMMY_APP_URL=http://localhost:8001
   export DJANGO_SECRET_KEY=your-secret-key-here
   python manage.py migrate
   python manage.py runserver
   ```

## Troubleshooting

### PAM Authentication Issues

If PAM authentication doesn't work:
- Ensure `libpam0g-dev` is installed in the Docker container
- Verify system users exist on the host
- Check PAM configuration

### Database Connection Issues

- Verify environment variables are set correctly
- Check network connectivity between services
- Ensure PostgreSQL is accessible from containers

### Service Communication

- Use service names in Coolify (e.g., `dummy-app:8001`)
- Or use external URLs if services are exposed
- Check firewall rules and network policies

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
