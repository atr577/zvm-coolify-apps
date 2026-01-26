"""
Database initialization script for production.

- Fresh DB (no tables): creates all tables from models, stamps alembic to HEAD
- Existing DB (has alembic_version): runs alembic upgrade head as normal
"""
import sys
from sqlalchemy import inspect
from app.db.base import engine, Base
from app.models import *  # noqa: F401,F403 — register all models

def main():
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    if "alembic_version" in tables:
        # Existing DB — run migrations normally
        print("Existing DB detected, running alembic upgrade head...")
        import subprocess
        result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            sys.exit(result.returncode)
    else:
        # Fresh DB — create all tables from models, then stamp
        print("Fresh DB detected, creating tables from models...")
        Base.metadata.create_all(bind=engine)
        print("Tables created. Stamping alembic to HEAD...")
        import subprocess
        result = subprocess.run(["alembic", "stamp", "head"], capture_output=True, text=True)
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
            sys.exit(result.returncode)

    print("Database initialized successfully.")

if __name__ == "__main__":
    main()
