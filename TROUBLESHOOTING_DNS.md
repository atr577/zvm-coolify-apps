# Troubleshooting: "could not translate host name" Error

## Error Message
```
Error connecting to database: could not translate host name "postgresql-database-nogsoc8wwg40cckc8ckow808" to address: Temporary failure in name resolution
```

## Problem
The hostname you're using cannot be resolved by DNS. This happens when:
1. The hostname doesn't match the actual PostgreSQL service name
2. Services are not on the same Docker network
3. You're using a UUID instead of the resource name

## Solution Steps

### Step 1: Find the Correct Resource Name

In Coolify, the PostgreSQL resource has a **user-friendly name**, not the UUID. To find it:

1. **Go to Coolify Dashboard**
2. **Navigate to your PostgreSQL resource**
3. **Look at the resource name** - it's usually something like:
   - `postgres`
   - `pg-db`
   - `database`
   - `postgresql`

**NOT** the UUID like `nogsoc8wwg40cckc8ckow808`

### Step 2: Check Connection Details

1. **Open your PostgreSQL resource page in Coolify**
2. **Look for "Connection Details" or "Environment Variables" section**
3. **Check if Coolify shows connection information there**
4. Some Coolify versions show the internal hostname in this section

### Step 3: Verify Network Connectivity

Both services must be in the **same Coolify project** to communicate:

1. Check that your migrations app is in the same project as PostgreSQL
2. Verify both are running (status should be "Running")
3. If they're in different projects, they won't be able to communicate

### Step 4: Update Environment Variables

In your **Migrations App** settings in Coolify:

1. Go to **Environment Variables**
2. Set `POSTGRES_HOST` to the **resource name** (not UUID)
   - Example: `postgres` or `pg-db`
   - **NOT**: `postgresql-database-nogsoc8wwg40cckc8ckow808`
3. Set other required variables:
   ```
   POSTGRES_HOST=<resource-name>  # e.g., "postgres"
   POSTGRES_PORT=5432
   POSTGRES_DB=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=<your-password>
   ```

### Step 5: Alternative - Check Coolify's Auto-Injected Variables

Coolify may automatically inject database connection variables. Check if these exist:

- `DATABASE_HOST`
- `DB_HOST`
- Resource-specific variables (check PostgreSQL resource page)

The updated migration script now checks for these automatically.

## Common Mistakes

❌ **Wrong**: Using the full UUID-like name
```
POSTGRES_HOST=postgresql-database-nogsoc8wwg40cckc8ckow808
```

✅ **Correct**: Using the resource name
```
POSTGRES_HOST=postgres
```

❌ **Wrong**: Using localhost
```
POSTGRES_HOST=localhost
```

✅ **Correct**: Using the resource name
```
POSTGRES_HOST=postgres
```

## How to Find Resource Name

### Method 1: Dashboard
- Look at the resource list in your project
- The name is usually displayed prominently

### Method 2: Resource URL
- Check the URL when viewing the PostgreSQL resource
- Often contains the name: `/resources/postgres/...` or `/resources/pg-db/...`

### Method 3: Container/Service Name
- In some Coolify versions, check the container details
- Look for "Service Name" or "Container Name"

## Testing the Connection

After updating the environment variables:

1. **Redeploy the migrations app**
2. **Check the logs** - you should see:
   ```
   Starting database migrations...
   Database: postgres@postgres:5432/postgres
   ✓ Database connection successful!
   ```
3. If it still fails, the resource name is likely still wrong

## Still Not Working?

If you've tried all the above:

1. **Check PostgreSQL resource logs** - ensure it's running correctly
2. **Verify both services are in the same project**
3. **Try using the internal IP** (if Coolify provides it in connection details)
4. **Check Coolify documentation** for your specific version
5. **Contact Coolify support** or check their Discord/community

## Quick Reference

- **Resource Name**: Short, user-friendly name (e.g., `postgres`)
- **UUID**: Long identifier (e.g., `nogsoc8wwg40cckc8ckow808`) - **Don't use this!**
- **Hostname**: Use the resource name, not the UUID
- **Network**: Services must be in the same Coolify project
