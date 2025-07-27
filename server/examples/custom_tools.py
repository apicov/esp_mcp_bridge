#!/usr/bin/env python3
"""
Custom MCP tools example for MCP-MQTT Bridge.
Demonstrates how to extend the bridge with additional functionality.
"""
import asyncio
import json
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    LoggingLevel, CallToolRequest, CallToolResult
)

# Import bridge components for extension
try:
    from mcp_mqtt_bridge.bridge import MCPMQTTBridge
    from mcp_mqtt_bridge.database import DatabaseManager
    from mcp_mqtt_bridge.device_manager import DeviceManager
except ImportError:
    print("MCP-MQTT Bridge components not found")
    sys.exit(1)


class CustomToolsExtension:
    """Extension providing custom tools for the MCP bridge."""
    
    def __init__(self, bridge: MCPMQTTBridge):
        self.bridge = bridge
        self.server = Server("mcp-mqtt-custom-tools")
        self.logger = logging.getLogger(__name__)
        self._register_tools()
    
    def _register_tools(self):
        """Register custom tools with the MCP server."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List all available custom tools."""
            return [
                Tool(
                    name="analyze_device_trends",
                    description="Analyze sensor data trends for a device over time",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {"type": "string", "description": "Device ID to analyze"},
                            "sensor_type": {"type": "string", "description": "Type of sensor to analyze"},
                            "days": {"type": "integer", "default": 7, "description": "Number of days to analyze"}
                        },
                        "required": ["device_id", "sensor_type"]
                    }
                ),
                Tool(
                    name="create_device_group",
                    description="Create a logical group of devices for batch operations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "group_name": {"type": "string", "description": "Name for the device group"},
                            "device_ids": {"type": "array", "items": {"type": "string"}, "description": "List of device IDs"},
                            "description": {"type": "string", "description": "Optional group description"}
                        },
                        "required": ["group_name", "device_ids"]
                    }
                ),
                Tool(
                    name="control_device_group",
                    description="Control all devices in a group simultaneously",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "group_name": {"type": "string", "description": "Name of the device group"},
                            "actuator_type": {"type": "string", "description": "Type of actuator to control"},
                            "action": {"type": "string", "description": "Action to perform"}
                        },
                        "required": ["group_name", "actuator_type", "action"]
                    }
                ),
                Tool(
                    name="generate_device_report",
                    description="Generate a comprehensive report for device status and performance",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {"type": "string", "description": "Device ID for report"},
                            "report_type": {"type": "string", "enum": ["summary", "detailed", "performance"], "default": "summary"},
                            "include_charts": {"type": "boolean", "default": False, "description": "Include data visualization"}
                        },
                        "required": ["device_id"]
                    }
                ),
                Tool(
                    name="predict_sensor_values",
                    description="Predict future sensor values based on historical data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "device_id": {"type": "string", "description": "Device ID"},
                            "sensor_type": {"type": "string", "description": "Sensor type to predict"},
                            "hours_ahead": {"type": "integer", "default": 24, "description": "Hours to predict ahead"}
                        },
                        "required": ["device_id", "sensor_type"]
                    }
                ),
                Tool(
                    name="setup_automation_rule",
                    description="Create automation rules based on sensor conditions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "rule_name": {"type": "string", "description": "Name for the automation rule"},
                            "trigger_device": {"type": "string", "description": "Device ID that triggers the rule"},
                            "trigger_sensor": {"type": "string", "description": "Sensor type that triggers"},
                            "trigger_condition": {"type": "string", "description": "Condition (e.g., '> 25')"},
                            "action_device": {"type": "string", "description": "Device to control"},
                            "action_actuator": {"type": "string", "description": "Actuator to control"},
                            "action_value": {"type": "string", "description": "Action to perform"}
                        },
                        "required": ["rule_name", "trigger_device", "trigger_sensor", "trigger_condition", 
                                   "action_device", "action_actuator", "action_value"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent | ImageContent | EmbeddedResource]:
            """Handle custom tool calls."""
            try:
                if name == "analyze_device_trends":
                    return await self._analyze_device_trends(arguments)
                elif name == "create_device_group":
                    return await self._create_device_group(arguments)
                elif name == "control_device_group":
                    return await self._control_device_group(arguments)
                elif name == "generate_device_report":
                    return await self._generate_device_report(arguments)
                elif name == "predict_sensor_values":
                    return await self._predict_sensor_values(arguments)
                elif name == "setup_automation_rule":
                    return await self._setup_automation_rule(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                self.logger.error(f"Error in custom tool {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _analyze_device_trends(self, args: Dict[str, Any]) -> List[TextContent]:
        """Analyze sensor data trends for a device."""
        device_id = args["device_id"]
        sensor_type = args["sensor_type"]
        days = args.get("days", 7)
        
        # Get historical data from database
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # Mock analysis for demonstration
        analysis = {
            "device_id": device_id,
            "sensor_type": sensor_type,
            "analysis_period": f"{days} days",
            "data_points": 168,  # Mock: hourly readings for 7 days
            "average_value": 23.2,
            "min_value": 18.5,
            "max_value": 28.1,
            "trend": "stable",
            "anomalies_detected": 2,
            "recommendations": [
                "Sensor readings are within normal range",
                "Two minor anomalies detected during maintenance window",
                "Consider increasing sampling frequency during peak hours"
            ]
        }
        
        report = f"""
📊 Sensor Trend Analysis Report

Device: {device_id}
Sensor: {sensor_type}
Period: {days} days

📈 Statistics:
  • Data Points: {analysis['data_points']}
  • Average: {analysis['average_value']}°C
  • Range: {analysis['min_value']}°C - {analysis['max_value']}°C
  • Trend: {analysis['trend'].title()}

⚠️ Anomalies: {analysis['anomalies_detected']} detected

💡 Recommendations:
{chr(10).join(f"  • {rec}" for rec in analysis['recommendations'])}
        """
        
        return [TextContent(type="text", text=report.strip())]
    
    async def _create_device_group(self, args: Dict[str, Any]) -> List[TextContent]:
        """Create a logical group of devices."""
        group_name = args["group_name"]
        device_ids = args["device_ids"]
        description = args.get("description", "")
        
        # Store group in database (mock implementation)
        group_data = {
            "group_name": group_name,
            "device_ids": device_ids,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "device_count": len(device_ids)
        }
        
        result = f"""
✅ Device Group Created

Group Name: {group_name}
Description: {description or 'No description provided'}
Devices: {len(device_ids)} devices
  {chr(10).join(f'  • {device_id}' for device_id in device_ids)}

The group can now be used for batch operations.
        """
        
        return [TextContent(type="text", text=result.strip())]
    
    async def _control_device_group(self, args: Dict[str, Any]) -> List[TextContent]:
        """Control all devices in a group."""
        group_name = args["group_name"]
        actuator_type = args["actuator_type"]
        action = args["action"]
        
        # Mock group lookup and control
        mock_device_ids = ["esp32_kitchen", "esp32_living_room", "esp32_bedroom"]
        
        results = []
        for device_id in mock_device_ids:
            # Simulate control operation
            success = True  # Mock success
            results.append({
                "device_id": device_id,
                "success": success,
                "message": f"Successfully {action}d {actuator_type}" if success else "Failed to control device"
            })
        
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        report = f"""
🎛️ Group Control Results

Group: {group_name}
Action: {action} {actuator_type}

📊 Summary:
  • Successful: {successful} devices
  • Failed: {failed} devices

📋 Details:
{chr(10).join(f'  • {r["device_id"]}: {r["message"]}' for r in results)}
        """
        
        return [TextContent(type="text", text=report.strip())]
    
    async def _generate_device_report(self, args: Dict[str, Any]) -> List[TextContent]:
        """Generate a comprehensive device report."""
        device_id = args["device_id"]
        report_type = args.get("report_type", "summary")
        include_charts = args.get("include_charts", False)
        
        # Mock device data
        device_data = {
            "device_id": device_id,
            "device_type": "ESP32",
            "firmware_version": "1.2.3",
            "status": "online",
            "last_seen": "2024-01-15T10:30:00Z",
            "uptime": "7 days, 14 hours",
            "memory_usage": "78%",
            "cpu_usage": "23%",
            "sensors": ["temperature", "humidity", "pressure"],
            "actuators": ["led", "relay"],
            "error_count": 2,
            "data_points_today": 1440
        }
        
        if report_type == "summary":
            report = f"""
📱 Device Summary Report

Device: {device_data['device_id']} ({device_data['device_type']})
Status: {device_data['status'].title()} ✅
Firmware: v{device_data['firmware_version']}
Uptime: {device_data['uptime']}

📊 Today's Metrics:
  • Data Points: {device_data['data_points_today']:,}
  • Errors: {device_data['error_count']}
  • Memory Usage: {device_data['memory_usage']}
  • CPU Usage: {device_data['cpu_usage']}

🔧 Capabilities:
  • Sensors: {', '.join(device_data['sensors'])}
  • Actuators: {', '.join(device_data['actuators'])}
            """
        
        elif report_type == "detailed":
            report = f"""
📊 Detailed Device Report

🔍 Device Information:
  • ID: {device_data['device_id']}
  • Type: {device_data['device_type']}
  • Firmware: v{device_data['firmware_version']}
  • Status: {device_data['status'].title()}
  • Last Seen: {device_data['last_seen']}
  • Uptime: {device_data['uptime']}

💻 System Metrics:
  • Memory Usage: {device_data['memory_usage']}
  • CPU Usage: {device_data['cpu_usage']}
  • Error Count: {device_data['error_count']}

📈 Data Collection:
  • Data Points Today: {device_data['data_points_today']:,}
  • Average per Hour: {device_data['data_points_today'] // 24}

🔧 Hardware Capabilities:
  • Sensors: {chr(10).join(f'    - {sensor}' for sensor in device_data['sensors'])}
  • Actuators: {chr(10).join(f'    - {actuator}' for actuator in device_data['actuators'])}

📊 Recent Sensor Readings:
  • Temperature: 23.5°C (Normal)
  • Humidity: 45% (Normal)
  • Pressure: 1013.2 hPa (Normal)
            """
        
        else:  # performance
            report = f"""
⚡ Performance Report

Device: {device_data['device_id']}
Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🚀 Performance Metrics:
  • Response Time: 45ms (Excellent)
  • Data Throughput: 1.2 KB/s
  • Connection Stability: 99.8%
  • Battery Level: 87% (if applicable)

📊 24-Hour Statistics:
  • Messages Sent: 1,440
  • Messages Failed: 0
  • Average Latency: 42ms
  • Peak Usage: 14:30 (lunch time)

🔄 System Health:
  • Memory Usage: {device_data['memory_usage']} (Good)
  • CPU Usage: {device_data['cpu_usage']} (Low)
  • Storage: 45% used
  • Temperature: Normal operating range

💡 Optimization Suggestions:
  • Consider reducing sampling frequency during low-activity periods
  • Memory usage is within acceptable limits
  • No immediate maintenance required
            """
        
        return [TextContent(type="text", text=report.strip())]
    
    async def _predict_sensor_values(self, args: Dict[str, Any]) -> List[TextContent]:
        """Predict future sensor values using simple trend analysis."""
        device_id = args["device_id"]
        sensor_type = args["sensor_type"]
        hours_ahead = args.get("hours_ahead", 24)
        
        # Mock prediction model
        current_value = 23.5  # Mock current temperature
        predictions = []
        
        for hour in range(1, min(hours_ahead + 1, 49)):  # Limit to 48 hours
            # Simple sine wave prediction for demonstration
            import math
            predicted_value = current_value + 2 * math.sin(hour * math.pi / 12)
            confidence = max(0.95 - (hour * 0.02), 0.3)  # Decreasing confidence
            
            predictions.append({
                "hour": hour,
                "predicted_value": round(predicted_value, 1),
                "confidence": round(confidence * 100, 1)
            })
        
        report = f"""
🔮 Sensor Value Predictions

Device: {device_id}
Sensor: {sensor_type}
Prediction Window: {hours_ahead} hours
Model: Trend Analysis with Seasonal Adjustment

📈 Predictions (next 12 hours):
{chr(10).join(f'  Hour +{p["hour"]:2d}: {p["predicted_value"]:5.1f}°C (confidence: {p["confidence"]:4.1f}%)' for p in predictions[:12])}

📊 Summary:
  • Current Value: {current_value}°C
  • Predicted Range: {min(p["predicted_value"] for p in predictions)} - {max(p["predicted_value"] for p in predictions)}°C
  • Average Confidence: {sum(p["confidence"] for p in predictions) / len(predictions):.1f}%

⚠️ Note: Predictions are based on historical patterns and may not account for unexpected events.
        """
        
        return [TextContent(type="text", text=report.strip())]
    
    async def _setup_automation_rule(self, args: Dict[str, Any]) -> List[TextContent]:
        """Setup an automation rule."""
        rule_data = {
            "rule_name": args["rule_name"],
            "trigger": {
                "device": args["trigger_device"],
                "sensor": args["trigger_sensor"],
                "condition": args["trigger_condition"]
            },
            "action": {
                "device": args["action_device"],
                "actuator": args["action_actuator"],
                "value": args["action_value"]
            },
            "created_at": datetime.now().isoformat(),
            "enabled": True
        }
        
        report = f"""
🤖 Automation Rule Created

Rule Name: {rule_data['rule_name']}
Status: Enabled ✅

🔔 Trigger:
  • Device: {rule_data['trigger']['device']}
  • Sensor: {rule_data['trigger']['sensor']}
  • Condition: {rule_data['trigger']['condition']}

⚡ Action:
  • Device: {rule_data['action']['device']}
  • Actuator: {rule_data['action']['actuator']}
  • Action: {rule_data['action']['value']}

Example: When {rule_data['trigger']['device']} {rule_data['trigger']['sensor']} {rule_data['trigger']['condition']}, 
         then {rule_data['action']['device']} {rule_data['action']['actuator']} will {rule_data['action']['value']}.

The rule is now active and will be evaluated whenever sensor data is received.
        """
        
        return [TextContent(type="text", text=report.strip())]


async def main():
    """Main function demonstrating custom tools."""
    print("🔧 MCP-MQTT Bridge Custom Tools Example")
    print("=" * 50)
    
    # This would normally be integrated with the main bridge
    # For demo purposes, we'll create a mock bridge instance
    
    print("Custom tools that can be added to the MCP bridge:")
    print("• analyze_device_trends - Analyze sensor data patterns")
    print("• create_device_group - Group devices for batch operations")
    print("• control_device_group - Control multiple devices at once")
    print("• generate_device_report - Create comprehensive device reports")
    print("• predict_sensor_values - Predict future sensor readings")
    print("• setup_automation_rule - Create automation rules")
    
    print("\nThese tools extend the basic MCP bridge functionality with:")
    print("• Advanced analytics and reporting")
    print("• Device grouping and batch operations")
    print("• Predictive analytics")
    print("• Automation rule engine")
    print("\nTo integrate these tools, modify the main bridge to include the CustomToolsExtension.")


if __name__ == "__main__":
    asyncio.run(main()) 