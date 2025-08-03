#!/usr/bin/env python3
"""
FastMCP Chat Demo Startup Script

This script starts all necessary services for the FastMCP chat demo:
1. Mock ESP32 devices (optional)
2. FastMCP-enabled chat interface

Usage:
    export OPENAI_API_KEY="your-api-key-here"
    python start_fastmcp_chat.py
    
    # With mock devices:
    python start_fastmcp_chat.py --with-devices

    # Custom MQTT broker:
    python start_fastmcp_chat.py --mqtt-broker 192.168.1.100
"""

import argparse
import asyncio
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


class FastMCPChatDemo:
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
            print("   cd server && python start_fastmcp_chat.py")
            return False
            
        # Check if FastMCP chat exists
        if not Path("fastmcp_chat.py").exists():
            print("❌ FastMCP chat interface not found")
            print("   Make sure fastmcp_chat.py exists in the current directory")
            return False
            
        return True

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
                stderr = process.stderr.read() if process.stderr else "No error output"
                print(f"Error: {stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting mock devices: {e}")
            return False

    async def start_fastmcp_chat(self, mqtt_broker: str, mqtt_port: int, db_path: str):
        """Start the FastMCP chat interface."""
        try:
            print("💬 Starting FastMCP chat interface...")
            print("\n" + "="*60)
            print("🎉 FASTMCP CHAT DEMO STARTING!")
            print("="*60)
            print("Services running:")
            if self.processes:
                print("  ✅ Mock ESP32 devices")
            print("  🔄 FastMCP bridge (will auto-start)")
            print("  💬 AI chat interface")
            print("="*60)
            
            # Import and run the FastMCP chat interface
            from fastmcp_chat import FastMCPChatInterface
            
            # Build bridge command
            bridge_command = [
                sys.executable, "fastmcp_bridge_server.py",
                "--stdio",
                "--mqtt-broker", mqtt_broker,
                "--mqtt-port", str(mqtt_port),
                "--db-path", db_path,
                "--log-level", "ERROR"  # Minimize logging for clean chat
            ]
            
            api_key = os.getenv("OPENAI_API_KEY")
            chat = FastMCPChatInterface(api_key, bridge_command)
            chat.setup_signal_handlers()
            
            # Initialize and start chat
            if await chat.initialize_fastmcp():
                await chat.start_chat()
            else:
                print("❌ Failed to initialize FastMCP chat interface")
                return False
                
            await chat.cleanup()
            return True
                
        except ImportError as e:
            print(f"❌ Error importing FastMCP chat interface: {e}")
            print("   Make sure fastmcp_chat.py is in the current directory")
            return False
        except Exception as e:
            print(f"❌ Error starting FastMCP chat: {e}")
            import traceback
            traceback.print_exc()
            return False

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
            
        print("✅ Cleanup complete")

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.running = False
            self.cleanup()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def run(self, with_devices: bool = False, mqtt_broker: str = "localhost", mqtt_port: int = 1883, db_path: str = "fastmcp_chat.db"):
        """Run the complete FastMCP chat demo."""
        print("🚀 Starting FastMCP Chat Demo")
        print("="*40)
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Check requirements
        if not self.check_requirements():
            return 1
        
        try:
            # Start mock devices if requested
            if with_devices:
                if not self.start_mock_devices():
                    print("⚠️  Continuing without mock devices...")
            else:
                print("ℹ️  Skipping mock devices (use --with-devices to enable)")
            
            # Start FastMCP chat interface
            success = await self.start_fastmcp_chat(mqtt_broker, mqtt_port, db_path)
            
            if not success:
                return 1
                
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            return 1
        finally:
            if self.running:
                self.cleanup()
        
        return 0


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="FastMCP Chat Demo")
    parser.add_argument("--with-devices", action="store_true",
                       help="Start mock ESP32 devices")
    parser.add_argument("--mqtt-broker", default="localhost",
                       help="MQTT broker hostname (default: localhost)")
    parser.add_argument("--db-path", default="fastmcp_chat.db",
                       help="Database path (default: fastmcp_chat.db)")
    parser.add_argument("--mqtt-port", type=int, default=1883,
                       help="MQTT broker port (default: 1883)")
    
    args = parser.parse_args()
    
    demo = FastMCPChatDemo()
    return await demo.run(
        with_devices=args.with_devices,
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        db_path=args.db_path
    )


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted")
        sys.exit(0)