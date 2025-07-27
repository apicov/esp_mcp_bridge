#!/usr/bin/env python3
"""
Database migration and cleanup script for MCP-MQTT Bridge.
Handles schema migrations, data cleanup, and database maintenance.
"""
import argparse
import sys
import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_mqtt_bridge.database import DatabaseManager


def setup_logging(log_level: str = "INFO"):
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('migration.log')
        ]
    )
    return logging.getLogger(__name__)


def get_database_version(db_path: str) -> int:
    """Get current database schema version."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            result = cursor.fetchone()
            return result[0] if result else 0
    except sqlite3.OperationalError:
        # Table doesn't exist, database is at version 0
        return 0


def create_schema_version_table(db_path: str, logger: logging.Logger):
    """Create schema version tracking table."""
    logger.info("Creating schema version table")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                description TEXT
            )
        """)
        conn.commit()


def apply_migration_v1(db_path: str, logger: logging.Logger):
    """Apply migration to version 1: Add device location index."""
    logger.info("Applying migration v1: Adding device location index")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Add index on device location for better query performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_device_location 
            ON devices(location) WHERE location IS NOT NULL
        """)
        
        # Record migration
        cursor.execute("""
            INSERT INTO schema_version (version, description) 
            VALUES (1, 'Add device location index')
        """)
        conn.commit()


def apply_migration_v2(db_path: str, logger: logging.Logger):
    """Apply migration to version 2: Add device error count tracking."""
    logger.info("Applying migration v2: Adding device error tracking")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Add error count column to devices table
        cursor.execute("""
            ALTER TABLE devices 
            ADD COLUMN error_count INTEGER DEFAULT 0
        """)
        
        # Add index on sensor_data timestamp for cleanup performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sensor_data_timestamp 
            ON sensor_data(timestamp)
        """)
        
        # Record migration
        cursor.execute("""
            INSERT INTO schema_version (version, description) 
            VALUES (2, 'Add device error tracking and sensor data timestamp index')
        """)
        conn.commit()


