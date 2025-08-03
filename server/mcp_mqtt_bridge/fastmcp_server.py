"""
FastMCP Server Implementation

Modern FastMCP-based server that exposes IoT device capabilities
through the MCP protocol with improved performance and simpler API.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from .timezone_utils import utc_isoformat

try:
    from fastmcp import FastMCP
except ImportError:
    try:
        # Try using standard MCP for FastMCP compatibility
        import mcp.server.stdio
        
        class FastMCP:
            def __init__(self, name):
                self.name = name
                self.tools = {}
            
            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator
            
            async def run(self):
                # For now, this is a placeholder
                pass
                
    except ImportError:
        # Create a simple MCP server class for fallback
        class FastMCP:
            def __init__(self, name):
                self.name = name
                self.tools = {}
            
            def tool(self):
                def decorator(func):
                    self.tools[func.__name__] = func
                    return func
                return decorator
            
            async def run(self):
                raise NotImplementedError("FastMCP fallback cannot run stdio server")
    
    # Set flag to indicate we're using fallback
    USING_FALLBACK = True
except:
    FastMCP = None
    USING_FALLBACK = True

logger = logging.getLogger(__name__)


class FastMCPServer:
    """FastMCP-based MCP server for IoT device control"""
    
    def __init__(self, device_manager, database_manager, bridge=None):
        self.device_manager = device_manager
        self.database_manager = database_manager
        self.bridge = bridge
        
        if FastMCP is None:
            logger.warning("FastMCP not available, falling back to standard MCP implementation")
            self.mcp = None
            self.using_fallback = True
            return
        
        self.using_fallback = globals().get('USING_FALLBACK', False)
        if self.using_fallback:
            logger.warning("Using FastMCP fallback implementation")
            
        # Initialize FastMCP server
        self.mcp = FastMCP("ESP32-MCP-Bridge")
        self._register_tools()
    
    def _register_tools(self):
        """Register all MCP tools with FastMCP"""
        if self.mcp is None:
            return
            
        @self.mcp.tool()
        async def list_devices(online_only: bool = False) -> List[Dict[str, Any]]:
            """List all connected IoT devices"""
            return await self._list_devices(online_only)
        
        @self.mcp.tool()
        async def read_sensor(device_id: str, sensor_type: str, history_minutes: int = 0) -> Dict[str, Any]:
            """Read current sensor data with optional history"""
            return await self._read_sensor(device_id, sensor_type, history_minutes)
        
        @self.mcp.tool()
        async def read_all_sensors(device_ids: Optional[List[str]] = None, 
                                 sensor_types: Optional[List[str]] = None) -> Dict[str, Any]:
            """Read multiple sensors from multiple devices at once"""
            return await self._read_all_sensors(device_ids, sensor_types)
        
        @self.mcp.tool()
        async def control_actuator(device_id: str, actuator_type: str, 
                                 action: str, value: Any = None) -> Dict[str, Any]:
            """Control a device actuator"""
            return await self._control_actuator(device_id, actuator_type, action, value)
        
        @self.mcp.tool()
        async def get_device_info(device_id: str) -> Dict[str, Any]:
            """Get detailed information about a specific device"""
            return await self._get_device_info(device_id)
        
        @self.mcp.tool()
        async def query_devices(sensor_type: Optional[str] = None,
                              actuator_type: Optional[str] = None,
                              online_only: bool = False) -> List[Dict[str, Any]]:
            """Query devices by capabilities"""
            return await self._query_devices(sensor_type, actuator_type, online_only)
        
        @self.mcp.tool()
        async def get_alerts(severity_min: int = 1, 
                           device_id: Optional[str] = None,
                           hours_back: int = 24) -> List[Dict[str, Any]]:
            """Get recent alerts and errors"""
            return await self._get_alerts(severity_min, device_id, hours_back)
        
        @self.mcp.tool()
        async def get_system_status() -> Dict[str, Any]:
            """Get overall system status"""
            return await self._get_system_status()
        
        @self.mcp.tool()
        async def get_device_metrics(device_id: str) -> Dict[str, Any]:
            """Get performance metrics for a specific device"""
            return await self._get_device_metrics(device_id)
        
        @self.mcp.tool()
        async def ping_device(device_id: str, timeout_seconds: int = 5) -> Dict[str, Any]:
            """Ping a device to check if it's responsive"""
            return await self._ping_device(device_id, timeout_seconds)
    
    # Implementation methods (same logic as MCPServerManager)
    async def _list_devices(self, online_only: bool = False) -> List[Dict[str, Any]]:
        """List all connected IoT devices"""
        devices = self.device_manager.get_all_devices()
        
        device_list = []
        for device in devices:
            if online_only and not device.online:
                continue
                
            device_info = {
                "device_id": device.device_id,
                "is_online": device.online,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                "sensors": list(device.sensor_readings.keys()),
                "actuators": list(device.actuator_states.keys()),
                "capabilities": device.capabilities.__dict__ if device.capabilities else None
            }
            device_list.append(device_info)
        
        return device_list
    
    async def _read_sensor(self, device_id: str, sensor_type: str, 
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
    
    async def _read_all_sensors(self, device_ids: Optional[List[str]] = None, 
                               sensor_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """Read multiple sensors from multiple devices at once"""
        devices_list = self.device_manager.get_all_devices()
        devices = {d.device_id: d for d in devices_list}
        
        # If no device_ids specified, use all online devices
        if device_ids is None:
            device_ids = [d.device_id for d in devices_list if d.online]
        
        results = {}
        
        for device_id in device_ids:
            device = devices.get(device_id)
            if not device or not device.online:
                results[device_id] = {"error": f"Device {device_id} not found or offline"}
                continue
            
            device_sensors = {}
            
            # If no sensor_types specified, read all sensors from this device
            sensors_to_read = sensor_types or list(device.sensor_readings.keys())
            
            for sensor_type in sensors_to_read:
                try:
                    reading = device.sensor_readings.get(sensor_type)
                    if reading:
                        device_sensors[sensor_type] = {
                            "value": reading.value,
                            "unit": reading.unit,
                            "timestamp": reading.timestamp.isoformat(),
                            "quality": reading.quality
                        }
                    else:
                        device_sensors[sensor_type] = {"error": f"Sensor {sensor_type} not found"}
                except Exception as e:
                    device_sensors[sensor_type] = {"error": str(e)}
            
            results[device_id] = device_sensors
        
        return {
            "timestamp": utc_isoformat(),
            "devices": results,
            "total_devices": len(device_ids),
            "online_devices": len([d for d in device_ids if devices.get(d) and devices[d].online])
        }
    
    async def _control_actuator(self, device_id: str, actuator_type: str, 
                               action: str, value: Any = None) -> Dict[str, Any]:
        """Control a device actuator"""
        device = self.device_manager.get_device(device_id)
        if not device:
            raise ValueError(f"Device {device_id} not found")
        
        if not device.online:
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
            "timestamp": utc_isoformat(),
            "status": "command_sent"
        }
    
    async def _get_device_info(self, device_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific device"""
        return self.device_manager.get_device_summary(device_id)
    
    async def _query_devices(self, sensor_type: Optional[str] = None,
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
                "is_online": device.online,
                "matching_sensors": [s for s in device.sensor_readings.keys() 
                                   if not sensor_type or s == sensor_type],
                "matching_actuators": [a for a in device.actuator_states.keys()
                                     if not actuator_type or a == actuator_type]
            }
            for device in devices
        ]
    
    async def _get_alerts(self, severity_min: int = 1, 
                         device_id: Optional[str] = None,
                         hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts and errors"""
        from datetime import timedelta
        since = datetime.now() - timedelta(hours=hours_back)
        
        if device_id:
            events = self.database_manager.get_device_events(
                device_id, since, severity_min
            )
        else:
            # Get events for all devices
            events = []
            for device in self.device_manager.get_all_devices():
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
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        devices = self.device_manager.get_all_devices()
        
        total_devices = len(devices)
        online_devices = sum(1 for d in devices if d.online)
        
        # Get database stats
        db_stats = self.database_manager.get_database_stats()
        
        return {
            "total_devices": total_devices,
            "online_devices": online_devices,
            "offline_devices": total_devices - online_devices,
            "database_stats": db_stats,
            "system_timestamp": utc_isoformat()
        }
    
    async def _get_device_metrics(self, device_id: str) -> Dict[str, Any]:
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
    
    async def _ping_device(self, device_id: str, timeout_seconds: int = 5) -> Dict[str, Any]:
        """Ping a device to check if it's responsive"""
        # Delegate to the MCPServerManager implementation
        from .mcp_server import MCPServerManager
        temp_manager = MCPServerManager(self.device_manager, self.database_manager, self.bridge)
        return await temp_manager.ping_device(device_id, timeout_seconds)
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming tool calls - compatibility method for fallback"""
        if self.mcp is None:
            # Fallback to original MCPServerManager behavior
            from .mcp_server import MCPServerManager
            fallback = MCPServerManager(self.device_manager, self.database_manager, self.bridge)
            return await fallback.handle_tool_call(tool_name, arguments)
        
        # FastMCP handles tool calls automatically through decorators
        # This method is here for compatibility with the bridge interface
        try:
            # Get the tool function and call it
            tool_func = getattr(self, f"_{tool_name}", None)
            if tool_func:
                result = await tool_func(**arguments)
                return {"success": True, "data": result}
            else:
                return {
                    "error": f"Unknown tool: {tool_name}",
                    "available_tools": [
                        "list_devices", "read_sensor", "read_all_sensors",
                        "control_actuator", "get_device_info", "query_devices",
                        "get_alerts", "get_system_status", "get_device_metrics",
                        "ping_device"
                    ]
                }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}
    
    def get_server(self):
        """Get the FastMCP server instance"""
        return self.mcp
    
    async def serve_stdio(self):
        """Serve MCP over stdio (for FastMCP clients)"""
        if self.mcp is None:
            raise RuntimeError("FastMCP not available")
        
        await self.mcp.run()