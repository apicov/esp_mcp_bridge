#!/usr/bin/env python3
"""
Remote FastMCP Chat Interface

Chat interface that connects to a remote FastMCP bridge server over HTTP/WebSocket.
This allows you to run the bridge on a server and the chat on your desktop.

Usage:
    # Connect to remote server
    export OPENAI_API_KEY="your-api-key-here"
    python remote_fastmcp_chat.py --remote-host 192.168.1.100
    
    # Custom port
    python remote_fastmcp_chat.py --remote-host server.example.com --remote-port 8000
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Dict, List, Any, Optional
import signal

try:
    import openai
    from openai import OpenAI
except ImportError:
    print("❌ OpenAI library not found. Install with: pip install openai")
    sys.exit(1)

try:
    import aiohttp
    import websockets
except ImportError:
    print("❌ Required libraries not found. Install with: pip install aiohttp websockets")
    sys.exit(1)


class RemoteFastMCPClient:
    """Client for connecting to remote FastMCP bridge via HTTP/WebSocket"""
    
    def __init__(self, host: str, port: int = 8000):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.ws_url = f"ws://{host}:{port}/mcp"
        self.session = None
        self.websocket = None
        self.available_tools = []

    async def connect(self) -> bool:
        """Connect to the remote FastMCP bridge"""
        try:
            print(f"🔗 Connecting to remote FastMCP bridge at {self.host}:{self.port}...")
            
            # Create HTTP session
            self.session = aiohttp.ClientSession()
            
            # Test connection with health check
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ Server healthy: {health_data.get('service', 'Unknown')}")
                else:
                    print(f"❌ Server health check failed: {response.status}")
                    return False
            
            # Get available tools
            async with self.session.get(f"{self.base_url}/tools") as response:
                if response.status == 200:
                    tools_data = await response.json()
                    self.available_tools = tools_data.get('tools', [])
                    print(f"✅ Connected! Available tools: {len(self.available_tools)}")
                    for tool in self.available_tools:
                        print(f"  - {tool['name']}: {tool['description']}")
                    return True
                else:
                    print(f"❌ Failed to get tools: {response.status}")
                    return False
                    
        except aiohttp.ClientError as e:
            print(f"❌ Connection failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any] = None) -> Any:
        """Call a tool on the remote FastMCP bridge"""
        if not self.session:
            raise RuntimeError("Not connected to remote bridge")
        
        arguments = arguments or {}
        
        try:
            # Use HTTP POST to call tool
            url = f"{self.base_url}/tools/{tool_name}"
            payload = {"arguments": arguments}
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    result_data = await response.json()
                    if result_data.get("success"):
                        return result_data.get("result")
                    else:
                        return {"error": result_data.get("error", "Unknown error")}
                else:
                    error_text = await response.text()
                    return {"error": f"HTTP {response.status}: {error_text}"}
                    
        except Exception as e:
            return {"error": f"Request failed: {e}"}

    async def disconnect(self):
        """Disconnect from the remote bridge"""
        try:
            if self.websocket:
                await self.websocket.close()
            if self.session:
                await self.session.close()
            print("✅ Disconnected from remote bridge")
        except Exception as e:
            print(f"⚠️  Error disconnecting: {e}")

    # Convenience methods
    async def list_devices(self) -> Any:
        return await self.call_tool("list_devices")

    async def read_all_sensors(self, device_ids: List[str] = None) -> Any:
        args = {}
        if device_ids:
            args["device_ids"] = device_ids
        return await self.call_tool("read_all_sensors", args)

    async def control_actuator(self, device_id: str, actuator_type: str, action: str) -> Any:
        return await self.call_tool("control_actuator", {
            "device_id": device_id,
            "actuator_type": actuator_type,
            "action": action
        })

    async def get_system_status(self) -> Any:
        return await self.call_tool("get_system_status")


class RemoteFastMCPChatInterface:
    """Chat interface for remote FastMCP bridge"""
    
    def __init__(self, openai_api_key: str, remote_host: str, remote_port: int = 8000):
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.remote_client = RemoteFastMCPClient(remote_host, remote_port)
        self.conversation_history: List[Dict] = []
        
        # Enhanced system prompt for remote FastMCP
        self.system_prompt = """You are an AI assistant controlling IoT devices through a remote FastMCP bridge.

You have access to these IoT device control tools:
- list_devices: List all connected IoT devices
- read_sensor: Read sensor data from a single device/sensor
- read_all_sensors: Read multiple sensors from multiple devices at once (PREFERRED for "all sensors")
- control_actuator: Control device actuators (LEDs, relays, etc.)
- get_device_info: Get detailed device information
- query_devices: Find devices by capabilities
- get_alerts: Check for system alerts and errors
- get_system_status: Get overall system health
- get_device_metrics: Get device performance metrics

IMPORTANT: You're connected to a REMOTE IoT system. Always:
1. Use read_all_sensors for "all sensors" requests (never multiple read_sensor calls)
2. Make multiple function calls in parallel when users request multiple operations
3. Provide comprehensive summaries since you're working with remote data
4. Be proactive - suggest actions based on sensor readings
5. If there are connection issues, inform the user clearly

