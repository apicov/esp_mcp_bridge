#!/usr/bin/env python3
"""
MCP-MQTT Bridge Server

This server bridges ESP32 IoT devices (communicating via MQTT) with LLMs using
the Model Context Protocol (MCP). It provides tools for device discovery,
sensor reading, actuator control, and real-time monitoring.
"""

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path
import signal
import sys

import paho.mqtt.client as mqtt
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Tool, 
    TextContent, 
    ImageContent, 
    EmbeddedResource,
    CallToolResult,
    ListToolsResult
)
from mcp.server.stdio import stdio_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== DATA MODELS ====================

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

# ==================== DATABASE MANAGER ====================

class DatabaseManager:
    """Manages persistent storage of device data"""
    
    def __init__(self, db_path: str = "iot_bridge.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database schema"""
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
                    INDEX idx_device_sensor (device_id, sensor_type),
                    INDEX idx_timestamp (timestamp)
                );
                
                CREATE TABLE IF NOT EXISTS actuator_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    actuator_type TEXT NOT NULL,
                    state TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    INDEX idx_device_actuator (device_id, actuator_type)
                );
                
                CREATE TABLE IF NOT EXISTS device_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    data TEXT,
                    timestamp DATETIME NOT NULL,
                    INDEX idx_device_event (device_id, event_type)
                );
            """)
    
    def store_sensor_reading(self, reading: SensorReading):
        """Store a sensor reading"""
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
    
    def get_sensor_history(self, device_id: str, sensor_type: str, 
                          duration_minutes: int = 60) -> List[Dict[str, Any]]:
        """Get historical sensor data"""
        since = datetime.now() - timedelta(minutes=duration_minutes)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM sensor_readings
                WHERE device_id = ? AND sensor_type = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (device_id, sensor_type, since))
            
            return [dict(row) for row in cursor.fetchall()]

# ==================== MQTT MANAGER ====================

class MQTTManager:
    """Manages MQTT client and message handling"""
    
    def __init__(self, broker: str, port: int = 1883, 
                 username: Optional[str] = None, 
                 password: Optional[str] = None):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(client_id="mcp_bridge_server")
        
        if username and password:
            self.client.username_pw_set(username, password)
        
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        self.message_handlers: Dict[str, Callable] = {}
        self.connected = False
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            self.connected = True
            
            # Subscribe to all device topics
            subscriptions = [
                ("devices/+/capabilities", 1),
                ("devices/+/sensors/+/data", 0),
                ("devices/+/actuators/+/status", 1),
                ("devices/+/status", 1),
                ("devices/+/error", 1)
            ]
            
            for topic, qos in subscriptions:
                client.subscribe(topic, qos)
                logger.info(f"Subscribed to {topic}")
        else:
            logger.error(f"Connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker (code: {rc})")
        
        if rc != 0:
            logger.info("Unexpected disconnection, will auto-reconnect")
    
    def _on_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            # Route to appropriate handler based on topic pattern
            topic_parts = topic.split('/')
            
            if len(topic_parts) >= 3:
                device_id = topic_parts[1]
                message_type = topic_parts[2]
                
                handler_key = f"{message_type}"
                if len(topic_parts) > 3:
                    handler_key = f"{message_type}/{topic_parts[3]}"
                
                if handler_key in self.message_handlers:
                    self.message_handlers[handler_key](device_id, topic_parts, payload)
                else:
                    logger.debug(f"No handler for topic pattern: {handler_key}")
                    
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in message from {msg.topic}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def register_handler(self, pattern: str, handler: Callable):
        """Register a message handler for a topic pattern"""
        self.message_handlers[pattern] = handler
    
    def publish(self, topic: str, payload: Dict[str, Any], qos: int = 0, retain: bool = False):
        """Publish a message to MQTT"""
        if not self.connected:
            logger.warning("Cannot publish - not connected to broker")
            return False
        
        try:
            json_payload = json.dumps(payload)
            result = self.client.publish(topic, json_payload, qos, retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published to {topic}")
                return True
            else:
                logger.error(f"Failed to publish to {topic}: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False

# ==================== MCP-MQTT BRIDGE ====================

class MCPMQTTBridge:
    """Main bridge between MQTT IoT devices and MCP"""
    
    def __init__(self, mqtt_broker: str, mqtt_port: int = 1883,
                 mqtt_username: Optional[str] = None,
                 mqtt_password: Optional[str] = None,
                 db_path: str = "iot_bridge.db"):
        
        # Initialize components
        self.devices: Dict[str, IoTDevice] = {}
        self.db = DatabaseManager(db_path)
        self.mqtt = MQTTManager(mqtt_broker, mqtt_port, mqtt_username, mqtt_password)
        self.mcp_server = Server("iot-bridge")
        
        # Setup MQTT handlers
        self._setup_mqtt_handlers()
        
        # Setup MCP tools
        self._setup_mcp_tools()
        
        # Start periodic tasks
        self.tasks: List[asyncio.Task] = []
    
    def _setup_mqtt_handlers(self):
        """Setup MQTT message handlers"""
        self.mqtt.register_handler("capabilities", self._handle_capabilities)
        self.mqtt.register_handler("sensors", self._handle_sensor_data)
        self.mqtt.register_handler("actuators", self._handle_actuator_status)
        self.mqtt.register_handler("status", self._handle_device_status)
        self.mqtt.register_handler("error", self._handle_device_error)
    
    def _setup_mcp_tools(self):
        """Define MCP tools for IoT interaction"""
        
        @self.mcp_server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="list_devices",
                    description="List all connected IoT devices and their capabilities",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "online_only": {
                                "type": "boolean",
                                "description": "Only show online devices",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="read_sensor",
                    description="Read current or historical sensor data from a device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Device identifier"
                            },
                            "sensor_type": {
                                "type": "string",
                                "description": "Sensor type (e.g., temperature, humidity)"
                            },
                            "history_minutes": {
                                "type": "integer",
                                "description": "Minutes of history to retrieve (0 for current only)",
                                "default": 0
                            }
                        },
                        "required": ["device_id", "sensor_type"]
                    }
                ),
                Tool(
                    name="control_actuator",
                    description="Control an actuator on a device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Device identifier"
                            },
                            "actuator_type": {
                                "type": "string",
                                "description": "Actuator type (e.g., led, relay)"
                            },
                            "action": {
                                "type": "string",
                                "enum": ["read", "write", "toggle"],
                                "description": "Action to perform"
                            },
                            "value": {
                                "description": "Value for write action",
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "number"},
                                    {"type": "boolean"},
                                    {"type": "null"}
                                ]
                            }
                        },
                        "required": ["device_id", "actuator_type", "action"]
                    }
                ),
                Tool(
                    name="get_device_info",
                    description="Get detailed information about a specific device",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Device identifier"
                            }
                        },
                        "required": ["device_id"]
                    }
                ),
                Tool(
                    name="query_devices",
                    description="Query devices based on capabilities or status",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "sensor_type": {
                                "type": "string",
                                "description": "Filter by sensor type"
                            },
                            "actuator_type": {
                                "type": "string",
                                "description": "Filter by actuator type"
                            },
                            "online_only": {
                                "type": "boolean",
                                "description": "Only include online devices",
                                "default": True
                            }
                        }
                    }
                ),
                Tool(
                    name="get_alerts",
                    description="Get recent device errors and alerts",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {
                                "type": "string",
                                "description": "Filter by device (optional)"
                            },
                            "severity_min": {
                                "type": "integer",
                                "description": "Minimum severity (0-3)",
                                "default": 0
                            }
                        }
                    }
                )
            ]
        
        @self.mcp_server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            logger.info(f"MCP tool called: {name} with args: {arguments}")
            
            try:
                if name == "list_devices":
                    return await self._handle_list_devices(arguments)
                elif name == "read_sensor":
                    return await self._handle_read_sensor(arguments)
                elif name == "control_actuator":
                    return await self._handle_control_actuator(arguments)
                elif name == "get_device_info":
                    return await self._handle_get_device_info(arguments)
                elif name == "query_devices":
                    return await self._handle_query_devices(arguments)
                elif name == "get_alerts":
                    return await self._handle_get_alerts(arguments)
                else:
                    return [TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )]
            except Exception as e:
                logger.error(f"Error handling tool {name}: {e}")
                return [TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )]
    
    # ==================== MQTT HANDLERS ====================
    
    def _handle_capabilities(self, device_id: str, topic_parts: List[str], payload: Dict[str, Any]):
        """Handle device capabilities message"""
        logger.info(f"Received capabilities from {device_id}")
        
        if device_id not in self.devices:
            self.devices[device_id] = IoTDevice(device_id=device_id)
        
        device = self.devices[device_id]
        device.capabilities.sensors = payload.get("sensors", [])
        device.capabilities.actuators = payload.get("actuators", [])
        device.capabilities.metadata = payload.get("metadata", {})
        device.capabilities.firmware_version = payload.get("firmware_version")
        device.capabilities.hardware_version = payload.get("hardware_version")
        device.last_seen = datetime.now()
    
    def _handle_sensor_data(self, device_id: str, topic_parts: List[str], payload: Dict[str, Any]):
        """Handle sensor data message"""
        if len(topic_parts) < 5:
            return
        
        sensor_type = topic_parts[3]
        
        # Extract value
        value_data = payload.get("value", {})
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
            timestamp=datetime.fromtimestamp(payload.get("timestamp", datetime.now().timestamp()))
        )
        
        # Update device
        if device_id not in self.devices:
            self.devices[device_id] = IoTDevice(device_id=device_id)
        
        self.devices[device_id].sensor_readings[sensor_type] = reading
        self.devices[device_id].last_seen = datetime.now()
        
        # Store in database
        self.db.store_sensor_reading(reading)
        
        logger.debug(f"Sensor data from {device_id}/{sensor_type}: {reading_value} {unit or ''}")
    
    def _handle_actuator_status(self, device_id: str, topic_parts: List[str], payload: Dict[str, Any]):
        """Handle actuator status message"""
        if len(topic_parts) < 5:
            return
        
        actuator_type = topic_parts[3]
        state = payload.get("value", "unknown")
        
        # Create state record
        actuator_state = ActuatorState(
            device_id=device_id,
            actuator_type=actuator_type,
            state=state,
            timestamp=datetime.fromtimestamp(payload.get("timestamp", datetime.now().timestamp()))
        )
        
        # Update device
        if device_id not in self.devices:
            self.devices[device_id] = IoTDevice(device_id=device_id)
        
        self.devices[device_id].actuator_states[actuator_type] = actuator_state
        self.devices[device_id].last_seen = datetime.now()
        
        logger.info(f"Actuator status from {device_id}/{actuator_type}: {state}")
    
    def _handle_device_status(self, device_id: str, topic_parts: List[str], payload: Dict[str, Any]):
        """Handle device status message"""
        status = payload.get("value", "unknown")
        
        if device_id not in self.devices:
            self.devices[device_id] = IoTDevice(device_id=device_id)
        
        self.devices[device_id].online = (status == "online")
        self.devices[device_id].last_seen = datetime.now()
        
        logger.info(f"Device {device_id} is {status}")
    
    def _handle_device_error(self, device_id: str, topic_parts: List[str], payload: Dict[str, Any]):
        """Handle device error message"""
        error_data = {
            "error_type": payload.get("value", {}).get("error_type", "unknown"),
            "message": payload.get("value", {}).get("message", ""),
            "severity": payload.get("value", {}).get("severity", 2),
            "timestamp": datetime.fromtimestamp(payload.get("timestamp", datetime.now().timestamp()))
        }
        
        if device_id not in self.devices:
            self.devices[device_id] = IoTDevice(device_id=device_id)
        
        self.devices[device_id].errors.append(error_data)
        
        # Keep only last 100 errors per device
        if len(self.devices[device_id].errors) > 100:
            self.devices[device_id].errors = self.devices[device_id].errors[-100:]
        
        logger.warning(f"Error from {device_id}: {error_data['error_type']} - {error_data['message']}")
    
    # ==================== MCP TOOL HANDLERS ====================
    
    async def _handle_list_devices(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """List all devices"""
        online_only = arguments.get("online_only", False)
        
        devices_list = []
        for device_id, device in self.devices.items():
            if online_only and not device.online:
                continue
            
            device_info = {
                "device_id": device_id,
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
            devices_list.append(device_info)
        
        return [TextContent(
            type="text",
            text=json.dumps(devices_list, indent=2)
        )]
    
    async def _handle_read_sensor(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Read sensor data"""
        device_id = arguments["device_id"]
        sensor_type = arguments["sensor_type"]
        history_minutes = arguments.get("history_minutes", 0)
        
        if device_id not in self.devices:
            return [TextContent(type="text", text=f"Device {device_id} not found")]
        
        device = self.devices[device_id]
        
        # Current reading
        if sensor_type in device.sensor_readings:
            current = device.sensor_readings[sensor_type]
            result = {
                "device_id": device_id,
                "sensor": sensor_type,
                "current": {
                    "value": current.value,
                    "unit": current.unit,
                    "quality": current.quality,
                    "timestamp": current.timestamp.isoformat()
                }
            }
        else:
            result = {
                "device_id": device_id,
                "sensor": sensor_type,
                "current": None,
                "error": "No current reading available"
            }
        
        # Historical data if requested
        if history_minutes > 0:
            history = self.db.get_sensor_history(device_id, sensor_type, history_minutes)
            result["history"] = history
            result["history_count"] = len(history)
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
    
    async def _handle_control_actuator(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Control an actuator"""
        device_id = arguments["device_id"]
        actuator_type = arguments["actuator_type"]
        action = arguments["action"]
        value = arguments.get("value")
        
        if device_id not in self.devices:
            return [TextContent(type="text", text=f"Device {device_id} not found")]
        
        device = self.devices[device_id]
        
        if actuator_type not in device.capabilities.actuators:
            return [TextContent(
                type="text",
                text=f"Device {device_id} does not have actuator {actuator_type}"
            )]
        
        # Publish MQTT command
        topic = f"devices/{device_id}/actuators/{actuator_type}/cmd"
        payload = {
            "action": action,
            "value": value,
            "timestamp": int(datetime.now().timestamp())
        }
        
        success = self.mqtt.publish(topic, payload, qos=1)
        
        if success:
            result = {
                "status": "success",
                "device_id": device_id,
                "actuator": actuator_type,
                "command": f"{action} = {value}" if value is not None else action,
                "topic": topic
            }
        else:
            result = {
                "status": "error",
                "message": "Failed to send command",
                "device_id": device_id,
                "actuator": actuator_type
            }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    async def _handle_get_device_info(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Get detailed device information"""
        device_id = arguments["device_id"]
        
        if device_id not in self.devices:
            return [TextContent(type="text", text=f"Device {device_id} not found")]
        
        device = self.devices[device_id]
        
        info = {
            "device_id": device_id,
            "online": device.online,
            "last_seen": device.last_seen.isoformat(),
            "uptime": "unknown",  # Could calculate from metrics
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
            "recent_errors": device.errors[-10:] if device.errors else []
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(info, indent=2, default=str)
        )]
    
    async def _handle_query_devices(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Query devices by capability"""
        sensor_type = arguments.get("sensor_type")
        actuator_type = arguments.get("actuator_type")
        online_only = arguments.get("online_only", True)
        
        matching_devices = []
        
        for device_id, device in self.devices.items():
            if online_only and not device.online:
                continue
            
            if sensor_type and sensor_type not in device.capabilities.sensors:
                continue
            
            if actuator_type and actuator_type not in device.capabilities.actuators:
                continue
            
            device_summary = {
                "device_id": device_id,
                "online": device.online,
                "last_seen": device.last_seen.isoformat()
            }
            
            if sensor_type and sensor_type in device.sensor_readings:
                reading = device.sensor_readings[sensor_type]
                device_summary[f"{sensor_type}_value"] = reading.value
                device_summary[f"{sensor_type}_unit"] = reading.unit
            
            if actuator_type and actuator_type in device.actuator_states:
                device_summary[f"{actuator_type}_state"] = device.actuator_states[actuator_type].state
            
            matching_devices.append(device_summary)
        
        result = {
            "query": {
                "sensor_type": sensor_type,
                "actuator_type": actuator_type,
                "online_only": online_only
            },
            "count": len(matching_devices),
            "devices": matching_devices
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    async def _handle_get_alerts(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Get device alerts and errors"""
        device_id = arguments.get("device_id")
        severity_min = arguments.get("severity_min", 0)
        
        alerts = []
        
        for dev_id, device in self.devices.items():
            if device_id and dev_id != device_id:
                continue
            
            for error in device.errors:
                if error.get("severity", 2) >= severity_min:
                    alerts.append({
                        "device_id": dev_id,
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
        alerts = alerts[:50]
        
        result = {
            "filter": {
                "device_id": device_id,
                "severity_min": severity_min
            },
            "count": len(alerts),
            "alerts": alerts
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
    
    # ==================== LIFECYCLE MANAGEMENT ====================
    
    async def start(self):
        """Start the bridge server"""
        logger.info("Starting MCP-MQTT Bridge...")
        
        # Connect to MQTT
        self.mqtt.connect()
        
        # Start background tasks
        self.tasks.append(asyncio.create_task(self._device_monitor_task()))
        self.tasks.append(asyncio.create_task(self._cleanup_task()))
        
        logger.info("MCP-MQTT Bridge started successfully")
    
    async def stop(self):
        """Stop the bridge server"""
        logger.info("Stopping MCP-MQTT Bridge...")
        
        # Cancel background tasks
        for task in self.tasks:
            task.cancel()
        
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Disconnect MQTT
        self.mqtt.disconnect()
        
        logger.info("MCP-MQTT Bridge stopped")
    
    async def _device_monitor_task(self):
        """Monitor device online/offline status"""
        while True:
            try:
                current_time = datetime.now()
                
                for device_id, device in self.devices.items():
                    # Mark devices offline if not seen for 5 minutes
                    if device.online and (current_time - device.last_seen).total_seconds() > 300:
                        device.online = False
                        logger.warning(f"Device {device_id} marked offline (no data for 5 minutes)")
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in device monitor task: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_task(self):
        """Clean up old data periodically"""
        while True:
            try:
                # Clean up old errors (keep last 7 days)
                cutoff_time = datetime.now() - timedelta(days=7)
                
                for device in self.devices.values():
                    device.errors = [
                        error for error in device.errors
                        if error.get("timestamp", datetime.now()) > cutoff_time
                    ]
                
                await asyncio.sleep(3600)  # Run hourly
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(3600)
    
    async def run(self):
        """Run the MCP server"""
        await self.start()
        
        try:
            # Run MCP server
            async with stdio_server() as (read_stream, write_stream):
                await self.mcp_server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="iot-bridge",
                        server_version="1.0.0",
                        capabilities={}
                    )
                )
        finally:
            await self.stop()

# ==================== MAIN ENTRY POINT ====================

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP-MQTT Bridge Server")
    parser.add_argument("--mqtt-broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--mqtt-port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--mqtt-username", help="MQTT username")
    parser.add_argument("--mqtt-password", help="MQTT password")
    parser.add_argument("--db-path", default="iot_bridge.db", help="Database file path")
    parser.add_argument("--log-level", default="INFO", 
                       choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                       help="Logging level")
    
    args = parser.parse_args()
    
    # Configure logging
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Create and run bridge
    bridge = MCPMQTTBridge(
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password,
        db_path=args.db_path
    )
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        asyncio.create_task(bridge.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await bridge.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
