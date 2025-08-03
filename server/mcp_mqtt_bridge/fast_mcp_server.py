"""
MCP Server using FastMCP Framework

Provides a proper MCP server that can run over HTTP/SSE for remote connections.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from mcp.server.fastmcp import FastMCP
from mcp import McpError

logger = logging.getLogger(__name__)


def create_mcp_server(bridge) -> FastMCP:
    """Create a FastMCP server instance with IoT device tools"""
    
    # Create FastMCP app
    app = FastMCP("IoT MCP Bridge")
    
    @app.tool()
    async def list_devices(online_only: bool = False) -> str:
        """List all connected IoT devices
        
        Args:
            online_only: Only show devices that are currently online
            
        Returns:
            List of devices with their capabilities
        """
        try:
            result = await bridge.call_mcp_tool("list_devices", {"online_only": online_only})
            return str(result)
        except Exception as e:
            logger.error(f"Error in list_devices: {e}")
            raise McpError("INTERNAL_ERROR", str(e))
    
    @app.tool()
    async def read_sensor(device_id: str, sensor_type: str, history_minutes: int = 60) -> str:
        """Read sensor data from a specific device
        
        Args:
            device_id: ID of the device to read from
            sensor_type: Type of sensor (temperature, humidity, pressure, etc.)
            history_minutes: Minutes of historical data to include
            
        Returns:
            Latest sensor reading with value and timestamp
        """
        try:
            result = await bridge.call_mcp_tool("read_sensor", {
                "device_id": device_id,
                "sensor_type": sensor_type,
                "history_minutes": history_minutes
            })
            return str(result)
        except Exception as e:
            logger.error(f"Error in read_sensor: {e}")
            raise McpError("INTERNAL_ERROR", str(e))
    
    @app.tool()
    async def control_actuator(device_id: str, actuator_type: str, action: str) -> str:
        """Control device actuators (LEDs, relays, motors, etc.)
        
        Args:
            device_id: ID of the device to control
            actuator_type: Type of actuator (led, relay, motor, etc.)
            action: Action to perform (on, off, toggle, set_value, etc.)
            
        Returns:
            Confirmation of command sent to device
        """
        try:
            result = await bridge.call_mcp_tool("control_actuator", {
                "device_id": device_id,
                "actuator_type": actuator_type,
                "action": action
            })
            return str(result)
        except Exception as e:
            logger.error(f"Error in control_actuator: {e}")
            raise McpError("INTERNAL_ERROR", str(e))
    
    @app.tool()
    async def get_device_info(device_id: str) -> str:
        """Get detailed information about a specific device
        
        Args:
            device_id: ID of the device to get info for
            
        Returns:
            Device information including capabilities, status, and metadata
        """
        try:
            result = await bridge.call_mcp_tool("get_device_info", {"device_id": device_id})
            return str(result)
        except Exception as e:
            logger.error(f"Error in get_device_info: {e}")
            raise McpError("INTERNAL_ERROR", str(e))
    
    @app.tool()
    async def query_devices(sensor_type: Optional[str] = None, actuator_type: Optional[str] = None, 
                          location: Optional[str] = None, online_only: bool = True) -> str:
        """Search for devices by capabilities or location
        
        Args:
            sensor_type: Filter by sensor type (temperature, humidity, etc.)
            actuator_type: Filter by actuator type (led, relay, etc.)
            location: Filter by device location
            online_only: Only include online devices
            
        Returns:
            List of matching devices
        """
        try:
            result = await bridge.call_mcp_tool("query_devices", {
                "sensor_type": sensor_type,
                "actuator_type": actuator_type,
                "location": location,
                "online_only": online_only
            })
            return str(result)
        except Exception as e:
            logger.error(f"Error in query_devices: {e}")
            raise McpError("INTERNAL_ERROR", str(e))
    
    @app.tool()
    async def get_alerts(severity_min: int = 1, device_id: Optional[str] = None, 
                        hours_back: int = 24) -> str:
        """Get recent errors and alerts from devices
        
        Args:
            severity_min: Minimum severity level (1=info, 2=warning, 3=error, 4=critical)
            device_id: Filter by specific device (optional)
            hours_back: Hours of history to check
            
        Returns:
            List of recent alerts and errors
        """
        try:
            result = await bridge.call_mcp_tool("get_alerts", {
                "severity_min": severity_min,
                "device_id": device_id,
                "hours_back": hours_back
            })
            return str(result)
        except Exception as e:
            logger.error(f"Error in get_alerts: {e}")
            raise McpError("INTERNAL_ERROR", str(e))
    
    @app.tool()
    async def read_all_sensors(device_ids: Optional[List[str]] = None, 
                             sensor_types: Optional[List[str]] = None) -> str:
        """Read all sensors from multiple devices efficiently
        
        Args:
            device_ids: List of device IDs to read from (empty for all devices)
            sensor_types: List of sensor types to read (empty for all sensors)
            
        Returns:
            Complete sensor readings from all specified devices
        """
        try:
            result = await bridge.call_mcp_tool("read_all_sensors", {
                "device_ids": device_ids or [],
                "sensor_types": sensor_types or []
            })
            return str(result)
        except Exception as e:
            logger.error(f"Error in read_all_sensors: {e}")
            raise McpError("INTERNAL_ERROR", str(e))
    
    @app.tool()
    async def read_device_sensors(device_id: str) -> str:
        """Read all sensors from a specific device
        
        Args:
            device_id: Device ID to read all sensors from
            
        Returns:
            All sensor readings from the specified device
        """
        try:
            result = await bridge.call_mcp_tool("read_device_sensors", {"device_id": device_id})
            return str(result)
        except Exception as e:
            logger.error(f"Error in read_device_sensors: {e}")
            raise McpError("INTERNAL_ERROR", str(e))
    
    return app


async def run_mcp_server(bridge, host: str = "0.0.0.0", port: int = 8000):
    """Run the MCP server with HTTP/SSE transport"""
    
    app = create_mcp_server(bridge)
    
    logger.info(f"Starting MCP server on http://{host}:{port}")
    logger.info("Available endpoints:")
    logger.info(f"  - SSE: http://{host}:{port}/sse")
    
    # Use uvicorn to run the FastMCP SSE app
    import uvicorn
    
    # Get the ASGI app from FastMCP
    asgi_app = app.sse_app()
    
    config = uvicorn.Config(
        app=asgi_app,
        host=host,
        port=port,
        log_level="info"
    )
    
    server = uvicorn.Server(config)
    await server.serve()