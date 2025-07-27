#!/usr/bin/env python3
"""
Web dashboard example for MCP-MQTT Bridge.
Provides a simple web interface to monitor and control IoT devices.
"""
import asyncio
import json
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from flask import Flask, render_template_string, jsonify, request, Response
    from flask_cors import CORS
    import requests
except ImportError:
    print("Flask and requests are required for the dashboard example")
    print("Install with: pip install flask flask-cors requests")
    sys.exit(1)

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


# HTML template for the dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MCP-MQTT Bridge Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .header h1 { margin: 0; }
        .status { font-size: 14px; opacity: 0.8; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
        .card h3 { margin-top: 0; color: #2c3e50; }
        .device { border-left: 4px solid #3498db; margin-bottom: 15px; padding: 10px; background: #ecf0f1; }
        .device.online { border-color: #2ecc71; }
        .device.offline { border-color: #e74c3c; }
        .sensor-reading { display: flex; justify-content: space-between; margin: 5px 0; }
        .controls button { 
            background: #3498db; color: white; border: none; padding: 8px 16px; 
            border-radius: 3px; margin: 2px; cursor: pointer; 
        }
        .controls button:hover { background: #2980b9; }
        .controls button.danger { background: #e74c3c; }
        .controls button.danger:hover { background: #c0392b; }
        .refresh-btn { 
            position: fixed; bottom: 20px; right: 20px; background: #2ecc71; 
            color: white; border: none; padding: 15px; border-radius: 50%; 
            cursor: pointer; font-size: 18px; box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }
        .loading { text-align: center; color: #7f8c8d; }
        .error { color: #e74c3c; background: #fdf2f2; padding: 10px; border-radius: 3px; }
        .alert { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 10px; border-radius: 3px; margin: 5px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🏠 MCP-MQTT Bridge Dashboard</h1>
        <div class="status" id="status">Connecting...</div>
    </div>

    <div class="grid">
        <div class="card">
            <h3>📊 System Status</h3>
            <div id="system-stats">Loading...</div>
        </div>

        <div class="card">
            <h3>🚨 Recent Alerts</h3>
            <div id="alerts">Loading...</div>
        </div>

        <div class="card">
            <h3>🔧 Quick Controls</h3>
            <div class="controls">
                <button onclick="refreshAll()">🔄 Refresh All</button>
                <button onclick="toggleAllLeds()">💡 Toggle All LEDs</button>
                <button onclick="getSystemInfo()">ℹ️ System Info</button>
            </div>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h3>📱 Connected Devices</h3>
            <div id="devices">Loading devices...</div>
        </div>
    </div>

    <button class="refresh-btn" onclick="refreshAll()" title="Refresh All Data">🔄</button>

    <script>
        let refreshInterval;
        
        async function apiCall(endpoint, data = null) {
            try {
                const response = await fetch(endpoint, {
                    method: data ? 'POST' : 'GET',
                    headers: { 'Content-Type': 'application/json' },
                    body: data ? JSON.stringify(data) : null
                });
                return await response.json();
            } catch (error) {
                console.error('API call failed:', error);
                return { error: error.message };
            }
        }

        async function loadDevices() {
            const devices = await apiCall('/api/devices');
            const container = document.getElementById('devices');
            
            if (devices.error) {
                container.innerHTML = `<div class="error">Error: ${devices.error}</div>`;
                return;
            }

            if (!devices.devices || devices.devices.length === 0) {
                container.innerHTML = '<div class="loading">No devices found</div>';
                return;
            }

            container.innerHTML = devices.devices.map(device => `
                <div class="device ${device.status}">
                    <strong>${device.device_id}</strong> (${device.device_type})
                    <div style="font-size: 12px; color: #7f8c8d;">
                        Status: ${device.status} | Last seen: ${device.last_seen || 'Never'}
                    </div>
                    <div class="sensor-readings">
                        ${device.sensors.map(sensor => `
                            <div class="sensor-reading">
                                <span>${sensor.type}:</span>
                                <span>${sensor.value} ${sensor.unit}</span>
                            </div>
                        `).join('')}
                    </div>
                    <div class="controls">
                        ${device.actuators.map(actuator => `
                            <button onclick="controlDevice('${device.device_id}', '${actuator}', 'toggle')">
                                ${actuator === 'led' ? '💡' : '🔧'} ${actuator}
                            </button>
                        `).join('')}
                        <button onclick="getDeviceInfo('${device.device_id}')">ℹ️ Info</button>
                    </div>
                </div>
            `).join('');
        }

        async function loadAlerts() {
            const alerts = await apiCall('/api/alerts');
            const container = document.getElementById('alerts');
            
            if (alerts.error) {
                container.innerHTML = `<div class="error">Error: ${alerts.error}</div>`;
                return;
            }

            if (!alerts.alerts || alerts.alerts.length === 0) {
                container.innerHTML = '<div class="loading">No recent alerts</div>';
                return;
            }

            container.innerHTML = alerts.alerts.map(alert => `
                <div class="alert">
                    <strong>${alert.device_id}</strong>: ${alert.message}
                    <div style="font-size: 11px; opacity: 0.7;">${alert.timestamp}</div>
                </div>
            `).join('');
        }

        async function loadSystemStats() {
            const stats = await apiCall('/api/stats');
            const container = document.getElementById('system-stats');
            
            if (stats.error) {
                container.innerHTML = `<div class="error">Error: ${stats.error}</div>`;
                return;
            }

            container.innerHTML = `
                <div class="sensor-reading"><span>Total Devices:</span><span>${stats.total_devices}</span></div>
                <div class="sensor-reading"><span>Online Devices:</span><span>${stats.online_devices}</span></div>
                <div class="sensor-reading"><span>Recent Readings:</span><span>${stats.recent_readings}</span></div>
                <div class="sensor-reading"><span>System Uptime:</span><span>${stats.uptime}</span></div>
            `;
        }

        async function controlDevice(deviceId, actuator, action) {
            const result = await apiCall('/api/control', {
                device_id: deviceId,
                actuator_type: actuator,
                action: action
            });
            
            if (result.error) {
                alert(`Error: ${result.error}`);
            } else {
                // Refresh devices after control action
                setTimeout(loadDevices, 1000);
            }
        }

        async function getDeviceInfo(deviceId) {
            const info = await apiCall('/api/device_info', { device_id: deviceId });
            
            if (info.error) {
                alert(`Error: ${info.error}`);
            } else {
                alert(`Device Info:\\n${JSON.stringify(info, null, 2)}`);
            }
        }

        async function toggleAllLeds() {
            const devices = await apiCall('/api/devices');
            if (devices.devices) {
                for (const device of devices.devices) {
                    if (device.actuators.includes('led') && device.status === 'online') {
                        await controlDevice(device.device_id, 'led', 'toggle');
                    }
                }
            }
        }

        async function refreshAll() {
            document.getElementById('status').textContent = 'Refreshing...';
            await Promise.all([loadDevices(), loadAlerts(), loadSystemStats()]);
            document.getElementById('status').textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        }

        // Initialize dashboard
        refreshAll();
        
        // Auto-refresh every 30 seconds
        refreshInterval = setInterval(refreshAll, 30000);
    </script>
</body>
</html>
"""


class MCPDashboard:
    """Web dashboard for MCP-MQTT Bridge."""
    
    def __init__(self, mcp_config_path: str = "config/development.yaml"):
        self.app = Flask(__name__)
        CORS(self.app)
        self.mcp_config_path = mcp_config_path
        self.setup_routes()
        
    def setup_routes(self):
        """Set up Flask routes."""
        @self.app.route('/')
        def dashboard():
            return render_template_string(DASHBOARD_TEMPLATE)
        
        @self.app.route('/api/devices')
        def get_devices():
            return asyncio.run(self._get_devices())
        
        @self.app.route('/api/alerts')
        def get_alerts():
            return asyncio.run(self._get_alerts())
        
        @self.app.route('/api/stats')
        def get_stats():
            return asyncio.run(self._get_stats())
        
        @self.app.route('/api/control', methods=['POST'])
        def control_device():
            data = request.get_json()
            return asyncio.run(self._control_device(data))
        
        @self.app.route('/api/device_info', methods=['POST'])
        def get_device_info():
            data = request.get_json()
            return asyncio.run(self._get_device_info(data))
    
    async def _call_mcp_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool and return the result."""
        server_params = StdioServerParameters(
            command="python",
            args=["-m", "mcp_mqtt_bridge", "--config", self.mcp_config_path],
            env={}
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(tool_name, parameters)
                    
                    if result.content:
                        # Parse the result content
                        content = result.content[0].text
                        try:
                            return json.loads(content)
                        except json.JSONDecodeError:
                            return {"result": content}
                    else:
                        return {"error": "No content returned"}
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_devices(self) -> Dict[str, Any]:
        """Get list of all devices with their sensor readings."""
        devices_result = await self._call_mcp_tool("list_devices", {"online_only": False})
        
        if "error" in devices_result:
            return devices_result
        
        # Mock device data for demo purposes
        mock_devices = [
            {
                "device_id": "esp32_kitchen",
                "device_type": "ESP32",
                "status": "online",
                "last_seen": "2024-01-15T10:30:00Z",
                "sensors": [
                    {"type": "temperature", "value": "23.5", "unit": "°C"},
                    {"type": "humidity", "value": "45", "unit": "%"}
                ],
                "actuators": ["led", "relay"]
            },
            {
                "device_id": "esp32_living_room",
                "device_type": "ESP32",
                "status": "online",
                "last_seen": "2024-01-15T10:29:30Z",
                "sensors": [
                    {"type": "temperature", "value": "22.1", "unit": "°C"},
                    {"type": "light", "value": "350", "unit": "lux"}
                ],
                "actuators": ["led"]
            },
            {
                "device_id": "esp32_garage",
                "device_type": "ESP32",
                "status": "offline",
                "last_seen": "2024-01-15T09:45:00Z",
                "sensors": [
                    {"type": "temperature", "value": "18.2", "unit": "°C"}
                ],
                "actuators": ["led", "door"]
            }
        ]
        
        return {"devices": mock_devices}
    
    async def _get_alerts(self) -> Dict[str, Any]:
        """Get recent alerts."""
        alerts_result = await self._call_mcp_tool("get_alerts", {"severity_min": 1})
        
        if "error" in alerts_result:
            return alerts_result
        
        # Mock alerts for demo
        mock_alerts = [
            {
                "device_id": "esp32_garage",
                "message": "Device went offline",
                "severity": 2,
                "timestamp": "2024-01-15T09:45:00Z"
            },
            {
                "device_id": "esp32_kitchen",
                "message": "High temperature reading",
                "severity": 1,
                "timestamp": "2024-01-15T10:15:00Z"
            }
        ]
        
        return {"alerts": mock_alerts}
    
    async def _get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        # Mock stats for demo
        return {
            "total_devices": 3,
            "online_devices": 2,
            "recent_readings": 156,
            "uptime": "2 days, 14 hours"
        }
    
    async def _control_device(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Control a device actuator."""
        return await self._call_mcp_tool("control_actuator", data)
    
    async def _get_device_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed device information."""
        return await self._call_mcp_tool("get_device_info", data)
    
    def run(self, host: str = "localhost", port: int = 5000, debug: bool = True):
        """Run the dashboard server."""
        print(f"🌐 Starting MCP-MQTT Bridge Dashboard on http://{host}:{port}")
        print("📱 Access the dashboard in your web browser")
        self.app.run(host=host, port=port, debug=debug)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP-MQTT Bridge Web Dashboard")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--config", default="config/development.yaml", 
                       help="MCP bridge configuration file")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    dashboard = MCPDashboard(args.config)
    dashboard.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main() 