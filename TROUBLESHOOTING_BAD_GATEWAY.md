# Troubleshooting: Bad Gateway Error

## Problem
Getting "502 Bad Gateway" error when accessing Django application at `http://admin.31.97.32.102.sslip.io/`

## Common Causes

### 1. Application Not Running
The Django app might have crashed on startup.

**Check:**
- Go to Coolify dashboard → Your Django app → **Logs** tab
- Look for error messages, especially:
  - Database connection errors
  - Import errors
  - Configuration errors
  - Port binding errors

**Solution:**
- Fix any errors shown in logs
- Ensure all environment variables are set correctly
- Verify database connection settings

### 2. Port Mismatch
Coolify might be trying to connect to the wrong port.

**Check:**
- In Coolify → Your Django app → **Configuration** → **General**
- Look for port settings
- Verify the app is listening on the port Coolify expects

**Solution:**
- Ensure Django is running on port 8000 (as configured in Dockerfile)
- Check if Coolify has a port setting that needs to match
- The Dockerfile exposes port 8000, and Django runs on `0.0.0.0:8000`

### 3. Database Connection Issues
If the app can't connect to the database, it might fail to start.

**Check:**
- Environment variables for database connection:
  - `POSTGRES_HOST`
  - `POSTGRES_PORT`
  - `POSTGRES_DB`
  - `POSTGRES_USER`
  - `POSTGRES_PASSWORD`
- Or `DATABASE_URL` if using URL format

**Solution:**
- Verify database connection variables are set correctly
- Test database connectivity from the container (use Terminal tab in Coolify)
- Ensure PostgreSQL resource is running

### 4. Application Crashes on Startup
Various issues can cause the app to crash immediately.

**Common causes:**
- Missing environment variables
- Invalid configuration
- Import errors
- PAM authentication issues (if in Docker)

**Check logs for:**
```
Traceback (most recent call last):
...
```

**Solution:**
- Review full error traceback in logs
- Fix the specific error mentioned
- For PAM issues: The app will fall back gracefully, but check logs

### 5. Health Check Failing
If health checks are configured, they might be failing.

**Check:**
- Look for health check errors in logs
- Verify the health check endpoint is accessible

## Step-by-Step Debugging

### Step 1: Check Application Logs
1. Go to Coolify dashboard
2. Navigate to your Django app
3. Click **Logs** tab
4. Look for:
   - Startup messages
   - Error messages
   - Database connection attempts
   - Port binding messages

### Step 2: Check Application Status
1. In Coolify dashboard, check the status indicator
2. Should show "Running" (green)
3. If showing "Stopped" or "Failed", check logs

### Step 3: Verify Port Configuration
1. In Coolify → Configuration → General
2. Check if there's a port setting
3. Should match port 8000 (or whatever Django is using)
4. Check Dockerfile: `EXPOSE 8000` and `runserver 0.0.0.0:8000`

### Step 4: Test Database Connection
1. Go to **Terminal** tab in Coolify
2. Try connecting to database:
   ```bash
   psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB
   ```
3. Or check environment variables:
   ```bash
   env | grep POSTGRES
   ```

### Step 5: Test Application Locally in Container
1. Use **Terminal** tab in Coolify
2. Try starting Django manually:
   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```
3. This will show any startup errors

### Step 6: Check Environment Variables
1. Go to **Configuration** → **Environment Variables**
2. Verify all required variables are set:
   - Database connection variables
   - `DJANGO_SECRET_KEY`
   - `ALLOWED_HOSTS` (should include your domain)
   - `DUMMY_APP_URL` (if using dummy app)

## Quick Fixes

### Fix 1: Restart the Application
1. In Coolify dashboard
2. Click **Restart** button
3. Wait for restart to complete
4. Check logs for any errors

### Fix 2: Check ALLOWED_HOSTS
Ensure your domain is in ALLOWED_HOSTS:
```
ALLOWED_HOSTS=admin.31.97.32.102.sslip.io,31.97.32.102.sslip.io,localhost,*
```

### Fix 3: Verify Database Connection
If using individual variables:
```
POSTGRES_HOST=nogsoc8wwg40cckc8ckow808
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<your-password>
```

Or use DATABASE_URL:
```
DATABASE_URL=postgres://postgres:password@nogsoc8wwg40cckc8ckow808:5432/postgres
```

### Fix 4: Check Static Files
If collectstatic failed, it might cause issues. Check if static files directory exists.

## Expected Log Output

When Django starts successfully, you should see:
```
Starting Django application...
Operations to perform:
  Apply all migrations: ...
Running migrations:
  ...
Starting server on 0.0.0.0:8000
Watching for file changes with StatReloader
Performing system checks...
System check identified no issues (0 silenced).
Django version X.X.X, using settings 'coolify_admin.settings'
Starting development server at http://0.0.0.0:8000/
Quit the server with CONTROL-C.
```

If you see errors before this, those are the issues to fix.

## Still Not Working?

1. **Check Coolify's reverse proxy logs** - might show connection errors
2. **Verify network connectivity** - ensure containers can communicate
3. **Check resource limits** - app might be getting killed due to memory/CPU limits
4. **Review Coolify documentation** - for your specific version

## Common Error Messages and Solutions

### "OperationalError: could not connect to server"
- **Cause:** Database connection failed
- **Solution:** Check POSTGRES_HOST, POSTGRES_PORT, POSTGRES_PASSWORD

### "django.core.exceptions.ImproperlyConfigured: Set the ALLOWED_HOSTS setting"
- **Cause:** Domain not in ALLOWED_HOSTS
- **Solution:** Add domain to ALLOWED_HOSTS environment variable

### "ModuleNotFoundError: No module named 'X'"
- **Cause:** Missing Python package
- **Solution:** Check requirements.txt and rebuild

### "Address already in use"
- **Cause:** Port 8000 already taken
- **Solution:** Check if another process is using the port, or change port
