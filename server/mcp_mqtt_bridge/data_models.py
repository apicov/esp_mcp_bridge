"""
Data models for the MCP-MQTT bridge server.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class SensorReading:
    """Represents a sensor reading"""
    device_id: str
    sensor_type: str
    value: float
    unit: Optional[str]
    timestamp: datetime
    quality: Optional[float] = None


@dataclass
class ActuatorState:
    """Represents an actuator state"""
    device_id: str
    actuator_type: str
    state: str
    timestamp: datetime


@dataclass
class DeviceCapabilities:
    """Device capability information"""
    sensors: List[str] = field(default_factory=list)
    actuators: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None


@dataclass
class IoTDevice:
    """Represents a connected IoT device"""
    device_id: str
    capabilities: DeviceCapabilities = field(default_factory=DeviceCapabilities)
    online: bool = False
    last_seen: datetime = field(default_factory=datetime.now)
    sensor_readings: Dict[str, SensorReading] = field(default_factory=dict)
    actuator_states: Dict[str, ActuatorState] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DeviceMetrics:
    """Device metrics and statistics"""
    messages_sent: int = 0
    messages_received: int = 0
    connection_failures: int = 0
    sensor_read_errors: int = 0
    last_activity: datetime = field(default_factory=datetime.now)
    uptime_start: datetime = field(default_factory=datetime.now)
    
    @property
    def uptime_seconds(self) -> int:
        return int((datetime.now() - self.uptime_start).total_seconds())


@dataclass
class BridgeConfig:
    """Configuration for the MCP-MQTT bridge"""
    mqtt_broker: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    db_path: str = "iot_bridge.db"
    log_level: str = "INFO"
    device_timeout_minutes: int = 5
    cleanup_interval_hours: int = 24
    max_errors_per_device: int = 100 