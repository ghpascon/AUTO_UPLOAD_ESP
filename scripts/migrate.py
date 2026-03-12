#!/usr/bin/env python3
"""
Simple migration script for SmartX Connector.
poetry run python migrate.py
"""

import subprocess
import sys


def run_command(command):
    """Run a command and print what's happening."""
    print(f"🔄 Running: {command}")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        if result.returncode == 0:
            print("✅ Command completed successfully")
        else:
            print(f"❌ Command failed with exit code: {result.returncode}")
            return False
        return True
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return False


def main():
    print("🚀 SmartX Connector - Database Migration Tool")
    print("=" * 50)

    # Ask for migration name
    migration_name = input(
        "📝 Enter migration name (or press Enter for 'Initial migration'): "
    ).strip()
    if not migration_name:
        migration_name = "Initial migration"

    print(f"\n🎯 Creating migration: '{migration_name}'")
    print("-" * 30)

    # Create migration
    create_cmd = f'alembic revision --autogenerate -m "{migration_name}"'
    if not run_command(create_cmd):
        print("❌ Failed to create migration. Exiting.")
        sys.exit(1)

    print("\n🚀 Applying migrations to database...")
    print("-" * 30)

    # Apply migrations
    upgrade_cmd = "alembic upgrade head"
    if not run_command(upgrade_cmd):
        print("❌ Failed to apply migrations. Exiting.")
        sys.exit(1)

    print("\n🎉 Migration process completed successfully!")
    print("✅ Database is now up to date.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏸️ Operation cancelled by user")
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        sys.exit(1)
