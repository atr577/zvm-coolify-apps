#!/usr/bin/env python3
"""
Script to create database tables from scratch
"""
import sys
sys.path.insert(0, '.')

from app.db.base import Base, engine
from app.models import (
    User, SocialAccount, Project, Video, WorkflowStep, ValidationResult
)
import hashlib

def hash_password(password: str) -> str:
    """Simple password hashing for testing"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_tables():
    """Drop all tables and recreate them"""
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)

    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)

    print("✅ Database tables created successfully!")

    # Create default user for testing
    from sqlalchemy.orm import Session
    db = Session(engine)

    try:
        # Check if default user exists
        from app.models.user import User
        existing_user = db.query(User).filter(User.email == "demo@example.com").first()

        if not existing_user:
            print("\nCreating default user...")
            default_user = User(
                email="demo@example.com",
                hashed_password=hash_password("demo123"),
                full_name="Demo User",
                is_active=True,
                is_verified=True,
                role="user"
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)

            print(f"✅ Default user created:")
            print(f"   Email: demo@example.com")
            print(f"   Password: demo123")
            print(f"   User ID: {default_user.id}")
        else:
            print(f"\n✅ Default user already exists (ID: {existing_user.id})")

    except Exception as e:
        print(f"❌ Error creating default user: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_tables()
