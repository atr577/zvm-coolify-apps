# Finding Dummy App Hostname in Coolify

## The Problem
The hostname `v8808gksc44w80csgss04ok8` cannot be resolved. This is the resource UUID, but not the correct Docker service name.

## Solution: Find the Correct Hostname

### Step 1: Check Dummy App Configuration
1. Go to Coolify dashboard
2. Navigate to your **Dummy App** resource
3. Go to **Configuration** tab
4. Look for connection details or internal URL

### Step 2: Check Network Settings
1. In the Dummy App → Configuration → **Network** section
2. Look for any internal URL or service name
3. Similar to PostgreSQL, there might be an internal URL field

### Step 3: Try the Resource Name
The hostname might be just the UUID part (like we did with PostgreSQL):
- Current: `v8808gksc44w80csgss04ok8` (full resource name)
- Try: Just the UUID part if there's a prefix

### Step 4: Check Container/Service Name
1. In Coolify → Dummy App → **Terminal** tab
2. Run: `hostname` to see the container's hostname
3. Or check the container name in Coolify

### Step 5: Update DUMMY_APP_URL
Once you find the correct hostname, update the environment variable in Django app:
```
DUMMY_APP_URL=http://<correct-hostname>:8001
```

## Quick Test
After updating, test the connection from Django app's terminal:
```bash
curl http://<hostname>:8001/health
```

If this works, the hostname is correct.
