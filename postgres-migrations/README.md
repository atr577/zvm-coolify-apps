# PostgreSQL Migrations

This service manages database migrations for the shared PostgreSQL database.

## Usage

The migration runner automatically:
1. Connects to PostgreSQL using environment variables
2. Creates a `schema_migrations` table to track applied migrations
3. Runs all pending migrations in chronological order

## Environment Variables

- `POSTGRES_HOST` - Database host (default: localhost)
- `POSTGRES_PORT` - Database port (default: 5432)
- `POSTGRES_DB` - Database name (default: postgres)
- `POSTGRES_USER` - Database user (default: postgres)
- `POSTGRES_PASSWORD` - Database password

## Migration Files

Migrations should be named: `YYYYMMDDHHMMSS_description.sql`

Example: `20240101000000_create_django_admin_schema.sql`

Migrations are executed in timestamp order and tracked in the `schema_migrations` table.
