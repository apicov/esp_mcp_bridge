"""
Unit tests for DatabaseManager.
"""
import pytest
import sqlite3
import tempfile
import os
from datetime import datetime, timedelta
from mcp_mqtt_bridge.database import DatabaseManager


class TestDatabaseManager:
    """Test cases for DatabaseManager."""
    
    @pytest.fixture
    def db_manager(self, temp_db_path):
        """Create a DatabaseManager instance for testing."""
        manager = DatabaseManager(db_path=temp_db_path)
        yield manager
        manager.close()
    
    def test_initialization(self, temp_db_path):
        """Test database initialization."""
        manager = DatabaseManager(db_path=temp_db_path)
        
        # Check that tables exist
        with sqlite3.connect(temp_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('devices', 'sensor_data', 'device_errors')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            assert 'devices' in tables
            assert 'sensor_data' in tables
            assert 'device_errors' in tables
        
        manager.close()
    
    def test_register_device(self, db_manager):
        """Test device registration."""
        device_data = {
            "device_id": "test_device_001",
            "device_type": "ESP32",
            "sensors": ["temperature", "humidity"],
            "actuators": ["led", "relay"],
            "firmware_version": "1.0.0",
            "location": "test_lab"
        }
        
        # Register device
        db_manager.register_device(device_data)
        
        # Verify device was registered
        device = db_manager.get_device("test_device_001")
        assert device is not None
        assert device["device_id"] == "test_device_001"
        assert device["device_type"] == "ESP32"
        assert device["location"] == "test_lab"
    
    def test_update_device_status(self, db_manager):
        """Test device status updates."""
        # First register a device
        device_data = {
            "device_id": "test_device_002",
            "device_type": "ESP32",
            "sensors": ["temperature"],
            "actuators": ["led"],
            "firmware_version": "1.0.0"
        }
        db_manager.register_device(device_data)
        
        # Update status
        db_manager.update_device_status("test_device_002", "online")
        
        # Verify status was updated
        device = db_manager.get_device("test_device_002")
        assert device["status"] == "online"
    
    def test_store_sensor_data(self, db_manager):
        """Test storing sensor data."""
        # Register device first
        device_data = {
            "device_id": "test_device_003",
            "device_type": "ESP32",
            "sensors": ["temperature"],
            "actuators": [],
            "firmware_version": "1.0.0"
        }
        db_manager.register_device(device_data)
        
        # Store sensor data
        sensor_data = {
            "device_id": "test_device_003",
            "sensor_type": "temperature",
            "value": 23.5,
            "unit": "°C",
            "timestamp": datetime.now().isoformat()
        }
        db_manager.store_sensor_data(sensor_data)
        
        # Verify data was stored
        readings = db_manager.get_sensor_data("test_device_003", "temperature", 60)
        assert len(readings) == 1
        assert readings[0]["value"] == 23.5
        assert readings[0]["unit"] == "°C"
    
    def test_get_sensor_data_with_history(self, db_manager):
        """Test retrieving sensor data with history."""
        device_id = "test_device_004"
        
        # Register device
        device_data = {
            "device_id": device_id,
            "device_type": "ESP32",
            "sensors": ["temperature"],
            "actuators": [],
            "firmware_version": "1.0.0"
        }
        db_manager.register_device(device_data)
        
        # Store multiple readings
        base_time = datetime.now()
        for i in range(5):
            sensor_data = {
                "device_id": device_id,
                "sensor_type": "temperature",
                "value": 20.0 + i,
                "unit": "°C",
                "timestamp": (base_time - timedelta(hours=i)).isoformat()
            }
            db_manager.store_sensor_data(sensor_data)
        
        # Get data from last 3 hours
        readings = db_manager.get_sensor_data(device_id, "temperature", 180)
        assert len(readings) == 3  # Should get 3 readings within 3 hours
    
    def test_log_device_error(self, db_manager):
        """Test logging device errors."""
        device_id = "test_device_005"
        
        # Register device
        device_data = {
            "device_id": device_id,
            "device_type": "ESP32",
            "sensors": [],
            "actuators": [],
            "firmware_version": "1.0.0"
        }
        db_manager.register_device(device_data)
        
        # Log an error
        error_data = {
            "device_id": device_id,
            "error_type": "connection_timeout",
            "message": "Device failed to respond",
            "severity": 2,
            "timestamp": datetime.now().isoformat()
        }
        db_manager.log_device_error(error_data)
        
        # Verify error was logged
        errors = db_manager.get_device_errors(device_id, hours=1)
        assert len(errors) == 1
        assert errors[0]["error_type"] == "connection_timeout"
        assert errors[0]["severity"] == 2
    
    def test_get_all_devices(self, db_manager):
        """Test getting all devices."""
        # Register multiple devices
        for i in range(3):
            device_data = {
                "device_id": f"test_device_{i:03d}",
                "device_type": "ESP32",
                "sensors": ["temperature"],
                "actuators": ["led"],
                "firmware_version": "1.0.0"
            }
            db_manager.register_device(device_data)
        
        # Get all devices
        devices = db_manager.get_all_devices()
        assert len(devices) >= 3
        
        device_ids = [d["device_id"] for d in devices]
        assert "test_device_000" in device_ids
        assert "test_device_001" in device_ids
        assert "test_device_002" in device_ids
    
    def test_get_online_devices(self, db_manager):
        """Test getting only online devices."""
        # Register devices with different statuses
        for i, status in enumerate(["online", "offline", "online"]):
            device_data = {
                "device_id": f"status_test_{i}",
                "device_type": "ESP32",
                "sensors": [],
                "actuators": [],
                "firmware_version": "1.0.0"
            }
            db_manager.register_device(device_data)
            db_manager.update_device_status(f"status_test_{i}", status)
        
        # Get only online devices
        online_devices = db_manager.get_online_devices()
        online_ids = [d["device_id"] for d in online_devices]
        
        assert "status_test_0" in online_ids
        assert "status_test_1" not in online_ids
        assert "status_test_2" in online_ids
    
    def test_cleanup_old_data(self, db_manager):
        """Test cleanup of old sensor data."""
        device_id = "cleanup_test"
        
        # Register device
        device_data = {
            "device_id": device_id,
            "device_type": "ESP32",
            "sensors": ["temperature"],
            "actuators": [],
            "firmware_version": "1.0.0"
        }
        db_manager.register_device(device_data)
        
        # Store old and new data
        old_time = datetime.now() - timedelta(days=31)
        new_time = datetime.now()
        
        for time_val, prefix in [(old_time, "old"), (new_time, "new")]:
            sensor_data = {
                "device_id": device_id,
                "sensor_type": "temperature",
                "value": 25.0,
                "unit": "°C",
                "timestamp": time_val.isoformat()
            }
            db_manager.store_sensor_data(sensor_data)
        
        # Clean up data older than 30 days
        cleaned_count = db_manager.cleanup_old_data(retention_days=30)
        assert cleaned_count > 0
        
        # Verify only new data remains
        all_readings = db_manager.get_sensor_data(device_id, "temperature", 24*60*32)  # 32 days
        assert len(all_readings) == 1  # Only the new reading should remain 