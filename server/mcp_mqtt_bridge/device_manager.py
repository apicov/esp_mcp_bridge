"""
Device management for the MCP-MQTT bridge.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .data_models import IoTDevice, SensorReading, ActuatorState, DeviceCapabilities, DeviceMetrics

logger = logging.getLogger(__name__)


class DeviceManager:
    """Manages IoT device state and operations"""
    
    def __init__(self, device_timeout_minutes: int = 5):
        self.devices: Dict[str, IoTDevice] = {}
        self.device_metrics: Dict[str, DeviceMetrics] = {}
        self.device_timeout_minutes = device_timeout_minutes
    
    def get_device(self, device_id: str) -> Optional[IoTDevice]:
        """Get device by ID"""
        return self.devices.get(device_id)
    
    def get_all_devices(self, online_only: bool = False) -> List[IoTDevice]:
        """Get all devices, optionally filtered by online status"""
        if online_only:
            return [device for device in self.devices.values() if device.online]
        return list(self.devices.values())
    
    def get_devices_by_capability(self, sensor_type: Optional[str] = None, 
                                 actuator_type: Optional[str] = None,
                                 online_only: bool = True) -> List[IoTDevice]:
        """Get devices filtered by capabilities"""
        result = []
        
        for device in self.devices.values():
            if online_only and not device.online:
                continue
            
            if sensor_type and sensor_type not in device.capabilities.sensors:
                continue
            
            if actuator_type and actuator_type not in device.capabilities.actuators:
                continue
            
            result.append(device)
        
        return result
    
    def update_device_capabilities(self, device_id: str, capabilities_data: Dict[str, Any]):
        """Update device capabilities"""
        if device_id not in self.devices:
            self.devices[device_id] = IoTDevice(device_id=device_id)
        
        device = self.devices[device_id]
        device.capabilities.sensors = capabilities_data.get("sensors", [])
        device.capabilities.actuators = capabilities_data.get("actuators", [])
        device.capabilities.metadata = capabilities_data.get("metadata", {})
        device.capabilities.firmware_version = capabilities_data.get("firmware_version")
        device.capabilities.hardware_version = capabilities_data.get("hardware_version")
        device.last_seen = datetime.now()
        
        logger.info(f"Updated capabilities for device {device_id}")
    
    def update_sensor_reading(self, device_id: str, sensor_type: str, reading_data: Dict[str, Any]):
        """Update sensor reading for a device"""
        if device_id not in self.devices:
            self.devices[device_id] = IoTDevice(device_id=device_id)
        
        device = self.devices[device_id]
        
        # Extract value
        value_data = reading_data.get("value", {})
        if isinstance(value_data, dict):
            reading_value = value_data.get("reading", 0)
            unit = value_data.get("unit")
            quality = value_data.get("quality")
        else:
            reading_value = value_data
            unit = None
            quality = None
        
        # Create reading
        reading = SensorReading(
            device_id=device_id,
            sensor_type=sensor_type,
            value=reading_value,
            unit=unit,
            quality=quality,
            timestamp=datetime.fromtimestamp(reading_data.get("timestamp", datetime.now().timestamp()))
        )
        
        device.sensor_readings[sensor_type] = reading
        device.last_seen = datetime.now()
        
        # Update metrics
        if device_id not in self.device_metrics:
            self.device_metrics[device_id] = DeviceMetrics()
        self.device_metrics[device_id].messages_received += 1
        self.device_metrics[device_id].last_activity = datetime.now()
        
        logger.debug(f"Updated sensor reading for {device_id}/{sensor_type}: {reading_value}")
    
    def update_actuator_state(self, device_id: str, actuator_type: str, state_data: Dict[str, Any]):
        """Update actuator state for a device"""
        if device_id not in self.devices:
            self.devices[device_id] = IoTDevice(device_id=device_id)
        
        device = self.devices[device_id]
        state = state_data.get("value", "unknown")
        
        # Create state record
        actuator_state = ActuatorState(
            device_id=device_id,
            actuator_type=actuator_type,
            state=state,
            timestamp=datetime.fromtimestamp(state_data.get("timestamp", datetime.now().timestamp()))
        )
        
        device.actuator_states[actuator_type] = actuator_state
        device.last_seen = datetime.now()
        
        # Update metrics
        if device_id not in self.device_metrics:
            self.device_metrics[device_id] = DeviceMetrics()
        self.device_metrics[device_id].messages_received += 1
        self.device_metrics[device_id].last_activity = datetime.now()
        
        logger.info(f"Updated actuator state for {device_id}/{actuator_type}: {state}")
    
    def update_device_status(self, device_id: str, status_data: Dict[str, Any]):
        """Update device online/offline status"""
        if device_id not in self.devices:
            self.devices[device_id] = IoTDevice(device_id=device_id)
        
        device = self.devices[device_id]
        status = status_data.get("value", "unknown")
        
        was_online = device.online
        device.online = (status == "online")
        device.last_seen = datetime.now()
        
        if was_online != device.online:
            logger.info(f"Device {device_id} is now {'online' if device.online else 'offline'}")
    
    def add_device_error(self, device_id: str, error_data: Dict[str, Any]):
        """Add error to device error log"""
        if device_id not in self.devices:
            self.devices[device_id] = IoTDevice(device_id=device_id)
        
        device = self.devices[device_id]
        
        error_record = {
            "error_type": error_data.get("value", {}).get("error_type", "unknown"),
            "message": error_data.get("value", {}).get("message", ""),
            "severity": error_data.get("value", {}).get("severity", 2),
            "timestamp": datetime.fromtimestamp(error_data.get("timestamp", datetime.now().timestamp()))
        }
        
        device.errors.append(error_record)
        device.last_seen = datetime.now()
        
        # Keep only last 100 errors per device
        if len(device.errors) > 100:
            device.errors = device.errors[-100:]
        
        # Update metrics
        if device_id not in self.device_metrics:
            self.device_metrics[device_id] = DeviceMetrics()
        
        if error_record["error_type"] == "sensor_error":
            self.device_metrics[device_id].sensor_read_errors += 1
        elif error_record["error_type"] == "connection_error":
            self.device_metrics[device_id].connection_failures += 1
        
        logger.warning(f"Error from {device_id}: {error_record['error_type']} - {error_record['message']}")
    
    def check_device_timeouts(self):
        """Check for devices that haven't been seen recently and mark them offline"""
        current_time = datetime.now()
        timeout_threshold = timedelta(minutes=self.device_timeout_minutes)
        
        for device_id, device in self.devices.items():
            if device.online and (current_time - device.last_seen) > timeout_threshold:
                device.online = False
                logger.warning(f"Device {device_id} marked offline (timeout)")
    
    def get_device_summary(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive device summary"""
        device = self.get_device(device_id)
        if not device:
            return None
        
        metrics = self.device_metrics.get(device_id, DeviceMetrics())
        
        return {
            "device_id": device_id,
            "online": device.online,
            "last_seen": device.last_seen.isoformat(),
            "uptime_seconds": metrics.uptime_seconds,
            "capabilities": {
                "sensors": device.capabilities.sensors,
                "actuators": device.capabilities.actuators,
                "metadata": device.capabilities.metadata,
                "firmware_version": device.capabilities.firmware_version,
                "hardware_version": device.capabilities.hardware_version
            },
            "current_state": {
                "sensors": {
                    sensor: {
                        "value": reading.value,
                        "unit": reading.unit,
                        "quality": reading.quality,
                        "timestamp": reading.timestamp.isoformat(),
                        "age_seconds": (datetime.now() - reading.timestamp).total_seconds()
                    }
                    for sensor, reading in device.sensor_readings.items()
                },
                "actuators": {
                    actuator: {
                        "state": state.state,
                        "timestamp": state.timestamp.isoformat(),
                        "age_seconds": (datetime.now() - state.timestamp).total_seconds()
                    }
                    for actuator, state in device.actuator_states.items()
                }
            },
            "metrics": {
                "messages_sent": metrics.messages_sent,
                "messages_received": metrics.messages_received,
                "connection_failures": metrics.connection_failures,
                "sensor_read_errors": metrics.sensor_read_errors,
                "last_activity": metrics.last_activity.isoformat() if metrics.last_activity else None
            },
            "recent_errors": device.errors[-10:] if device.errors else []
        }
    
    def get_device_list_summary(self, online_only: bool = False) -> List[Dict[str, Any]]:
        """Get summary list of all devices"""
        devices = self.get_all_devices(online_only)
        
        return [
            {
                "device_id": device.device_id,
                "online": device.online,
                "last_seen": device.last_seen.isoformat(),
                "sensors": device.capabilities.sensors,
                "actuators": device.capabilities.actuators,
                "firmware_version": device.capabilities.firmware_version,
                "current_readings": {
                    sensor: {
                        "value": reading.value,
                        "unit": reading.unit,
                        "timestamp": reading.timestamp.isoformat()
                    }
                    for sensor, reading in device.sensor_readings.items()
                },
                "actuator_states": {
                    actuator: state.state
                    for actuator, state in device.actuator_states.items()
                }
            }
            for device in devices
        ]
    
    def increment_sent_messages(self, device_id: str):
        """Increment sent message count for device"""
        if device_id not in self.device_metrics:
            self.device_metrics[device_id] = DeviceMetrics()
        self.device_metrics[device_id].messages_sent += 1
    
    def get_alert_summary(self, device_id: Optional[str] = None, 
                         severity_min: int = 0) -> List[Dict[str, Any]]:
        """Get alert summary from device errors"""
        alerts = []
        
        devices_to_check = [self.devices[device_id]] if device_id and device_id in self.devices else self.devices.values()
        
        for device in devices_to_check:
            for error in device.errors:
                if error.get("severity", 2) >= severity_min:
                    alerts.append({
                        "device_id": device.device_id,
                        "timestamp": error.get("timestamp", datetime.now()).isoformat()
                            if isinstance(error.get("timestamp"), datetime)
                            else error.get("timestamp"),
                        "error_type": error.get("error_type"),
                        "message": error.get("message"),
                        "severity": error.get("severity")
                    })
        
        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Limit to last 50 alerts
        return alerts[:50] 