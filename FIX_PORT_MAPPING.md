# Fix: Port Mapping Mismatch

## The Problem
- Coolify's reverse proxy (Traefik/Caddy) is configured to connect to **container port 3000**
- Django is running on **container port 8000**
- Result: Bad Gateway (reverse proxy can't reach Django)

## The Solution

### Option 1: Change Port Mapping (Recommended)
In Coolify → Django app → Configuration → Network:

1. **Port Mappings:** Change from `3000:3000` to `3000:8000`
   - This maps: host port 3000 → container port 8000
   - Reverse proxy connects to 3000, which now reaches Django on 8000

2. **Save** and the app should automatically redeploy

### Option 2: Change Django to Port 3000
If you prefer to keep the mapping as `3000:3000`:

1. Set environment variable: `PORT=3000`
2. Redeploy (Django will now run on port 3000)

### Option 3: Update Traefik Labels (Advanced)
Change the Traefik label to use port 8000, but this is more complex.

## Recommended: Use Option 1
Simply change **Port Mappings** from `3000:3000` to `3000:8000` in the Network settings.
