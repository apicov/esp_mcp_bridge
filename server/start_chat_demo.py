#!/usr/bin/env python3
"""
Complete IoT Chat Demo Startup Script

This script starts all necessary services and then launches the chat interface:
1. Mock ESP32 devices 
2. MCP-MQTT Bridge
3. Chat interface with OpenAI

Note: Assumes MQTT broker is already running externally

Usage:
    export OPENAI_API_KEY="your-api-key-here"
    python start_chat_demo.py
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


class IoTChatDemo:
    def __init__(self):
        self.processes = []
        self.running = True
        
    def check_requirements(self) -> bool:
        """Check if all requirements are met."""
        # Check OpenAI API key
        if not os.getenv("OPENAI_API_KEY"):
            print("❌ OpenAI API key not found!")
            print("   Set it with: export OPENAI_API_KEY='your-api-key-here'")
            print("   Get your API key from: https://platform.openai.com/api-keys")
            return False
            
        # Check if we're in the right directory
        if not Path("mcp_mqtt_bridge").exists():
            print("❌ Please run this script from the server directory")
            print("   cd server && python start_chat_demo.py")
            return False
            
        # Check if virtual environment is activated
        if not sys.prefix != sys.base_prefix:
            print("⚠️  Virtual environment not detected")
            print("   Recommend: source venv/bin/activate")
            
        return True

    # def start_mosquitto(self) -> bool:
    #     """Start Mosquitto MQTT broker."""
    #     try:
    #         print("🦟 Starting Mosquitto MQTT broker...")
    #         
    #         # Kill any existing mosquitto processes
    #         subprocess.run(["pkill", "-f", "mosquitto"], capture_output=True)
    #         time.sleep(1)
    #         
    #         # Start mosquitto
    #         process = subprocess.Popen(
    #             ["mosquitto", "-v"],
    #             stdout=subprocess.PIPE,
    #             stderr=subprocess.PIPE,
    #             text=True
    #         )
    #         
    #         self.processes.append(("mosquitto", process))
    #         
    #         # Wait a moment for it to start
    #         time.sleep(2)
    #         
    #         if process.poll() is None:
    #             print("✅ Mosquitto started successfully")
    #             return True
    #         else:
    #             print("❌ Failed to start Mosquitto")
    #             return False
    #             
    #     except FileNotFoundError:
    #         print("❌ Mosquitto not found. Install with: sudo apt install mosquitto")
    #         return False
    #     except Exception as e:
    #         print(f"❌ Error starting Mosquitto: {e}")
    #         return False

    def start_mock_devices(self) -> bool:
        """Start mock ESP32 devices."""
        try:
            print("🤖 Starting mock ESP32 devices...")
            
            process = subprocess.Popen(
                [sys.executable, "examples/mock_esp32_device.py", "--devices", "3"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes.append(("mock_devices", process))
            
            # Wait for devices to start
            time.sleep(3)
            
            if process.poll() is None:
                print("✅ Mock devices started successfully")
                return True
            else:
                print("❌ Failed to start mock devices")
                return False
                
        except Exception as e:
            print(f"❌ Error starting mock devices: {e}")
            return False

    def start_bridge(self) -> bool:
        """Start MCP-MQTT bridge."""
        try:
            print("🌉 Starting MCP-MQTT bridge...")
            
            process = subprocess.Popen(
                [sys.executable, "-m", "mcp_mqtt_bridge", "--log-level", "WARNING"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes.append(("bridge", process))
            
            # Wait for bridge to start
            time.sleep(3)
            
            if process.poll() is None:
                print("✅ MCP bridge started successfully")
                return True
            else:
                print("❌ Failed to start MCP bridge")
                return False
                
        except Exception as e:
            print(f"❌ Error starting MCP bridge: {e}")
            return False

    async def start_chat(self):
        """Start the chat interface."""
        try:
            print("💬 Starting chat interface...")
            print("\n" + "="*60)
            print("🎉 ALL SERVICES RUNNING!")
            print("="*60)
            print("You can now chat with an AI that controls your IoT devices!")
            print("="*60)
            
            # Import and run the chat interface
            from chat_with_devices import IoTChatInterface
            
            api_key = os.getenv("OPENAI_API_KEY")
            chat = IoTChatInterface(api_key)
            
            if await chat.initialize_mcp():
                await chat.start_chat()
            else:
                print("❌ Failed to initialize MCP connection")
                
        except ImportError as e:
            print(f"❌ Error importing chat interface: {e}")
            print("   Make sure to install requirements: pip install -r requirements-chat.txt")
        except Exception as e:
            print(f"❌ Error starting chat: {e}")

    def cleanup(self):
        """Stop all running processes."""
        print("\n🛑 Shutting down services...")
        
        for name, process in self.processes:
            try:
                print(f"   Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"   Force killing {name}...")
                process.kill()
            except Exception as e:
                print(f"   Error stopping {name}: {e}")
        
        # Clean up mosquitto specifically
        # try:
        #     subprocess.run(["pkill", "-f", "mosquitto"], capture_output=True)
        # except:
        #     pass
            
        print("✅ Cleanup complete")

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.running = False
            self.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run(self):
        """Run the complete demo."""
        print("🚀 Starting IoT Chat Demo")
        print("="*40)
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Check requirements
        if not self.check_requirements():
            return 1
        
        try:
            # Start services in order
            # Note: Assumes MQTT broker (mosquitto) is already running
            print("📋 Assuming MQTT broker is already running...")
            
            if not self.start_mock_devices():
                return 1
                
            if not self.start_bridge():
                return 1
            
            # Start chat interface
            await self.start_chat()
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            return 1
        finally:
            if self.running:
                self.cleanup()
        
        return 0


async def main():
    """Main entry point."""
    demo = IoTChatDemo()
    return await demo.run()


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted")
        sys.exit(0) 