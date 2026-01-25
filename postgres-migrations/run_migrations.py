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
DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
DB_PORT = os.getenv('POSTGRES_PORT', '5432')
DB_NAME = os.getenv('POSTGRES_DB', 'postgres')
DB_USER = os.getenv('POSTGRES_USER', 'postgres')
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')

MIGRATIONS_DIR = Path(__file__).parent / 'migrations'
MIGRATIONS_TABLE = 'schema_migrations'


def get_connection():
    """Create database connection."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except psycopg2.Error as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
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
