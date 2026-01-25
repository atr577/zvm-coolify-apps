#!/usr/bin/env python3
"""
PostgreSQL Migration Runner
Runs migrations in order based on filename timestamps.
"""

import os
import sys
import psycopg2
from psycopg2 import sql
from pathlib import Path
import re
from typing import List, Tuple

# Database connection parameters from environment
# Coolify may provide these automatically for database resources
# Check: POSTGRES_HOST, DATABASE_HOST, or resource-specific variables
DB_HOST = (
    os.getenv('POSTGRES_HOST') or 
    os.getenv('DATABASE_HOST') or 
    os.getenv('DB_HOST') or 
    'localhost'
)
DB_PORT = os.getenv('POSTGRES_PORT') or os.getenv('DATABASE_PORT') or os.getenv('DB_PORT') or '5432'
DB_NAME = os.getenv('POSTGRES_DB') or os.getenv('DATABASE_DB') or os.getenv('DB_NAME') or 'postgres'
DB_USER = os.getenv('POSTGRES_USER') or os.getenv('DATABASE_USER') or os.getenv('DB_USER') or 'postgres'
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD') or os.getenv('DATABASE_PASSWORD') or os.getenv('DB_PASSWORD') or ''

MIGRATIONS_DIR = Path(__file__).parent / 'migrations'
MIGRATIONS_TABLE = 'schema_migrations'


def get_connection():
    """Create database connection."""
    try:
        # Print connection details for debugging (without password)
        print(f"Attempting to connect to: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=10
        )
        print("✓ Database connection successful!")
        return conn
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        print(f"✗ Database connection failed: {error_msg}", file=sys.stderr)
        
        # Provide helpful error messages
        if "could not translate host name" in error_msg or "name resolution" in error_msg:
            print("\nTROUBLESHOOTING:", file=sys.stderr)
            print("  The hostname cannot be resolved. This usually means:", file=sys.stderr)
            print("  1. The POSTGRES_HOST value is incorrect", file=sys.stderr)
            print("  2. Services are not on the same Docker network", file=sys.stderr)
            print("  3. The PostgreSQL resource name in Coolify is different", file=sys.stderr)
            print(f"\n  Current POSTGRES_HOST value: {DB_HOST}", file=sys.stderr)
            print("\n  To fix:", file=sys.stderr)
            print("  - Check your PostgreSQL resource name in Coolify dashboard", file=sys.stderr)
            print("  - Use the resource name (not the UUID) as POSTGRES_HOST", file=sys.stderr)
            print("  - Ensure both services are in the same Coolify project", file=sys.stderr)
            print("  - Check PostgreSQL resource connection details page", file=sys.stderr)
        
        sys.exit(1)
    except psycopg2.Error as e:
        print(f"✗ Database error: {e}", file=sys.stderr)
        sys.exit(1)


def init_migrations_table(conn):
    """Create migrations tracking table if it doesn't exist."""
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
                version VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.commit()


def get_applied_migrations(conn) -> set:
    """Get list of already applied migrations."""
    with conn.cursor() as cur:
        cur.execute(f"SELECT version FROM {MIGRATIONS_TABLE} ORDER BY version")
        return {row[0] for row in cur.fetchall()}


def get_migration_files() -> List[Tuple[str, Path]]:
    """Get all migration files sorted by timestamp."""
    if not MIGRATIONS_DIR.exists():
        return []
    
    migrations = []
    pattern = re.compile(r'^(\d{14})_(.+)\.sql$')
    
    for file in sorted(MIGRATIONS_DIR.glob('*.sql')):
        match = pattern.match(file.name)
        if match:
            timestamp, name = match.groups()
            migrations.append((timestamp, file))
    
    return migrations


def run_migration(conn, version: str, filepath: Path):
    """Run a single migration file."""
    print(f"Running migration: {filepath.name}")
    
    with open(filepath, 'r') as f:
        sql_content = f.read()
    
    with conn.cursor() as cur:
        try:
            # Execute migration SQL
            cur.execute(sql_content)
            
            # Record migration
            cur.execute(
                f"INSERT INTO {MIGRATIONS_TABLE} (version) VALUES (%s) ON CONFLICT DO NOTHING",
                (version,)
            )
            
            conn.commit()
            print(f"✓ Migration {filepath.name} applied successfully")
            return True
        except Exception as e:
            conn.rollback()
            print(f"✗ Error applying migration {filepath.name}: {e}", file=sys.stderr)
            return False


def main():
    """Main migration runner."""
    print("Starting database migrations...")
    print(f"Database: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    print(f"Environment check:")
    print(f"  POSTGRES_HOST: {os.getenv('POSTGRES_HOST', 'NOT SET')}")
    print(f"  DATABASE_HOST: {os.getenv('DATABASE_HOST', 'NOT SET')}")
    print(f"  DB_HOST: {os.getenv('DB_HOST', 'NOT SET')}")
    print()
    
    conn = get_connection()
    
    try:
        # Initialize migrations table
        init_migrations_table(conn)
        
        # Get applied migrations
        applied = get_applied_migrations(conn)
        print(f"Found {len(applied)} already applied migrations")
        
        # Get all migration files
        migrations = get_migration_files()
        print(f"Found {len(migrations)} migration files")
        
        # Run pending migrations
        success = True
        for timestamp, filepath in migrations:
            version = f"{timestamp}_{filepath.stem}"
            
            if version in applied:
                print(f"⊘ Skipping {filepath.name} (already applied)")
                continue
            
            if not run_migration(conn, version, filepath):
                success = False
                break
        
        if success:
            print("\n✓ All migrations completed successfully")
            sys.exit(0)
        else:
            print("\n✗ Migration failed", file=sys.stderr)
            sys.exit(1)
            
    finally:
        conn.close()


if __name__ == '__main__':
    main()
