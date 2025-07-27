"""
MCP Server Module

Handles the Model Context Protocol interface, exposing IoT device capabilities
and control to LLM agents through standardized tools.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MCPServerManager:
    """Manages MCP tools and protocol interface"""
    
    def __init__(self, device_manager, database_manager):
        self.device_manager = device_manager
        self.database_manager = database_manager
        self.tools = self._register_tools()
    
    def _register_tools(self) -> Dict[str, callable]:
        """Register all available MCP tools"""
        return {
            "list_devices": self.list_devices,
            "read_sensor": self.read_sensor, 
            "control_actuator": self.control_actuator,
            "get_device_info": self.get_device_info,
            "query_devices": self.query_devices,
            "get_alerts": self.get_alerts,
            "get_system_status": self.get_system_status,
            "get_device_metrics": self.get_device_metrics
        }
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP tool calls"""
        if tool_name not in self.tools:
            return {
                "error": f"Unknown tool: {tool_name}",
                "available_tools": list(self.tools.keys())
            }
        
        try:
            result = await self.tools[tool_name](**arguments)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}
    
    async def list_devices(self, online_only: bool = False) -> List[Dict[str, Any]]:
        """List all connected IoT devices"""
        devices = self.device_manager.get_all_devices()
        
        device_list = []
        for device in devices.values():
            if online_only and not device.is_online:
                continue
                
            device_info = {
                "device_id": device.device_id,
                "is_online": device.is_online,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                "sensors": list(device.sensor_readings.keys()),
                "actuators": list(device.actuator_states.keys()),
                "capabilities": device.capabilities.__dict__ if device.capabilities else None
            }
            device_list.append(device_info)
        
        return device_list
    
    async def read_sensor(self, device_id: str, sensor_type: str, 
                         history_minutes: int = 0) -> Dict[str, Any]:
        """Read current sensor data with optional history"""
        device = self.device_manager.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        # Get current reading
        current_reading = device.sensor_readings.get(sensor_type)
        if not current_reading:
            raise ValueError(f"Sensor {sensor_type} not found on device {device_id}")
        
        result = {
            "device_id": device_id,
            "sensor_type": sensor_type,
            "current_value": current_reading.value,
            "unit": current_reading.unit,
            "timestamp": current_reading.timestamp.isoformat(),
            "quality": current_reading.quality
        }
        
        # Add historical data if requested
        if history_minutes > 0:
            history = self.database_manager.get_sensor_data(
                device_id, sensor_type, history_minutes
            )
            result["history"] = [
                {
                    "value": reading["value"],
                    "timestamp": reading["timestamp"],
                    "unit": reading["unit"]
                }
                for reading in history
            ]
        
        return result
    
    async def control_actuator(self, device_id: str, actuator_type: str, 
                             action: str, value: Any = None) -> Dict[str, Any]:
        """Control a device actuator"""
        device = self.device_manager.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        if not device.is_online:
            raise ValueError(f"Device {device_id} is offline")
        
        if actuator_type not in device.actuator_states:
            raise ValueError(f"Actuator {actuator_type} not found on device {device_id}")
        
        # This will be handled by the bridge coordinator when properly connected
        logger.info(f"Control command: {device_id}/{actuator_type} {action}={value}")
        
        return {
            "device_id": device_id,
            "actuator_type": actuator_type,
            "action": action,
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "status": "command_sent"
        }
    
    async def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific device"""
        return self.device_manager.get_device_summary(device_id)
    
    async def query_devices(self, sensor_type: Optional[str] = None,
                           actuator_type: Optional[str] = None,
                           online_only: bool = False) -> List[Dict[str, Any]]:
        """Query devices by capabilities"""
        devices = self.device_manager.get_devices_by_capability(
            sensor_type=sensor_type,
            actuator_type=actuator_type,
            online_only=online_only
        )
        
        return [
            {
                "device_id": device.device_id,
                "is_online": device.is_online,
                "matching_sensors": [s for s in device.sensor_readings.keys() 
                                   if not sensor_type or s == sensor_type],
                "matching_actuators": [a for a in device.actuator_states.keys()
                                     if not actuator_type or a == actuator_type]
            }
            for device in devices
        ]
    
    async def get_alerts(self, severity_min: int = 1, 
                        device_id: Optional[str] = None,
                        hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts and errors"""
        since = datetime.now() - timedelta(hours=hours_back)
        
        if device_id:
            events = self.database_manager.get_device_events(
                device_id, since, severity_min
            )
        else:
            # Get events for all devices
            events = []
            for device in self.device_manager.get_all_devices().values():
                device_events = self.database_manager.get_device_events(
                    device.device_id, since, severity_min
                )
                events.extend(device_events)
        
        return [
            {
                "device_id": event[1],
                "event_type": event[2], 
                "data": event[3],
                "severity": event[4],
                "timestamp": event[5].isoformat()
            }
            for event in events
        ]
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        devices = self.device_manager.get_all_devices()
        
        total_devices = len(devices)
        online_devices = sum(1 for d in devices.values() if d.is_online)
        
        # Get database stats
        db_stats = self.database_manager.get_database_stats()
        
        return {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": total_devices - online_devices,
            "database_stats": db_stats,
            "system_timestamp": datetime.now().isoformat()
        }
    
    async def get_device_metrics(self, device_id: str) -> Dict[str, Any]:
        """Get performance metrics for a specific device"""
        device = self.device_manager.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        metrics = self.device_manager.device_metrics.get(device_id)
        if not metrics:
            return {"device_id": device_id, "error": "No metrics available"}
        
        return {
            "device_id": device_id,
            "messages_sent": metrics.messages_sent,
            "messages_received": metrics.messages_received,
            "connection_failures": metrics.connection_failures,
            "sensor_read_errors": metrics.sensor_read_errors,
            "last_activity": metrics.last_activity.isoformat(),
            "uptime_seconds": metrics.uptime_seconds
        } 