"""
Database management for the MCP-MQTT bridge.
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from .data_models import SensorReading

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages persistent storage of device data"""
    
    def __init__(self, db_path: str = "iot_bridge.db"):
        self.db_path = db_path
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
            since = datetime.now() - timedelta(minutes=duration_minutes)
            
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
            timestamp = datetime.now()
        
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
            since = datetime.now() - timedelta(hours=duration_hours)
            
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
                    datetime.now()
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
                    metrics.get('last_activity', datetime.now()),
                    metrics.get('uptime_start', datetime.now()),
                    datetime.now()
                ))
        except Exception as e:
            logger.error(f"Failed to update device metrics: {e}")
    
    def cleanup_old_data(self, retention_days: int = 30):
        """Clean up old data beyond retention period"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
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
                conn.execute("""
                    DELETE FROM actuator_states 
                    WHERE id NOT IN (
                        SELECT MAX(id) FROM actuator_states 
                        GROUP BY device_id, actuator_type
                    ) AND timestamp < ?
                """, (cutoff_date,))
                
                logger.info(f"Cleaned up {sensor_deleted} sensor readings and {events_deleted} events")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
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