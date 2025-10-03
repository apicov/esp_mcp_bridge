"""
MCP HTTP Server Module

Provides HTTP transport for the MCP bridge, allowing remote clients to connect
and control IoT devices through the MCP protocol over HTTP.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from aiohttp import web, WSMsgType
import aiohttp_cors

logger = logging.getLogger(__name__)


class MCPHTTPServer:
    """HTTP server that exposes MCP bridge functionality via HTTP/WebSocket"""
    
    def __init__(self, bridge, host: str = "0.0.0.0", port: int = 8000):
        self.bridge = bridge
        self.host = host
        self.port = port
        self.app = web.Application()
        self.websockets = set()
        self._setup_routes()
        self._setup_cors()
    
    def _setup_cors(self):
        """Setup CORS for cross-origin requests"""
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    def _setup_routes(self):
        """Setup HTTP routes"""
        # Health check
        self.app.router.add_get("/health", self.health_check)
        
        # MCP tool endpoints
        self.app.router.add_get("/tools", self.list_tools)
        self.app.router.add_post("/tools/{tool_name}", self.call_tool)
        
        # WebSocket endpoint for real-time MCP communication
        self.app.router.add_get("/mcp", self.websocket_handler)
        
        # Device endpoints for easy REST access
        self.app.router.add_get("/devices", self.get_devices)
        self.app.router.add_get("/devices/{device_id}", self.get_device_info)
        self.app.router.add_get("/devices/{device_id}/sensors/{sensor_type}", self.get_sensor_data)
        self.app.router.add_post("/devices/{device_id}/actuators/{actuator_type}", self.control_actuator)
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "service": "mcp-mqtt-bridge",
            "version": "1.0.0"
        })
    
    async def list_tools(self, request):
        """List available MCP tools"""
        tools = [
            {
                "name": "list_devices",
                "description": "List all connected IoT devices",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "online_only": {"type": "boolean", "description": "Only show online devices"}
                    }
                }
            },
            {
                "name": "read_sensor",
                "description": "Read sensor data from a device",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device ID"},
                        "sensor_type": {"type": "string", "description": "Sensor type"},
                        "history_minutes": {"type": "integer", "description": "Minutes of history to fetch"}
                    },
                    "required": ["device_id", "sensor_type"]
                }
            },
            {
                "name": "control_actuator",
                "description": "Control device actuators",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device ID"},
                        "actuator_type": {"type": "string", "description": "Actuator type"},
                        "action": {"type": "string", "description": "Action to perform"}
                    },
                    "required": ["device_id", "actuator_type", "action"]
                }
            },
            {
                "name": "get_device_info",
                "description": "Get detailed device information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "device_id": {"type": "string", "description": "Device ID"}
                    },
                    "required": ["device_id"]
                }
            },
            {
                "name": "query_database",
                "description": "Execute a custom SQL query on the sensor database (SELECT only, read-only)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL SELECT query to execute"},
                        "max_rows": {"type": "integer", "description": "Maximum rows to return (default 10000)"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_database_schema",
                "description": "Get database schema showing all tables and columns",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_query_examples",
                "description": "Get example SQL queries for common use cases",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

        return web.json_response({"tools": tools})
    
    async def call_tool(self, request):
        """Call an MCP tool"""
        tool_name = request.match_info['tool_name']
        
        try:
            data = await request.json()
            arguments = data.get('arguments', {})
            
            # Call the bridge's MCP tool
            result = await self.bridge.call_mcp_tool(tool_name, arguments)
            
            return web.json_response({
                "success": True,
                "result": result
            })
            
        except json.JSONDecodeError:
            return web.json_response({
                "error": "Invalid JSON in request body"
            }, status=400)
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {e}")
            return web.json_response({
                "error": str(e)
            }, status=500)
    
    async def websocket_handler(self, request):
        """WebSocket handler for real-time MCP communication"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        logger.info("New WebSocket connection established")
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        method = data.get('method')
                        params = data.get('params', {})
                        msg_id = data.get('id')
                        
                        if method == 'tools/call':
                            tool_name = params.get('name')
                            arguments = params.get('arguments', {})
                            
                            result = await self.bridge.call_mcp_tool(tool_name, arguments)
                            
                            response = {
                                "jsonrpc": "2.0",
                                "id": msg_id,
                                "result": {
                                    "content": [{"type": "text", "text": str(result)}]
                                }
                            }
                        elif method == 'tools/list':
                            tools_response = await self.list_tools(request)
                            tools_data = json.loads(tools_response.text)
                            
                            response = {
                                "jsonrpc": "2.0", 
                                "id": msg_id,
                                "result": {"tools": tools_data["tools"]}
                            }
                        else:
                            response = {
                                "jsonrpc": "2.0",
                                "id": msg_id,
                                "error": {"code": -32601, "message": "Method not found"}
                            }
                        
                        await ws.send_str(json.dumps(response))
                        
                    except json.JSONDecodeError:
                        await ws.send_str(json.dumps({
                            "jsonrpc": "2.0",
                            "error": {"code": -32700, "message": "Parse error"}
                        }))
                    except Exception as e:
                        logger.error(f"WebSocket error: {e}")
                        await ws.send_str(json.dumps({
                            "jsonrpc": "2.0", 
                            "error": {"code": -32603, "message": "Internal error"}
                        }))
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    break
        finally:
            self.websockets.discard(ws)
            logger.info("WebSocket connection closed")
        
        return ws
    
    # REST API endpoints for direct device access
    async def get_devices(self, request):
        """Get list of devices"""
        try:
            result = await self.bridge.call_mcp_tool("list_devices", {})
            return web.json_response({"devices": result})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_device_info(self, request):
        """Get device information"""
        device_id = request.match_info['device_id']
        try:
            result = await self.bridge.call_mcp_tool("get_device_info", {"device_id": device_id})
            return web.json_response({"device": result})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_sensor_data(self, request):
        """Get sensor data"""
        device_id = request.match_info['device_id']
        sensor_type = request.match_info['sensor_type']
        
        try:
            result = await self.bridge.call_mcp_tool("read_sensor", {
                "device_id": device_id,
                "sensor_type": sensor_type
            })
            return web.json_response({"data": result})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def control_actuator(self, request):
        """Control actuator"""
        device_id = request.match_info['device_id']
        actuator_type = request.match_info['actuator_type']
        
        try:
            data = await request.json()
            action = data.get('action')
            
            if not action:
                return web.json_response({"error": "Missing 'action' in request body"}, status=400)
            
            result = await self.bridge.call_mcp_tool("control_actuator", {
                "device_id": device_id,
                "actuator_type": actuator_type,
                "action": action
            })
            return web.json_response({"result": result})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def start(self):
        """Start the HTTP server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"MCP HTTP server started on http://{self.host}:{self.port}")
        logger.info(f"  - Health check: http://{self.host}:{self.port}/health")
        logger.info(f"  - MCP WebSocket: ws://{self.host}:{self.port}/mcp")
        logger.info(f"  - Tools API: http://{self.host}:{self.port}/tools")
        logger.info(f"  - Devices API: http://{self.host}:{self.port}/devices")
    
    async def stop(self):
        """Stop the HTTP server"""
        # Close all WebSocket connections
        for ws in self.websockets.copy():
            await ws.close()
        logger.info("MCP HTTP server stopped")