"""
MCP-MQTT Bridge Server

A modular server that bridges ESP32 IoT devices (communicating via MQTT) 
with LLMs using the Model Context Protocol (MCP).
"""

__version__ = "1.0.0"
__author__ = "ESP MCP Bridge Team"

from .data_models import (
    SensorReading,
    ActuatorState, 
    DeviceCapabilities,
    IoTDevice,
    DeviceMetrics,
    BridgeConfig
)
from .mqtt_manager import MQTTManager
from .database import DatabaseManager
from .device_manager import DeviceManager
from .mcp_server import MCPServerManager
from .bridge import MCPMQTTBridge

__all__ = [
    "MCPMQTTBridge",
    "MQTTManager", 
    "DatabaseManager",
    "DeviceManager",
    "MCPServerManager",
    "SensorReading",
    "ActuatorState", 
    "DeviceCapabilities",
    "IoTDevice",
    "DeviceMetrics",
    "BridgeConfig"
] 