Available devices typically include: esp32_kitchen, esp32_living_room, esp32_bedroom
Common sensors: temperature, humidity, pressure, light
Common actuators: led, relay, buzzer

Execute all required function calls immediately and provide complete results."""

    async def initialize(self) -> bool:
        """Initialize connection to remote FastMCP bridge"""
        return await self.remote_client.connect()

    async def process_message(self, user_message: str) -> str:
        """Process user message with OpenAI and remote FastMCP tools"""
        try:
            # Add user message to conversation
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            # Convert remote tools to OpenAI format
            openai_tools = []
            for tool in self.remote_client.available_tools:
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool.get("parameters", {
                            "type": "object",
                            "properties": {},
                            "required": []
                        })
                    }
                }
                openai_tools.append(openai_tool)
            
            # Create OpenAI completion with tools
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.conversation_history
                ],
                tools=openai_tools,
                tool_choice="auto",
                temperature=0.1
            )
            
            message = response.choices[0].message
            tool_calls = message.tool_calls
            
            # Add assistant message to conversation
            self.conversation_history.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [{"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}} for tc in tool_calls] if tool_calls else None
            })
            
            # Process tool calls if any
            if tool_calls:
                print("\n🔧 Executing remote device operations...")
                
                # Execute all tool calls in parallel
                tool_results = await asyncio.gather(*[
                    self.remote_client.call_tool(
                        tc.function.name,
                        json.loads(tc.function.arguments)
                    ) for tc in tool_calls
                ], return_exceptions=True)
                
                # Add tool results to conversation
                for i, (tool_call, result) in enumerate(zip(tool_calls, tool_results)):
                    if isinstance(result, Exception):
                        result = {"error": str(result)}
                    
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result, default=str, indent=2)
                    })
                
                # Get final response with tool results
                final_response = self.openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        *self.conversation_history
                    ],
                    temperature=0.1
                )
                
                final_message = final_response.choices[0].message.content
                self.conversation_history.append({
                    "role": "assistant",
                    "content": final_message
                })
                
                return final_message
            else:
                return message.content or "I understand, but I don't have a specific response."
                
        except Exception as e:
            error_msg = f"Error processing message: {e}"
            print(f"❌ {error_msg}")
            return f"Sorry, I encountered an error: {error_msg}"

    async def start_chat(self):
        """Start the interactive chat session"""
        print("\n" + "="*60)
        print("🌐 REMOTE FASTMCP IoT CHAT INTERFACE READY!")
        print("="*60)
        print(f"Connected to: {self.remote_client.host}:{self.remote_client.port}")
        print("You can now chat with an AI that controls your remote IoT devices!")
        print("\nTry commands like:")
        print("  • 'Show me all devices'")
        print("  • 'Read all sensors'")
        print("  • 'Turn on the kitchen LED'")
        print("  • 'What's the system status?'")
        print("\nType 'quit' or 'exit' to stop")
        print("="*60)
        
        while True:
            try:
                # Get user input
                user_input = input("\n💬 You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                print("🤖 Assistant: ", end="", flush=True)
                
                # Process the message
                response = await self.process_message(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n\n👋 Chat interrupted. Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error in chat: {e}")

    async def cleanup(self):
        """Clean up resources"""
        await self.remote_client.disconnect()

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            print("\n🛑 Received interrupt signal...")
            raise KeyboardInterrupt()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point for remote FastMCP chat"""
    parser = argparse.ArgumentParser(description="Remote FastMCP IoT Chat Interface")
    parser.add_argument("--remote-host", required=True,
                       help="Hostname or IP of remote FastMCP bridge server")
    parser.add_argument("--remote-port", type=int, default=8000,
                       help="Port of remote FastMCP bridge server (default: 8000)")
    parser.add_argument("--mqtt-broker", default="localhost",
                       help="MQTT broker for remote bridge (info only)")
    parser.add_argument("--mqtt-port", type=int, default=1883,
                       help="MQTT port for remote bridge (info only)")
    
    args = parser.parse_args()
    
    # Check OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OpenAI API key not found!")
        print("   Set it with: export OPENAI_API_KEY='your-api-key-here'")
        print("   Get your API key from: https://platform.openai.com/api-keys")
        return 1
    
    # Create chat interface
    chat = RemoteFastMCPChatInterface(api_key, args.remote_host, args.remote_port)
    chat.setup_signal_handlers()
    
    try:
        print(f"🚀 Starting Remote FastMCP Chat Interface...")
        print(f"🎯 Target: {args.remote_host}:{args.remote_port}")
        
        # Initialize connection
        if not await chat.initialize():
            print("❌ Failed to connect to remote FastMCP bridge")
            print("\nTroubleshooting:")
            print(f"  1. Check if bridge server is running: http://{args.remote_host}:{args.remote_port}/health")
            print(f"  2. Verify network connectivity to {args.remote_host}")
            print("  3. Check firewall settings on the remote server")
            return 1
        
        # Start chat
        await chat.start_chat()
        
    except KeyboardInterrupt:
        print("\n🛑 Chat interrupted")
    except Exception as e:
        print(f"❌ Error running remote FastMCP chat: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await chat.cleanup()
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Remote FastMCP chat stopped")
        sys.exit(0)