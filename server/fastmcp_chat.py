#!/usr/bin/env python3
"""
FastMCP Chat Interface with IoT Device Control

Advanced chat interface using FastMCP for direct, high-performance
communication with ESP32 IoT devices.

Usage:
    export OPENAI_API_KEY="your-api-key-here"
    python fastmcp_chat.py
    
    # For remote FastMCP bridge server:
    python fastmcp_chat.py --remote-host 192.168.1.100

Requirements:
    - OpenAI API key
    - FastMCP-enabled bridge running (local or remote)
    - Mock devices running (optional)
"""

import argparse
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


class FastMCPChatInterface:
    def __init__(self, openai_api_key: str, bridge_command: Optional[str] = None):
        """Initialize the FastMCP chat interface with OpenAI and direct FastMCP connection."""
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.mcp_session: Optional[ClientSession] = None
        self.available_tools: List[Dict] = []
        self.conversation_history: List[Dict] = []
        self._stdio_context = None
        self.bridge_process = None
        self.bridge_command = bridge_command or [
            sys.executable, "fastmcp_bridge_server.py", "--stdio", "--log-level", "WARNING"
        ]
        
        # Enhanced system prompt for FastMCP
        self.system_prompt = """You are an AI assistant that can control IoT devices through a FastMCP (Model Context Protocol) interface.

You have direct access to these IoT device control tools:
- list_devices: List all connected IoT devices
- read_sensor: Read sensor data from a single device/sensor
- read_all_sensors: Read multiple sensors from multiple devices at once (PREFERRED for "all sensors" requests)
- control_actuator: Control device actuators (LEDs, relays, etc.)
- get_device_info: Get detailed device information
- query_devices: Find devices by sensor/actuator capabilities
- get_alerts: Check for system alerts and errors
- get_system_status: Get overall system health
- get_device_metrics: Get device performance metrics

Available devices: esp32_kitchen, esp32_living_room, esp32_bedroom
Available sensors: temperature, humidity, pressure, light (always use lowercase)
Available actuators: led, relay, buzzer

IMPORTANT INSTRUCTIONS:
1. When users ask for "all sensors" or multiple readings, ALWAYS use read_all_sensors instead of multiple read_sensor calls
2. Make multiple function calls in parallel when users request multiple operations
3. Be proactive - if you see concerning sensor values, suggest actions
4. Use get_alerts to check for system issues when appropriate
5. Provide comprehensive summaries of all data collected

NEVER stop mid-task to ask permission - execute all required function calls immediately and provide complete results.

Examples of efficient usage:
- "Check all sensors" → use read_all_sensors (not multiple read_sensor calls)
- "Turn on all lights" → use control_actuator for each device in parallel
- "System status" → use get_system_status and get_alerts together
- "What devices are available" → use list_devices

Be confident, efficient, and provide actionable insights based on the IoT data you collect."""

    async def start_bridge_process(self) -> bool:
        """Start the FastMCP bridge process for stdio communication"""
        try:
            print("🚀 Starting FastMCP bridge server...")
            
            # Start the bridge process
            self.bridge_process = subprocess.Popen(
                self.bridge_command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Give it a moment to start
            await asyncio.sleep(2)
            
            if self.bridge_process.poll() is None:
                print("✅ FastMCP bridge server started successfully")
                return True
            else:
                print("❌ Failed to start FastMCP bridge server")
                stderr = self.bridge_process.stderr.read() if self.bridge_process.stderr else "No error output"
                print(f"Error: {stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting FastMCP bridge: {e}")
            return False

    async def initialize_fastmcp(self) -> bool:
        """Initialize FastMCP connection to the bridge"""
        try:
            print("🔗 Connecting to FastMCP bridge...")
            
            # Start bridge if not already running
            if not self.bridge_process:
                if not await self.start_bridge_process():
                    return False
            
            # Connect to the bridge via stdio
            server_params = StdioServerParameters(
                command=self.bridge_command[0],
                args=self.bridge_command[1:],
                env=None
            )
            
            self._stdio_context = stdio_client(server_params)
            read, write = await self._stdio_context.__aenter__()
            self.mcp_session = ClientSession(read, write)
            
            # Initialize the connection
            await self.mcp_session.initialize()
            
            # List available tools
            tools_result = await self.mcp_session.list_tools()
            
            # Convert MCP tools to OpenAI function format
            self.available_tools = []
            for tool in tools_result.tools:
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema if hasattr(tool, 'inputSchema') else {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
                self.available_tools.append(openai_tool)
            
            print(f"✅ Connected! Available tools: {len(self.available_tools)}")
            for tool in self.available_tools:
                name = tool['function']['name']
                desc = tool['function']['description']
                print(f"  - {name}: {desc}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize FastMCP: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def call_fastmcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a FastMCP tool and return the result"""
        try:
            if not self.mcp_session:
                raise RuntimeError("FastMCP session not initialized")
            
            # Call the tool
            result = await self.mcp_session.call_tool(tool_name, arguments)
            
            # Extract content from result
            if hasattr(result, 'content') and result.content:
                # Handle different content types
                content = result.content[0]
                if hasattr(content, 'text'):
                    try:
                        # Try to parse as JSON first
                        return json.loads(content.text)
                    except json.JSONDecodeError:
                        # Return as string if not JSON
                        return content.text
                else:
                    return str(content)
            else:
                return result
                
        except Exception as e:
            error_msg = f"Error calling FastMCP tool '{tool_name}': {e}"
            print(f"❌ {error_msg}")
            return {"error": error_msg}

    async def process_message(self, user_message: str) -> str:
        """Process user message with OpenAI and FastMCP tools"""
        try:
            # Add user message to conversation
            self.conversation_history.append({
                "role": "user",
                "content": user_message
            })
            
            # Create OpenAI completion with tools
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *self.conversation_history
                ],
                tools=self.available_tools,
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
                print("\n🔧 Executing device operations...")
                
                # Execute all tool calls in parallel for better performance
                tool_results = await asyncio.gather(*[
                    self.call_fastmcp_tool(
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
        print("🎉 FASTMCP IoT CHAT INTERFACE READY!")
        print("="*60)
        print("You can now chat with an AI that controls your IoT devices!")
        print("Try commands like:")
        print("  • 'Show me all devices'")
        print("  • 'Read all sensors'")
        print("  • 'Turn on the kitchen LED'")
        print("  • 'What's the temperature in the living room?'")
        print("  • 'Check system status'")
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
        try:
            if self._stdio_context:
                await self._stdio_context.__aexit__(None, None, None)
                
            if self.bridge_process:
                self.bridge_process.terminate()
                try:
                    self.bridge_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.bridge_process.kill()
                    
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            print("\n🛑 Received interrupt signal...")
            # The cleanup will be handled in the main function
            raise KeyboardInterrupt()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point for FastMCP chat"""
    parser = argparse.ArgumentParser(description="FastMCP IoT Chat Interface")
    parser.add_argument("--bridge-command", 
                       help="Custom command to start FastMCP bridge server")
    parser.add_argument("--mqtt-broker", default="localhost",
                       help="MQTT broker for FastMCP bridge (default: localhost)")
    parser.add_argument("--db-path", default="fastmcp_bridge.db",
                       help="Database path for FastMCP bridge")
    
    args = parser.parse_args()
    
    # Check OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OpenAI API key not found!")
        print("   Set it with: export OPENAI_API_KEY='your-api-key-here'")
        print("   Get your API key from: https://platform.openai.com/api-keys")
        return 1
    
    # Build bridge command
    bridge_command = None
    if args.bridge_command:
        bridge_command = args.bridge_command.split()
    else:
        bridge_command = [
            sys.executable, "fastmcp_bridge_server.py", 
            "--stdio", 
            "--mqtt-broker", args.mqtt_broker,
            "--db-path", args.db_path,
            "--log-level", "ERROR"  # Minimize bridge logging for clean chat
        ]
    
    # Create chat interface
    chat = FastMCPChatInterface(api_key, bridge_command)
    chat.setup_signal_handlers()
    
    try:
        print("🚀 Starting FastMCP IoT Chat Interface...")
        
        # Initialize FastMCP connection
        if not await chat.initialize_fastmcp():
            print("❌ Failed to initialize FastMCP connection")
            return 1
        
        # Start chat
        await chat.start_chat()
        
    except KeyboardInterrupt:
        print("\n🛑 Chat interrupted")
    except Exception as e:
        print(f"❌ Error running FastMCP chat: {e}")
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
        print("\n👋 FastMCP chat stopped")
        sys.exit(0)