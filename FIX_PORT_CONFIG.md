# Fix: Bad Gateway - Port Configuration

## The Problem
Django is running correctly (logs show it's responding), but Coolify's reverse proxy can't reach it. This is almost always a **port mismatch**.

## Solution: Check Port Configuration in Coolify

### Step 1: Find Port Settings
1. Go to Coolify dashboard
2. Navigate to your Django app → **Configuration** tab
3. Look for **"Port"** or **"Application Port"** setting
4. This is the port Coolify's reverse proxy expects your app to be listening on

### Step 2: Common Port Settings
- **Coolify default:** Often `3000` or `80`
- **Django default:** `8000` (what we're using)

### Step 3: Fix the Mismatch

**Option A: Change Coolify Port Setting**
1. In Coolify → Configuration → Find port setting
2. Change it to `8000` (to match Django)
3. Save and redeploy

**Option B: Change Django Port** (if you can't change Coolify setting)
1. Update Dockerfile to use port 3000 (or whatever Coolify expects)
2. Update CMD to: `python manage.py runserver 0.0.0.0:3000`
3. Update EXPOSE: `EXPOSE 3000`
4. Redeploy

### Step 4: Alternative - Check Network/Advanced Settings
In Coolify → Configuration → **Advanced** or **Network**:
- Look for port mappings
- Check if there's a "Container Port" vs "Host Port" setting
- Ensure they match

## Quick Test
After fixing, the logs should show requests reaching Django successfully.
