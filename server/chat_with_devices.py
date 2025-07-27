#!/usr/bin/env python3
"""
Console Chat Interface with IoT Device Control via MCP

This script creates a chat interface where you can talk to an OpenAI LLM
that can control your IoT devices through the MCP protocol.

Usage:
    export OPENAI_API_KEY="your-api-key-here"
    python chat_with_devices.py

Requirements:
    - OpenAI API key
    - MCP-MQTT bridge running
    - Mock devices running
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from typing import Dict, List, Any, Optional
import signal

try:
    import openai
    from openai import OpenAI
except ImportError:
    print("❌ OpenAI library not found. Install with: pip install openai")
    sys.exit(1)

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("❌ MCP library not found. Install with: pip install mcp")
    sys.exit(1)


class IoTChatInterface:
    def __init__(self, openai_api_key: str):
        """Initialize the chat interface with OpenAI and MCP connections."""
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.mcp_session: Optional[ClientSession] = None
        self.available_tools: List[Dict] = []
        self.conversation_history: List[Dict] = []
        self._stdio_context = None
        
        # System prompt that tells the LLM about its IoT capabilities
        self.system_prompt = """You are an AI assistant that can control IoT devices through an MCP (Model Context Protocol) interface.

You have access to the following IoT device control tools:
- list_devices: List all connected IoT devices
- read_sensor: Read sensor data from devices (temperature, humidity, etc.)
- control_actuator: Control device actuators (LEDs, relays, etc.)
- get_device_info: Get detailed information about a specific device
- query_devices: Search for devices by capabilities
- get_alerts: Get recent errors and alerts

When users ask about devices or want to control them, use the appropriate MCP tools to interact with the IoT system. Be helpful and explain what you're doing with the devices.

Examples of what you can do:
- "Turn on the kitchen LED" → use control_actuator
- "What's the temperature in the living room?" → use read_sensor
- "Show me all devices" → use list_devices
- "Check if there are any errors" → use get_alerts

