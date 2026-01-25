# Quick Start Guide

## Project Overview

This repository contains three applications for your Coolify installation:

1. **PostgreSQL Migrations** - Manages database schema changes
2. **Django Web Interface** - Admin interface with PAM authentication
3. **Dummy Coolify App** - Microservice that fetches PostgreSQL table structures

## Initial Git Setup

### 1. Initialize Git Repository

```bash
cd /home/vimundr/coolify-apps
git init
git add .
git commit -m "Initial commit: Coolify apps setup"
```

### 2. Add Your Git Remote

```bash
# Replace with your actual Git repository URL
git remote add origin https://github.com/yourusername/coolify-apps.git
# or
git remote add origin git@github.com:yourusername/coolify-apps.git

git branch -M main
git push -u origin main
```

### 3. Configure Git Credentials (if needed)

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

For private repositories, you'll need to set up authentication:
- **HTTPS**: Use personal access token or GitHub CLI
- **SSH**: Set up SSH keys and add to your Git provider

## Coolify Deployment Steps

### Step 1: Deploy PostgreSQL (if not already deployed)

In Coolify, create a PostgreSQL service or use an existing one. Note the connection details.

### Step 2: Deploy Migrations Service

1. In Coolify, create a new application
2. **Source**: Connect to your Git repository
   - Repository: `yourusername/coolify-apps`
   - Branch: `main`
   - Build Pack: Docker
   - Dockerfile Path: `postgres-migrations/Dockerfile`
3. **Environment Variables**:
   - Find your PostgreSQL resource name in Coolify (e.g., `postgres`, `pg-db`)
   - Use that name as the hostname:
   ```
   POSTGRES_HOST=<postgres-resource-name>  # e.g., "postgres" or "pg-db"
   POSTGRES_PORT=5432
   POSTGRES_DB=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=<your-password>
   ```
   **Note:** In Coolify, services communicate via Docker network using resource names as hostnames.
4. **Deployment**: Set as one-time job or scheduled task
5. Deploy and verify migrations ran successfully

### Step 3: Deploy Dummy App

1. Create new application in Coolify
2. **Source**: Same Git repository
   - Dockerfile Path: `dummy-app/Dockerfile`
3. **Environment Variables**:
   ```
   POSTGRES_HOST=<postgres-resource-name>  # Same as migrations app
   POSTGRES_PORT=5432
   POSTGRES_DB=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=<your-password>
   PORT=8001
   ```
4. **Ports**: Expose port 8001
5. **Service Name**: Note the service name (e.g., `dummy-app`) for Django to connect
6. Deploy

### Step 4: Deploy Django Web Interface

1. Create new application in Coolify
2. **Source**: Same Git repository
   - Dockerfile Path: `django-web/Dockerfile`
3. **Environment Variables**:
   ```
   POSTGRES_HOST=<postgres-resource-name>  # Same as migrations app
   POSTGRES_PORT=5432
   POSTGRES_DB=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=<your-password>
   DUMMY_APP_URL=http://<dummy-app-resource-name>:8001  # Use dummy app's resource name
   DJANGO_SECRET_KEY=<generate-with-command-below>
   DEBUG=False
   ALLOWED_HOSTS=your-domain.com,localhost
   ```
4. **Generate Django Secret Key**:
   ```bash
   python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
   ```
5. **Ports**: Expose port 8000
6. **Domain**: Configure your domain/subdomain
7. Deploy

## Testing the Setup

1. **Check Migrations**: Verify `django_admin` schema and `telegram_channels` table exist
2. **Test Dummy App**: Visit `http://your-dummy-app-url:8001/health`
3. **Test Django**: Visit your Django domain and log in with a system user

## Workflow for Team Collaboration

### Making Changes

1. **Create Feature Branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**:
   - Edit files in the appropriate app directory
   - Test locally if possible

3. **Commit and Push**:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push origin feature/your-feature-name
   ```

4. **Create Pull Request**:
   - Use your Git provider's UI to create a PR
   - Request review from team members
   - After approval, merge to `main`

5. **Auto-Deploy** (if configured):
   - Coolify will detect the push to `main`
   - Automatically rebuild and redeploy affected services

### Adding New Migrations

1. Create new migration file:
   ```bash
   cd postgres-migrations/migrations
   # Format: YYYYMMDDHHMMSS_description.sql
   touch 20240115120000_add_new_table.sql
   ```

2. Write SQL in the file

3. Commit and push:
   ```bash
   git add postgres-migrations/migrations/20240115120000_add_new_table.sql
   git commit -m "Add migration for new table"
   git push
   ```

4. Re-run migrations service in Coolify

## Troubleshooting

### Git Authentication Issues

**HTTPS:**
- Use personal access token instead of password
- Store credentials: `git config --global credential.helper store`

**SSH:**
- Generate key: `ssh-keygen -t ed25519 -C "your.email@example.com"`
- Add to Git provider (GitHub/GitLab/etc.)
- Test: `ssh -T git@github.com`

### Coolify Not Detecting Changes

- Check webhook configuration in Coolify
- Manually trigger rebuild in Coolify UI
- Verify branch name matches Coolify configuration

### Service Communication Issues

- Use service names (e.g., `dummy-app:8001`) within Coolify network
- Use external URLs if services are on different networks
- Check environment variables are set correctly

## Next Steps

1. Set up your Git repository and push initial code
2. Configure Coolify applications with proper environment variables
3. Test the full workflow end-to-end
4. Set up CI/CD pipelines if needed
5. Configure monitoring and logging
6. Set up backup strategies for database

## Support

For issues or questions:
- Check the main README.md for detailed documentation
- Review Coolify documentation for deployment specifics
- Check application logs in Coolify dashboard
