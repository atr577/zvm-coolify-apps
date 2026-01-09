"""
Migration script: Convert existing users/projects to workspace-based structure

Run with: cd backend && venv/bin/python migrate_to_workspaces.py
"""
from datetime import datetime
from sqlalchemy import text
from app.db.base import engine, SessionLocal


def migrate():
    db = SessionLocal()

    try:
        print("Starting migration to workspaces...")

        # 1. Add new columns to users table
        print("\n1. Updating users table...")
        try:
            db.execute(text("ALTER TABLE users ADD COLUMN can_create_workspace BOOLEAN DEFAULT 1"))
            print("   Added can_create_workspace column")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("   can_create_workspace column already exists")
            else:
                print(f"   Note: {e}")

        # 2. Add workspace_id column to projects table
        print("\n2. Updating projects table...")
        try:
            db.execute(text("ALTER TABLE projects ADD COLUMN workspace_id INTEGER"))
            print("   Added workspace_id column")
        except Exception as e:
            if "duplicate column" in str(e).lower():
                print("   workspace_id column already exists")
            else:
                print(f"   Note: {e}")

        # 3. Create workspaces table
        print("\n3. Creating workspaces table...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS workspaces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                owner_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users(id)
            )
        """))
        print("   Created workspaces table")

        # 4. Create workspace_members table
        print("\n4. Creating workspace_members table...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS workspace_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role VARCHAR(50) DEFAULT 'member',
                joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """))
        print("   Created workspace_members table")

        # 5. Create invites table
        print("\n5. Creating invites table...")
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token VARCHAR(64) UNIQUE NOT NULL,
                type VARCHAR(20) NOT NULL DEFAULT 'standalone',
                email VARCHAR(255),
                workspace_id INTEGER,
                created_by_id INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                used_at DATETIME,
                used_by_id INTEGER,
                FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
                FOREIGN KEY (created_by_id) REFERENCES users(id),
                FOREIGN KEY (used_by_id) REFERENCES users(id)
            )
        """))
        print("   Created invites table")

        db.commit()

        # 6. Get all existing users
        print("\n6. Migrating users to workspaces...")
        result = db.execute(text("SELECT id, email, full_name FROM users"))
        users = result.fetchall()
        print(f"   Found {len(users)} users")

        for user_id, email, full_name in users:
            # Check if user already has a workspace
            existing = db.execute(text(
                "SELECT id FROM workspace_members WHERE user_id = :uid"
            ), {"uid": user_id}).fetchone()

            if existing:
                print(f"   User {email} already has workspace membership, skipping...")
                continue

            # Create workspace for user
            workspace_name = f"{full_name or email}'s Workspace"
            db.execute(text("""
                INSERT INTO workspaces (name, owner_id, created_at, updated_at)
                VALUES (:name, :owner_id, datetime('now'), datetime('now'))
            """), {"name": workspace_name, "owner_id": user_id})

            # Get the new workspace id
            ws_result = db.execute(text("SELECT last_insert_rowid()"))
            workspace_id = ws_result.fetchone()[0]

            # Add user as owner
            db.execute(text("""
                INSERT INTO workspace_members (workspace_id, user_id, role, joined_at)
                VALUES (:ws_id, :user_id, 'owner', datetime('now'))
            """), {"ws_id": workspace_id, "user_id": user_id})

            # Update user's projects
            db.execute(text("""
                UPDATE projects
                SET workspace_id = :ws_id
                WHERE user_id = :user_id AND (workspace_id IS NULL OR workspace_id = 0)
            """), {"ws_id": workspace_id, "user_id": user_id})

            print(f"   Created workspace for {email} (workspace_id={workspace_id})")

        # 7. Make georgy@expremiental.com admin
        print("\n7. Setting admin user...")
        db.execute(text("""
            UPDATE users SET role = 'admin'
            WHERE email = 'georgy@expremiental.com'
        """))
        print("   Set georgy@expremiental.com as admin")

        db.commit()
        print("\n✓ Migration completed successfully!")

        # Show summary
        ws_count = db.execute(text("SELECT COUNT(*) FROM workspaces")).fetchone()[0]
        member_count = db.execute(text("SELECT COUNT(*) FROM workspace_members")).fetchone()[0]
        invite_count = db.execute(text("SELECT COUNT(*) FROM invites")).fetchone()[0]

        print(f"\nSummary:")
        print(f"  Workspaces: {ws_count}")
        print(f"  Workspace members: {member_count}")
        print(f"  Invites: {invite_count}")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