def apply_migration_v3(db_path: str, logger: logging.Logger):
    """Apply migration to version 3: Add device groups support."""
    logger.info("Applying migration v3: Adding device groups support")
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Create device groups table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_groups (
                group_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create device group membership table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_group_members (
                group_id TEXT,
                device_id TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, device_id),
                FOREIGN KEY (group_id) REFERENCES device_groups(group_id),
                FOREIGN KEY (device_id) REFERENCES devices(device_id)
            )
        """)
        
        # Record migration
        cursor.execute("""
            INSERT INTO schema_version (version, description) 
            VALUES (3, 'Add device groups support')
        """)
        conn.commit()


# Migration registry
MIGRATIONS = {
    1: apply_migration_v1,
    2: apply_migration_v2,
    3: apply_migration_v3,
}

LATEST_VERSION = max(MIGRATIONS.keys()) if MIGRATIONS else 0


def run_migrations(db_path: str, target_version: int = None, logger: logging.Logger = None):
    """Run database migrations up to target version."""
    if not logger:
        logger = setup_logging()
    
    if not Path(db_path).exists():
        logger.error(f"Database file not found: {db_path}")
        return False
    
    current_version = get_database_version(db_path)
    target_version = target_version or LATEST_VERSION
    
    logger.info(f"Current database version: {current_version}")
    logger.info(f"Target version: {target_version}")
    
    if current_version >= target_version:
        logger.info("Database is already up to date")
        return True
    
    # Create schema version table if it doesn't exist
    if current_version == 0:
        create_schema_version_table(db_path, logger)
    
    # Apply migrations
    for version in range(current_version + 1, target_version + 1):
        if version in MIGRATIONS:
            try:
                logger.info(f"Applying migration to version {version}")
                MIGRATIONS[version](db_path, logger)
                logger.info(f"Successfully applied migration to version {version}")
            except Exception as e:
                logger.error(f"Failed to apply migration to version {version}: {e}")
                return False
        else:
            logger.warning(f"No migration found for version {version}")
    
    logger.info("All migrations completed successfully")
    return True


def cleanup_old_data(db_path: str, retention_days: int = 30, logger: logging.Logger = None):
    """Clean up old sensor data and device errors."""
    if not logger:
        logger = setup_logging()
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    cutoff_timestamp = cutoff_date.isoformat()
    
    logger.info(f"Cleaning up data older than {retention_days} days ({cutoff_timestamp})")
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Clean up old sensor data
        cursor.execute("""
            DELETE FROM sensor_data 
            WHERE timestamp < ?
        """, (cutoff_timestamp,))
        sensor_deleted = cursor.rowcount
        
        # Clean up old device errors
        cursor.execute("""
            DELETE FROM device_errors 
            WHERE timestamp < ?
        """, (cutoff_timestamp,))
        error_deleted = cursor.rowcount
        
        # Reset error counts for devices with no recent errors
        cursor.execute("""
            UPDATE devices 
            SET error_count = 0 
            WHERE device_id NOT IN (
                SELECT DISTINCT device_id 
                FROM device_errors 
                WHERE timestamp > ?
            )
        """, (cutoff_timestamp,))
        reset_count = cursor.rowcount
        
        conn.commit()
        
        logger.info(f"Cleanup completed:")
        logger.info(f"  - Deleted {sensor_deleted} old sensor readings")
        logger.info(f"  - Deleted {error_deleted} old device errors")
        logger.info(f"  - Reset error count for {reset_count} devices")


def get_database_stats(db_path: str) -> Dict[str, Any]:
    """Get database statistics."""
    stats = {}
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Device counts
        cursor.execute("SELECT COUNT(*) FROM devices")
        stats['total_devices'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM devices WHERE status = 'online'")
        stats['online_devices'] = cursor.fetchone()[0]
        
        # Sensor data counts
        cursor.execute("SELECT COUNT(*) FROM sensor_data")
        stats['total_sensor_readings'] = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM sensor_data 
            WHERE timestamp > datetime('now', '-24 hours')
        """)
        stats['recent_sensor_readings'] = cursor.fetchone()[0]
        
        # Error counts
        cursor.execute("SELECT COUNT(*) FROM device_errors")
        stats['total_errors'] = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM device_errors 
            WHERE timestamp > datetime('now', '-24 hours')
        """)
        stats['recent_errors'] = cursor.fetchone()[0]
        
        # Database size
        cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
        stats['database_size_bytes'] = cursor.fetchone()[0]
        
    return stats


def main():
    """Main function for command line usage."""
    parser = argparse.ArgumentParser(description="MCP-MQTT Bridge Database Migration Tool")
    parser.add_argument("--db-path", default="./data/bridge.db", 
                       help="Path to database file")
    parser.add_argument("--migrate", action="store_true", 
                       help="Run database migrations")
    parser.add_argument("--target-version", type=int, 
                       help="Target migration version")
    parser.add_argument("--cleanup", action="store_true", 
                       help="Clean up old data")
    parser.add_argument("--retention-days", type=int, default=30, 
                       help="Data retention period in days")
    parser.add_argument("--stats", action="store_true", 
                       help="Show database statistics")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    
    args = parser.parse_args()
    logger = setup_logging(args.log_level)
    
    if not Path(args.db_path).exists() and not args.migrate:
        logger.error(f"Database file not found: {args.db_path}")
        sys.exit(1)
    
    if args.migrate:
        success = run_migrations(args.db_path, args.target_version, logger)
        if not success:
            sys.exit(1)
    
    if args.cleanup:
        cleanup_old_data(args.db_path, args.retention_days, logger)
    
    if args.stats:
        stats = get_database_stats(args.db_path)
        print("\n📊 Database Statistics:")
        print(f"  Total devices: {stats['total_devices']}")
        print(f"  Online devices: {stats['online_devices']}")
        print(f"  Total sensor readings: {stats['total_sensor_readings']:,}")
        print(f"  Recent readings (24h): {stats['recent_sensor_readings']:,}")
        print(f"  Total errors: {stats['total_errors']:,}")
        print(f"  Recent errors (24h): {stats['recent_errors']:,}")
        print(f"  Database size: {stats['database_size_bytes'] / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main() 