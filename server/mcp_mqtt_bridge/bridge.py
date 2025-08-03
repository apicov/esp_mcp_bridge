"""
Main Bridge Coordinator

Coordinates between MQTT manager, device manager, database, and MCP server
to provide a complete IoT-to-LLM bridge.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from .timezone_utils import from_timestamp_utc, utc_now, utc_timestamp, utc_isoformat

from .mqtt_manager import MQTTManager
from .database import DatabaseManager  
from .device_manager import DeviceManager
from .mcp_server import MCPServerManager
try:
    from .fastmcp_server import FastMCPServer
    FASTMCP_AVAILABLE = True
except ImportError:
    FastMCPServer = None
    FASTMCP_AVAILABLE = False
from .data_models import SensorReading, ActuatorState

logger = logging.getLogger(__name__)

class MCPMQTTBridge:
    """Main bridge coordinator class"""
    
    def __init__(self, 
                 mqtt_broker: str,
                 mqtt_port: int = 1883,
                 mqtt_username: Optional[str] = None,
                 mqtt_password: Optional[str] = None,
                 db_path: str = "bridge.db",
                 device_timeout_minutes: int = 5,
                 use_fastmcp: bool = True):
        
        # Initialize components
        self.database = DatabaseManager(db_path)
        self.device_manager = DeviceManager(device_timeout_minutes)
        self.mqtt = MQTTManager(mqtt_broker, mqtt_port, mqtt_username, mqtt_password)
        
        # Initialize MCP server (prefer FastMCP if available and requested)
        if use_fastmcp and FASTMCP_AVAILABLE:
            logger.info("Using FastMCP server implementation")
            self.mcp_server = FastMCPServer(self.device_manager, self.database)
            self.using_fastmcp = True
        else:
            if use_fastmcp and not FASTMCP_AVAILABLE:
                logger.warning("FastMCP requested but not available, falling back to standard MCP")
            self.mcp_server = MCPServerManager(self.device_manager, self.database)
            self.using_fastmcp = False
        
        # State
        self.running = False
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup event handlers between components"""
        
        # MQTT message handlers
        self.mqtt.add_message_handler("devices/+/sensors/+/data", self._handle_sensor_data)
        self.mqtt.add_message_handler("devices/+/actuators/+/status", self._handle_actuator_status)
        self.mqtt.add_message_handler("devices/+/capabilities", self._handle_device_capabilities)
        self.mqtt.add_message_handler("devices/+/status", self._handle_device_status)
        self.mqtt.add_message_handler("devices/+/error", self._handle_device_error)
        
        # Connection event handlers
        self.mqtt.add_connection_callback(self._on_mqtt_connected)
        self.mqtt.add_disconnection_callback(self._on_mqtt_disconnected)
    
    async def start(self):
        """Start the bridge"""
        if self.running:
            logger.warning("Bridge already running")
            return
        
        logger.info("Starting MCP-MQTT Bridge...")
        
        # Initialize database
        await self.database.initialize()
        
        # Connect to MQTT
        await self.mqtt.connect()
        
        # Start background tasks without blocking
        self.running = True
        self._background_tasks = []
        self._background_tasks.append(asyncio.create_task(self._device_timeout_task()))
        self._background_tasks.append(asyncio.create_task(self._metrics_task()))
        self._background_tasks.append(asyncio.create_task(self._cleanup_task()))
        
        logger.info("Bridge background tasks started")
    
    async def stop(self):
        """Stop the bridge"""
        logger.info("Stopping MCP-MQTT Bridge...")
        self.running = False
        
        # Cancel background tasks
        if hasattr(self, '_background_tasks'):
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to finish cancelling
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        await self.mqtt.disconnect()
    
    async def _device_timeout_task(self):
        """Periodically check for device timeouts"""
        while self.running:
            try:
                self.device_manager.check_device_timeouts()
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Error in device timeout task: {e}")
                await asyncio.sleep(60)
    
    async def _metrics_task(self):
        """Periodically update device metrics in database"""
        while self.running:
            try:
                for device_id, metrics in self.device_manager.device_metrics.items():
                    self.database.update_device_metrics(device_id, metrics)
                await asyncio.sleep(300)  # Update every 5 minutes
            except Exception as e:
                logger.error(f"Error in metrics task: {e}")
                await asyncio.sleep(300)
    
    async def _cleanup_task(self):
        """Periodically clean up old data"""
        while self.running:
            try:
                self.database.cleanup_old_data()
                await asyncio.sleep(86400)  # Clean up daily
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(86400)
    
    def _handle_sensor_data(self, topic: str, payload: Dict[str, Any]):
        """Handle incoming sensor data"""
        try:
            # Parse topic: devices/{device_id}/sensors/{sensor_type}/data
            parts = topic.split('/')
            if len(parts) != 5:
                logger.warning(f"Invalid sensor topic format: {topic}")
                return
            
            device_id = parts[1]
            sensor_type = parts[3]
            
            logger.debug(f"Sensor data from {device_id}/{sensor_type}: {payload}")
            
            # Update device state
            self.device_manager.update_sensor_reading(device_id, sensor_type, payload)
            
            # Store in database
            sensor_data = {
                "device_id": device_id,
                "sensor_type": sensor_type,
                "value": payload.get("value", {}).get("reading", 0),
                "unit": payload.get("value", {}).get("unit", ""),
                "timestamp": utc_isoformat(from_timestamp_utc(payload.get("timestamp", utc_timestamp())))
            }
            self.database.store_sensor_data(sensor_data)
            
        except Exception as e:
            logger.error(f"Error handling sensor data: {e}")
    
    def _handle_actuator_status(self, topic: str, payload: Dict[str, Any]):
        """Handle actuator status updates"""
        try:
            # Parse topic: devices/{device_id}/actuators/{actuator_type}/status
            parts = topic.split('/')
            if len(parts) != 5:
                logger.warning(f"Invalid actuator topic format: {topic}")
                return
            
            device_id = parts[1]
            actuator_type = parts[3]
            
            logger.debug(f"Actuator status from {device_id}/{actuator_type}: {payload}")
            
            # Update device state
            self.device_manager.update_actuator_status(device_id, actuator_type, payload)
            
            # Store in database
            state = ActuatorState(
                device_id=device_id,
                actuator_type=actuator_type,
                state=payload.get("state", "unknown"),
                timestamp=from_timestamp_utc(payload.get("timestamp", utc_timestamp()))
            )
            self.database.store_actuator_state(state)
            
        except Exception as e:
            logger.error(f"Error handling actuator status: {e}")
    
    def _handle_device_capabilities(self, topic: str, payload: Dict[str, Any]):
        """Handle device capability announcements"""
        try:
            # Parse topic: devices/{device_id}/capabilities
            parts = topic.split('/')
            if len(parts) != 3:
                logger.warning(f"Invalid capabilities topic format: {topic}")
                return
            
            device_id = parts[1]
            
            logger.info(f"Processing device capabilities from {device_id}")
            logger.debug(f"Full payload: {payload}")
            
            # Update device capabilities
            self.device_manager.update_device_capabilities(device_id, payload)
            logger.debug(f"Updated device manager for {device_id}")
            
            # Store in database
            self.database.update_device_capabilities(device_id, payload)
            logger.debug(f"Stored capabilities in database for {device_id}")
            
            # Also register the device in the main devices table
            # Convert sensor/actuator objects to simple lists
            sensors = payload.get("sensors", [])
            if sensors and isinstance(sensors[0], dict):
                sensors = [s.get("name", s.get("type", "unknown")) for s in sensors]
            
            actuators = payload.get("actuators", [])
            if actuators and isinstance(actuators[0], dict):
                actuators = [a.get("name", a.get("type", "unknown")) for a in actuators]
            
            device_data = {
                "device_id": device_id,
                "device_type": payload.get("device_type", "esp32"),
                "sensors": sensors,
                "actuators": actuators,
                "firmware_version": payload.get("firmware_version", ""),
                "location": payload.get("location", ""),
                "status": "online"
            }
            logger.debug(f"Registering device with data: {device_data}")
            self.database.register_device(device_data)
            logger.info(f"Successfully registered device {device_id} in database")
            
        except Exception as e:
            logger.error(f"Error handling device capabilities: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _handle_device_status(self, topic: str, payload: Dict[str, Any]):
        """Handle device status updates"""
        try:
            # Parse topic: devices/{device_id}/status
            parts = topic.split('/')
            if len(parts) != 3:
                logger.warning(f"Invalid status topic format: {topic}")
                return
            
            device_id = parts[1]
            status = payload.get("status", "unknown")
            
            logger.debug(f"Device status from {device_id}: {status}")
            
            # Update device online status
            self.device_manager.update_device_status(device_id, {"value": status})
            
        except Exception as e:
            logger.error(f"Error handling device status: {e}")
    
    def _handle_device_error(self, topic: str, payload: Dict[str, Any]):
        """Handle device error reports"""
        try:
            # Parse topic: devices/{device_id}/error
            parts = topic.split('/')
            if len(parts) != 3:
                logger.warning(f"Invalid error topic format: {topic}")
                return
            
            device_id = parts[1]
            
            logger.warning(f"Device error from {device_id}: {payload}")
            
            # Store error in device manager
            error_msg = payload.get("message", "Unknown error")
            self.device_manager.add_device_error(device_id, error_msg)
            
            # Store in database
            self.database.store_device_event(
                device_id=device_id,
                event_type="error",
                data=payload,
                severity=payload.get("severity", 2),
                timestamp=from_timestamp_utc(payload.get("timestamp", utc_timestamp()))
            )
            
        except Exception as e:
            logger.error(f"Error handling device error: {e}")
    
    def _on_mqtt_connected(self, reconnected: bool):
        """Handle MQTT connection established"""
        logger.info("MQTT connected successfully")
    
    def _on_mqtt_disconnected(self):
        """Handle MQTT connection lost"""
        logger.warning("MQTT connection lost")
    
    async def handle_mcp_request(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP requests"""
        return await self.mcp_server.handle_tool_call(tool_name, arguments)
    
    async def send_actuator_command(self, device_id: str, actuator_type: str, 
                                   action: str, value: Any = None) -> bool:
        """Send command to device actuator"""
        topic = f"devices/{device_id}/actuators/{actuator_type}/cmd"
        payload = {
            "action": action,
            "value": value,
            "timestamp": utc_timestamp()
        }
        
        success = await self.mqtt.publish(topic, payload)
        if success:
            # Increment sent message count
            self.device_manager.increment_sent_messages(device_id)
        
        return success
    
    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call MCP tool and return result"""
        result = await self.mcp_server.handle_tool_call(tool_name, arguments)
        
        # If the tool call was successful and involves actuator control, send the actual command
        if (result.get("success") and tool_name == "control_actuator" and 
            "device_id" in arguments and "actuator_type" in arguments):
            await self.send_actuator_command(
                arguments["device_id"],
                arguments["actuator_type"], 
                arguments["action"],
                arguments.get("value")
            )
        
        return result.get("data") if result.get("success") else result
    
    def get_fastmcp_server(self):
        """Get the FastMCP server instance for direct stdio serving"""
        if self.using_fastmcp and hasattr(self.mcp_server, 'get_server'):
            return self.mcp_server.get_server()
        return None
    
    async def serve_mcp_stdio(self):
        """Serve MCP over stdio (for FastMCP clients)"""
        if self.using_fastmcp and hasattr(self.mcp_server, 'serve_stdio'):
            await self.mcp_server.serve_stdio()
        else:
            raise RuntimeError("FastMCP not available or not in use") 