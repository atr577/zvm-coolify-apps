# Finding PostgreSQL Host in Coolify

## Quick Steps

1. **Open Coolify Dashboard**
   - Navigate to your project
   - Find your PostgreSQL resource/database

2. **Find the Resource Name**
   - Look at the PostgreSQL resource name (shown in the resource list or details page)
   - Common names: `postgres`, `pg-db`, `database`, `postgresql`
   - **This name is your hostname!**

3. **Use Resource Name as Hostname**
   - In Coolify's Docker network, services communicate using resource names
   - Set `POSTGRES_HOST` to the exact resource name

## Example Configuration

If your PostgreSQL resource is named `postgres`:

```env
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here
```

If your PostgreSQL resource is named `pg-db`:

```env
POSTGRES_HOST=pg-db
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here
```

## Where to Set Environment Variables

1. Go to your **Migrations App** in Coolify
2. Click on **Environment Variables** or **Settings**
3. Add the variables listed above
4. Save and redeploy

## Troubleshooting

### Can't find the resource name?
- Check the PostgreSQL resource details page
- Look for "Service Name" or "Container Name"
- Check the resource URL - it often contains the name

### Connection still failing?
- Verify the PostgreSQL resource is running (status should be "Running")
- Check that both apps are in the same Coolify project/network
- Ensure the resource name matches exactly (case-sensitive)
- Verify the password is correct

### Testing the connection
You can test if the hostname works by:
1. Deploying the migrations app with the environment variables
2. Checking the logs for connection errors
3. If you see "could not resolve hostname", the resource name is wrong

## Important Notes

- **Don't use** `localhost` or `127.0.0.1` - these won't work in Docker networking
- **Don't use** external IPs or domains - use the resource name
- The port is usually `5432` (PostgreSQL default)
- All services in the same Coolify project can communicate using resource names