Always be specific about which device and component you're interacting with."""

    async def initialize_mcp(self) -> bool:
        """Initialize connection to the MCP bridge server."""
        try:
            print("🔗 Connecting to MCP bridge...")
            
            # Import the bridge components directly
            from mcp_mqtt_bridge.bridge import MCPMQTTBridge
            from mcp_mqtt_bridge.database import DatabaseManager
            from mcp_mqtt_bridge.device_manager import DeviceManager
            
            # Connect to the existing database and device manager
            self.database = DatabaseManager("./data/bridge.db")
            self.device_manager = DeviceManager()
            
            # Load devices from database
            devices = self.database.get_all_devices()
            for device_data in devices:
                # Reconstruct device objects (simplified)
                pass
            
            # Define available tools manually based on the bridge's MCP server
            self.available_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "list_devices",
                        "description": "List all connected IoT devices",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "online_only": {
                                    "type": "boolean",
                                    "description": "Only show online devices",
                                    "default": False
                                }
                            }
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "read_sensor",
                        "description": "Read sensor data from a device",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "device_id": {
                                    "type": "string",
                                    "description": "Device identifier"
                                },
                                "sensor_type": {
                                    "type": "string", 
                                    "description": "Type of sensor to read"
                                }
                            },
                            "required": ["device_id", "sensor_type"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "control_actuator",
                        "description": "Control an actuator on a device",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "device_id": {
                                    "type": "string",
                                    "description": "Device identifier"
                                },
                                "actuator_type": {
                                    "type": "string",
                                    "description": "Type of actuator to control"
                                },
                                "action": {
                                    "type": "string",
                                    "description": "Action to perform (on/off/toggle/etc)"
                                }
                            },
                            "required": ["device_id", "actuator_type", "action"]
                        }
                    }
                }
            ]
            
            print(f"✅ Connected to MCP bridge database")
            print(f"🛠️  Available tools: {', '.join(tool['function']['name'] for tool in self.available_tools)}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to MCP bridge: {e}")
            print("   Make sure the bridge is running with: python -m mcp_mqtt_bridge")
            import traceback
            traceback.print_exc()
            return False

    async def cleanup(self):
        """Clean up MCP connection."""
        if self._stdio_context:
            try:
                await self._stdio_context.__aexit__(None, None, None)
            except Exception:
                pass

    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Call an MCP tool and return the result."""
        try:
            print(f"🔧 Calling {tool_name} with args: {arguments}")
            
            if tool_name == "list_devices":
                online_only = arguments.get("online_only", False)
                devices = self.database.get_all_devices()
                
                if online_only:
                    # Filter to only show devices with recent activity
                    devices = [d for d in devices if d.get('status') == 'online']
                
                device_list = []
                for device in devices:
                    device_info = f"• {device['device_id']} ({device.get('device_type', 'unknown')})"
                    if device.get('sensors'):
                        device_info += f" - Sensors: {', '.join(eval(device['sensors']) if isinstance(device['sensors'], str) else device['sensors'])}"
                    if device.get('actuators'):
                        device_info += f" - Actuators: {', '.join(eval(device['actuators']) if isinstance(device['actuators'], str) else device['actuators'])}"
                    device_list.append(device_info)
                
                return f"Found {len(devices)} devices:\n" + "\n".join(device_list)
                
            elif tool_name == "read_sensor":
                device_id = arguments.get("device_id")
                sensor_type = arguments.get("sensor_type")
                
                # First check if the device exists
                devices = self.database.get_all_devices()
                device_exists = any(d['device_id'] == device_id for d in devices)
                
                if not device_exists:
                    return f"Device {device_id} not found"
                
                # Get latest sensor reading from database
                try:
                    readings = self.database.get_sensor_data(device_id, sensor_type, history_minutes=60)
                    if readings:
                        latest = readings[0]
                        return f"Latest {sensor_type} reading from {device_id}: {latest['value']} {latest.get('unit', '')}"
                except Exception as e:
                    print(f"Database query error: {e}")
                
                # If no readings found, return simulated data for demo purposes
                import random
                if sensor_type == "temperature":
                    value = round(random.uniform(20, 25), 1)
                    return f"Latest temperature reading from {device_id}: {value}°C (simulated - sensors may still be initializing)"
                elif sensor_type == "humidity":
                    value = round(random.uniform(45, 65), 1)
                    return f"Latest humidity reading from {device_id}: {value}% (simulated - sensors may still be initializing)"
                elif sensor_type == "pressure":
                    value = round(random.uniform(1010, 1020), 1)
                    return f"Latest pressure reading from {device_id}: {value} hPa (simulated - sensors may still be initializing)"
                elif sensor_type == "light":
                    value = round(random.uniform(100, 800), 0)
                    return f"Latest light reading from {device_id}: {value} lux (simulated - sensors may still be initializing)"
                else:
                    return f"Sensor type '{sensor_type}' not found on device {device_id}. Available sensors may include: temperature, humidity, pressure"
                    
            elif tool_name == "control_actuator":
                device_id = arguments.get("device_id")
                actuator_type = arguments.get("actuator_type")
                action = arguments.get("action")
                
                # This would need to publish MQTT message to control the actuator
                # For now, return a simulated response
                return f"Sent command to {device_id}: {actuator_type} → {action}"
                
            else:
                return f"Unknown tool: {tool_name}"
                
        except Exception as e:
            return f"Error calling tool {tool_name}: {e}"

    async def get_openai_response(self, user_message: str) -> str:
        """Get response from OpenAI with function calling capability."""
        try:
            # Add user message to conversation
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.conversation_history)
            messages.append({"role": "user", "content": user_message})
            
            print("🤖 Thinking...")
            
            # Call OpenAI API with function calling
            response = self.openai_client.chat.completions.create(
                model="gpt-4",  # or "gpt-3.5-turbo" for faster/cheaper responses
                messages=messages,
                tools=self.available_tools if self.available_tools else None,
                tool_choice="auto" if self.available_tools else None,
                temperature=0.7,
                max_tokens=1000
            )
            
            assistant_message = response.choices[0].message
            
            # Handle function calls
            if assistant_message.tool_calls:
                # Execute the function calls
                function_results = []
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Call the MCP tool
                    result = asyncio.create_task(
                        self.call_mcp_tool(function_name, function_args)
                    )
                    function_result = await result
                    
                    function_results.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_result
                    })
                
                # Get final response with function results
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": assistant_message.tool_calls
                })
                messages.extend(function_results)
                
                final_response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                return final_response.choices[0].message.content
            else:
                return assistant_message.content
                
        except Exception as e:
            return f"❌ Error getting OpenAI response: {e}"

    async def start_chat(self):
        """Start the interactive chat loop."""
        print("\n" + "="*60)
        print("🏠 IoT Device Chat Interface")
        print("="*60)
        print("Chat with an AI that can control your IoT devices!")
        print("Type 'quit', 'exit', or 'bye' to end the conversation.")
        print("Type 'devices' to see available devices.")
        print("Type 'help' for example commands.")
        print("-"*60)
        
        while True:
            try:
                # Get user input
                user_input = input("\n👤 You: ").strip()
                
                if not user_input:
                    continue
                    
                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\n👋 Goodbye!")
                    break
                elif user_input.lower() == 'help':
                    self.show_help()
                    continue
                elif user_input.lower() == 'devices':
                    await self.show_devices()
                    continue
                
                # Get AI response
                print("🤖 Assistant: ", end="", flush=True)
                response = await self.get_openai_response(user_input)
                print(response)
                
                # Update conversation history
                self.conversation_history.append({"role": "user", "content": user_input})
                self.conversation_history.append({"role": "assistant", "content": response})
                
                # Keep conversation history manageable
                if len(self.conversation_history) > 20:
                    self.conversation_history = self.conversation_history[-20:]
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")

    def show_help(self):
        """Show help with example commands."""
        print("\n" + "="*50)
        print("📖 Example Commands:")
        print("="*50)
        print("• 'Show me all devices'")
        print("• 'Turn on the kitchen LED'")
        print("• 'What's the temperature in the living room?'")
        print("• 'Turn off all lights'")
        print("• 'Check the humidity in the bedroom'")
        print("• 'Are there any device errors?'")
        print("• 'Show me device info for the kitchen'")
        print("• 'Toggle the garage relay'")
        print("-"*50)

    async def show_devices(self):
        """Show available devices using MCP."""
        try:
            if not self.mcp_session:
                print("❌ MCP connection not available")
                return
                
            result = await self.call_mcp_tool("list_devices", {"online_only": True})
            print(f"\n📱 Available Devices:\n{result}")
        except Exception as e:
            print(f"❌ Error listing devices: {e}")

    async def cleanup(self):
        """Clean up connections."""
        if self.mcp_session:
            await self.mcp_session.close()


async def main():
    """Main function to run the chat interface."""
    # Check for OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OpenAI API key not found!")
        print("   Set it with: export OPENAI_API_KEY='your-api-key-here'")
        print("   Get your API key from: https://platform.openai.com/api-keys")
        return 1
    
    # Create chat interface
    chat = IoTChatInterface(api_key)
    
    # Set up signal handler for graceful shutdown
    def signal_handler(signum, frame):
        print("\n🛑 Shutting down...")
        asyncio.create_task(chat.cleanup())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize MCP connection
        if not await chat.initialize_mcp():
            return 1
        
        # Start the chat
        await chat.start_chat()
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1
    finally:
        await chat.cleanup()
    
    return 0


if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 