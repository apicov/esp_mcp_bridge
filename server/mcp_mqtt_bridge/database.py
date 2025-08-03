"""
Database management for the MCP-MQTT bridge.
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .data_models import SensorReading
from .timezone_utils import utc_now, utc_minus_timedelta, utc_isoformat, ensure_utc

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages persistent storage of device data"""
    
    def __init__(self, db_path: str = "iot_bridge.db"):
        self.db_path = db_path
        self.init_database()
    
    async def initialize(self):
        """Async initialize method for compatibility"""
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS sensor_readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        sensor_type TEXT NOT NULL,
                        value REAL NOT NULL,
                        unit TEXT,
                        quality REAL,
                        timestamp DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_sensor_device_type 
                    ON sensor_readings(device_id, sensor_type);
                    
                    CREATE INDEX IF NOT EXISTS idx_sensor_timestamp 
                    ON sensor_readings(timestamp);
                    
                    CREATE TABLE IF NOT EXISTS actuator_states (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        actuator_type TEXT NOT NULL,
                        state TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_actuator_device_type 
                    ON actuator_states(device_id, actuator_type);
                    
                    CREATE TABLE IF NOT EXISTS device_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        data TEXT,
                        severity INTEGER DEFAULT 0,
                        timestamp DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_event_device_type 
                    ON device_events(device_id, event_type);
                    
                    CREATE INDEX IF NOT EXISTS idx_event_timestamp 
                    ON device_events(timestamp);
                    
                    CREATE TABLE IF NOT EXISTS device_capabilities (
                        device_id TEXT PRIMARY KEY,
                        sensors TEXT,
                        actuators TEXT,
                        metadata TEXT,
                        firmware_version TEXT,
                        hardware_version TEXT,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS device_metrics (
                        device_id TEXT PRIMARY KEY,
                        messages_sent INTEGER DEFAULT 0,
                        messages_received INTEGER DEFAULT 0,
                        connection_failures INTEGER DEFAULT 0,
                        sensor_read_errors INTEGER DEFAULT 0,
                        last_activity DATETIME,
                        uptime_start DATETIME,
                        last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS devices (
                        device_id TEXT PRIMARY KEY,
                        device_type TEXT,
                        sensors TEXT,
                        actuators TEXT,
                        firmware_version TEXT,
                        location TEXT,
                        status TEXT DEFAULT 'offline',
                        last_seen DATETIME,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS sensor_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        sensor_type TEXT NOT NULL,
                        value REAL NOT NULL,
                        unit TEXT,
                        timestamp DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (device_id) REFERENCES devices(device_id)
                    );
                    
                    CREATE TABLE IF NOT EXISTS device_errors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT NOT NULL,
                        error_type TEXT NOT NULL,
                        message TEXT,
                        severity INTEGER DEFAULT 1,
                        timestamp DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (device_id) REFERENCES devices(device_id)
                    );
                """)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def store_sensor_reading(self, reading: SensorReading):
        """Store a sensor reading"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO sensor_readings 
                    (device_id, sensor_type, value, unit, quality, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    reading.device_id,
                    reading.sensor_type,
                    reading.value,
                    reading.unit,
                    reading.quality,
                    reading.timestamp
                ))
        except Exception as e:
            logger.error(f"Failed to store sensor reading: {e}")
    
    def store_sensor_readings_batch(self, readings: List[SensorReading]):
        """Store multiple sensor readings in a batch"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.executemany("""
                    INSERT INTO sensor_readings 
                    (device_id, sensor_type, value, unit, quality, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, [
                    (r.device_id, r.sensor_type, r.value, r.unit, r.quality, r.timestamp)
                    for r in readings
                ])
            logger.debug(f"Stored {len(readings)} sensor readings")
        except Exception as e:
            logger.error(f"Failed to store sensor readings batch: {e}")
    
    def get_sensor_history(self, device_id: str, sensor_type: str, 
                          duration_minutes: int = 60) -> List[Dict[str, Any]]:
        """Get historical sensor data"""
        try:
            since = utc_minus_timedelta(timedelta(minutes=duration_minutes))
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM sensor_readings
                    WHERE device_id = ? AND sensor_type = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                    LIMIT 1000
                """, (device_id, sensor_type, since))
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get sensor history: {e}")
            return []
    
    def get_latest_sensor_reading(self, device_id: str, sensor_type: str) -> Optional[Dict[str, Any]]:
        """Get the latest sensor reading for a device/sensor"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM sensor_readings
                    WHERE device_id = ? AND sensor_type = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (device_id, sensor_type))
                
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Failed to get latest sensor reading: {e}")
            return None
    
    def store_actuator_state(self, device_id: str, actuator_type: str, state: str, timestamp: datetime):
        """Store actuator state"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO actuator_states 
                    (device_id, actuator_type, state, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (device_id, actuator_type, state, timestamp))
        except Exception as e:
            logger.error(f"Failed to store actuator state: {e}")
    
    def store_device_event(self, device_id: str, event_type: str, data: str, 
                          severity: int = 0, timestamp: datetime = None):
        """Store device event"""
        if timestamp is None:
            timestamp = utc_now()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO device_events 
                    (device_id, event_type, data, severity, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (device_id, event_type, data, severity, timestamp))
        except Exception as e:
            logger.error(f"Failed to store device event: {e}")
    
    def get_device_events(self, device_id: Optional[str] = None, 
                         event_type: Optional[str] = None,
                         severity_min: int = 0,
                         duration_hours: int = 24) -> List[Dict[str, Any]]:
        """Get device events with filtering"""
        try:
            since = utc_minus_timedelta(timedelta(hours=duration_hours))
            
            query = """
                SELECT * FROM device_events
                WHERE timestamp > ? AND severity >= ?
            """
            params = [since, severity_min]
            
            if device_id:
                query += " AND device_id = ?"
                params.append(device_id)
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            
            query += " ORDER BY timestamp DESC LIMIT 500"
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get device events: {e}")
            return []
    
    def update_device_capabilities(self, device_id: str, capabilities: Dict[str, Any]):
        """Update device capabilities"""
        try:
            import json
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO device_capabilities 
                    (device_id, sensors, actuators, metadata, firmware_version, hardware_version, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    device_id,
                    json.dumps(capabilities.get('sensors', [])),
                    json.dumps(capabilities.get('actuators', [])),
                    json.dumps(capabilities.get('metadata', {})),
                    capabilities.get('firmware_version'),
                    capabilities.get('hardware_version'),
                    utc_now()
                ))
        except Exception as e:
            logger.error(f"Failed to update device capabilities: {e}")
    
    def update_device_metrics(self, device_id: str, metrics: Dict[str, Any]):
        """Update device metrics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO device_metrics 
                    (device_id, messages_sent, messages_received, connection_failures, 
                     sensor_read_errors, last_activity, uptime_start, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    device_id,
                    metrics.get('messages_sent', 0),
                    metrics.get('messages_received', 0),
                    metrics.get('connection_failures', 0),
                    metrics.get('sensor_read_errors', 0),
                    metrics.get('last_activity', utc_now()),
                    metrics.get('uptime_start', utc_now()),
                    utc_now()
                ))
        except Exception as e:
            logger.error(f"Failed to update device metrics: {e}")
    
    def cleanup_old_data(self, retention_days: int = 30):
        """Clean up old data beyond retention period"""
        try:
            cutoff_date = utc_minus_timedelta(timedelta(days=retention_days))
            
            with sqlite3.connect(self.db_path) as conn:
                # Clean up old sensor readings
                result = conn.execute("""
                    DELETE FROM sensor_readings 
                    WHERE timestamp < ?
                """, (cutoff_date,))
                sensor_deleted = result.rowcount
                
                # Clean up old device events
                result = conn.execute("""
                    DELETE FROM device_events 
                    WHERE timestamp < ?
                """, (cutoff_date,))
                events_deleted = result.rowcount
                
                # Clean up old actuator states (keep only latest for each device/actuator)
                result = conn.execute("""
                    DELETE FROM actuator_states 
                    WHERE id NOT IN (
                        SELECT MAX(id) FROM actuator_states 
                        GROUP BY device_id, actuator_type
                    ) AND timestamp < ?
                """, (cutoff_date,))
                states_deleted = result.rowcount
                
                # Also clean up test tables if they exist
                total_deleted = sensor_deleted + events_deleted + states_deleted
                try:
                    # Clean up old sensor_data (test table)
                    result = conn.execute("""
                        DELETE FROM sensor_data 
                        WHERE timestamp < ?
                    """, (cutoff_date.isoformat(),))
                    total_deleted += result.rowcount
                    
                    # Clean up old device_errors (test table)
                    result = conn.execute("""
                        DELETE FROM device_errors 
                        WHERE timestamp < ?
                    """, (cutoff_date.isoformat(),))
                    total_deleted += result.rowcount
                except sqlite3.OperationalError:
                    # Tables don't exist, that's ok
                    pass
                
                logger.info(f"Cleaned up {total_deleted} total records")
                return total_deleted
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return 0
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                stats = {}
                
                # Count records in each table
                tables = ['sensor_readings', 'actuator_states', 'device_events', 
                         'device_capabilities', 'device_metrics']
                
                for table in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    stats[f"{table}_count"] = cursor.fetchone()[0]
                
                # Get database size
                cursor = conn.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor = conn.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                stats['database_size_bytes'] = page_count * page_size
                
                return stats
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {} 

    def close(self):
        """Close database connection (no-op for SQLite)"""
        pass
    
    # Additional methods expected by tests
    def register_device(self, device_data: Dict[str, Any]):
        """Register a new device"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO devices 
                    (device_id, device_type, sensors, actuators, firmware_version, location, status, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    device_data["device_id"],
                    device_data.get("device_type", ""),
                    json.dumps(device_data.get("sensors", [])),
                    json.dumps(device_data.get("actuators", [])),
                    device_data.get("firmware_version", ""),
                    device_data.get("location", ""),
                    device_data.get("status", "offline"),
                    utc_now().isoformat()
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to register device: {e}")
            raise
    
    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT device_id, device_type, sensors, actuators, firmware_version, 
                           location, status, last_seen, created_at
                    FROM devices WHERE device_id = ?
                """, (device_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        "device_id": row[0],
                        "device_type": row[1],
                        "sensors": json.loads(row[2]) if row[2] else [],
                        "actuators": json.loads(row[3]) if row[3] else [],
                        "firmware_version": row[4],
                        "location": row[5],
                        "status": row[6],
                        "last_seen": row[7],
                        "created_at": row[8]
                    }
                return None
        except Exception as e:
            logger.error(f"Failed to get device: {e}")
            return None
    
    def update_device_status(self, device_id: str, status: str):
        """Update device status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE devices SET status = ?, last_seen = ? WHERE device_id = ?
                """, (status, utc_isoformat(), device_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update device status: {e}")
            raise
    
    def store_sensor_data(self, sensor_data: Dict[str, Any]):
        """Store sensor data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO sensor_data (device_id, sensor_type, value, unit, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    sensor_data["device_id"],
                    sensor_data["sensor_type"],
                    sensor_data["value"],
                    sensor_data.get("unit", ""),
                    sensor_data["timestamp"]
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to store sensor data: {e}")
            raise
    
    def get_sensor_data(self, device_id: str, sensor_type: str, history_minutes: int) -> List[Dict[str, Any]]:
        """Get sensor data with history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                since_time = utc_isoformat(utc_minus_timedelta(timedelta(minutes=history_minutes)))
                cursor.execute("""
                    SELECT device_id, sensor_type, value, unit, timestamp
                    FROM sensor_data 
                    WHERE device_id = ? AND sensor_type = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                """, (device_id, sensor_type, since_time))
                rows = cursor.fetchall()
                return [
                    {
                        "device_id": row[0],
                        "sensor_type": row[1],
                        "value": row[2],
                        "unit": row[3],
                        "timestamp": row[4]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get sensor data: {e}")
            return []
    
    def log_device_error(self, error_data: Dict[str, Any]):
        """Log a device error"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO device_errors (device_id, error_type, message, severity, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    error_data["device_id"],
                    error_data["error_type"],
                    error_data["message"],
                    error_data.get("severity", 1),
                    error_data["timestamp"]
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log device error: {e}")
            raise
    
    def get_device_errors(self, device_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get device errors"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                since_time = utc_isoformat(utc_minus_timedelta(timedelta(hours=hours)))
                cursor.execute("""
                    SELECT device_id, error_type, message, severity, timestamp
                    FROM device_errors 
                    WHERE device_id = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                """, (device_id, since_time))
                rows = cursor.fetchall()
                return [
                    {
                        "device_id": row[0],
                        "error_type": row[1],
                        "message": row[2],
                        "severity": row[3],
                        "timestamp": row[4]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get device errors: {e}")
            return []
    
    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get all devices"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT device_id, device_type, sensors, actuators, firmware_version, 
                           location, status, last_seen, created_at
                    FROM devices
                """)
                rows = cursor.fetchall()
                return [
                    {
                        "device_id": row[0],
                        "device_type": row[1],
                        "sensors": json.loads(row[2]) if row[2] else [],
                        "actuators": json.loads(row[3]) if row[3] else [],
                        "firmware_version": row[4],
                        "location": row[5],
                        "status": row[6],
                        "last_seen": row[7],
                        "created_at": row[8]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get all devices: {e}")
            return []
    
    def get_online_devices(self) -> List[Dict[str, Any]]:
        """Get only online devices"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT device_id, device_type, sensors, actuators, firmware_version, 
                           location, status, last_seen, created_at
                    FROM devices WHERE status = 'online'
                """)
                rows = cursor.fetchall()
                return [
                    {
                        "device_id": row[0],
                        "device_type": row[1],
                        "sensors": json.loads(row[2]) if row[2] else [],
                        "actuators": json.loads(row[3]) if row[3] else [],
                        "firmware_version": row[4],
                        "location": row[5],
                        "status": row[6],
                        "last_seen": row[7],
                        "created_at": row[8]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get online devices: {e}")
            return [] 