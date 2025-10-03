#!/usr/bin/env python3
"""
Database Cleanup Script

Clean up old data from the MCP bridge database.

Usage:
    # Clean data older than 30 days
    python cleanup_database.py --days 30

    # Clean data older than 7 days
    python cleanup_database.py --days 7

    # Show stats without cleaning
    python cleanup_database.py --stats-only

    # Complete reset (careful!)
    python cleanup_database.py --reset
"""

import argparse
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_mqtt_bridge.database import DatabaseManager


def show_stats(db: DatabaseManager):
    """Show database statistics"""
    print("\n📊 Database Statistics:")
    print("=" * 60)

    stats = db.get_database_stats()

    if stats.get('success'):
        print(f"Database size: {stats['database_size_bytes'] / 1024 / 1024:.2f} MB")
        print(f"\nTable statistics:")
        for key, value in stats.items():
            if key.endswith('_count') and key != 'database_size_bytes':
                table_name = key.replace('_count', '')
                print(f"  {table_name:30s}: {value:,} records")
    else:
        print(f"❌ Failed to get stats: {stats.get('error')}")

    print("=" * 60)


def cleanup_old_data(db: DatabaseManager, days: int):
    """Clean up old data"""
    print(f"\n🧹 Cleaning up data older than {days} days...")

    deleted = db.cleanup_old_data(retention_days=days)

    if deleted > 0:
        print(f"✅ Deleted {deleted:,} old records")
    else:
        print("✅ No old records to delete")


def reset_database(db_path: str):
    """Reset the database completely"""
    print("\n⚠️  WARNING: This will delete ALL data!")
    response = input("Type 'yes' to confirm reset: ")

    if response.lower() == 'yes':
        # Backup first
        backup_path = f"{db_path}.backup"
        if os.path.exists(db_path):
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"✅ Backup created: {backup_path}")

        # Delete database
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"✅ Database deleted: {db_path}")

        # Recreate fresh database
        db = DatabaseManager(db_path)
        print("✅ Fresh database created")
    else:
        print("❌ Reset cancelled")


def main():
    parser = argparse.ArgumentParser(
        description="Clean up MCP bridge database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cleanup_database.py --days 30          # Clean data older than 30 days
  python cleanup_database.py --stats-only       # Show stats only
  python cleanup_database.py --reset            # Complete reset (careful!)
  python cleanup_database.py --db custom.db     # Use custom database file
        """
    )

    parser.add_argument(
        '--db',
        default='iot_bridge.db',
        help='Database file path (default: iot_bridge.db)'
    )

    parser.add_argument(
        '--days',
        type=int,
        help='Delete data older than N days'
    )

    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Only show statistics, do not clean'
    )

    parser.add_argument(
        '--reset',
        action='store_true',
        help='Complete database reset (WARNING: deletes all data!)'
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("MCP Bridge Database Cleanup Tool")
    print("=" * 60)

    # Handle reset
    if args.reset:
        reset_database(args.db)
        return

    # Open database
    if not os.path.exists(args.db):
        print(f"❌ Database not found: {args.db}")
        return

    db = DatabaseManager(args.db)

    # Show stats
    show_stats(db)

    # Clean up if requested
    if args.days and not args.stats_only:
        cleanup_old_data(db, args.days)

        # Show stats again
        print("\n📊 After cleanup:")
        show_stats(db)
    elif not args.stats_only and not args.days:
        print("\n💡 Use --days N to clean up old data")
        print("   Example: python cleanup_database.py --days 30")

    print("\n✅ Done!")


if __name__ == "__main__":
    main()
