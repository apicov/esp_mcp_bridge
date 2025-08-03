# FastMCP Chat Interface

A high-performance chat interface for controlling ESP32 IoT devices using FastMCP (Model Context Protocol).

## Features

- **Direct FastMCP Integration**: Uses FastMCP for efficient communication with IoT devices
- **Enhanced AI Assistant**: Advanced system prompt optimized for IoT device control
- **Parallel Operations**: Execute multiple device commands simultaneously
- **Real-time Device Control**: Immediate response to device commands
- **Comprehensive Tools**: 9 specialized tools for complete IoT management

## Quick Start

### 1. Set up your environment

```bash
# Set OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Activate virtual environment
source venv/bin/activate
```

### 2. Start the FastMCP chat

```bash
# Simple start (no mock devices)
python start_fastmcp_chat.py

# With mock ESP32 devices for testing
python start_fastmcp_chat.py --with-devices

# Custom MQTT broker
python start_fastmcp_chat.py --mqtt-broker 192.168.1.100
```

### 3. Chat with your devices

```
💬 You: Show me all devices
🤖 Assistant: I can see you have 3 ESP32 devices connected...

💬 You: Read all sensors
🤖 Assistant: Here are the current readings from all your sensors...

💬 You: Turn on the kitchen LED
🤖 Assistant: I've turned on the LED in the kitchen device...
```

## Available Commands

### Device Management
- "Show me all devices"
- "What devices are online?"
- "Get device information for esp32_kitchen"

### Sensor Reading
- "Read all sensors" (recommended for multiple readings)
- "What's the temperature in the living room?"
- "Check humidity levels"
- "Show me sensor history for the last hour"

### Device Control
- "Turn on the kitchen LED"
- "Turn off all lights"
- "Toggle the bedroom relay"

### System Monitoring
- "Check system status"
- "Are there any alerts?"
- "Show device metrics"

## Advanced Usage

### Direct FastMCP Client

Use the FastMCP client programmatically:

```python
from fastmcp_client_example import FastMCPClient

client = FastMCPClient()
await client.connect()

devices = await client.list_devices()
sensors = await client.read_all_sensors()
await client.control_actuator("esp32_kitchen", "led", "on")

await client.disconnect()
```

### Standalone FastMCP Server

Run just the FastMCP bridge server:

```bash
# Stdio mode for MCP clients
python fastmcp_bridge_server.py --stdio

# With custom settings
python fastmcp_bridge_server.py --mqtt-broker localhost --db-path custom.db
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastMCP Chat  │    │  FastMCP Bridge │    │   ESP32 Devices │
│   Interface     │◄──►│     Server      │◄──►│   via MQTT      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌─────────┐              ┌─────────┐           ┌─────────────┐
    │ OpenAI  │              │ SQLite  │           │ Mock Devices│
    │   API   │              │Database │           │   (optional)│
    └─────────┘              └─────────┘           └─────────────┘
```

## Available Tools

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `list_devices` | List connected devices | "Show all devices" |
| `read_sensor` | Read single sensor | "Kitchen temperature" |
| `read_all_sensors` | Read multiple sensors | "Read all sensors" |
| `control_actuator` | Control actuators | "Turn on LED" |
| `get_device_info` | Device details | "Device info for kitchen" |
| `query_devices` | Search by capabilities | "Devices with temperature sensors" |
| `get_alerts` | System alerts | "Any errors?" |
| `get_system_status` | System overview | "System status" |
| `get_device_metrics` | Performance data | "Device metrics" |

## Troubleshooting

### Connection Issues
```bash
# Test FastMCP functionality
python test_fastmcp_simple.py

# Test bridge server
python fastmcp_bridge_server.py --help
```

### MQTT Issues
```bash
# Check if MQTT broker is running
mosquitto -v

# Start with Docker
docker run -d -p 1883:1883 eclipse-mosquitto
```

### API Key Issues
```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test OpenAI connection
python -c "import openai; print('OpenAI library works')"
```

## Performance Features

- **Parallel Tool Calls**: Multiple device operations execute simultaneously
- **Efficient Communication**: FastMCP reduces protocol overhead
- **Smart Batching**: `read_all_sensors` reads multiple sensors in one call
- **Optimized Prompts**: AI assistant uses the most efficient tools

## Compared to Standard MCP Chat

| Feature | Standard MCP | FastMCP |
|---------|-------------|---------|
| Protocol Overhead | Higher | Lower |
| Parallel Operations | Limited | Full Support |
| Tool Registration | Manual | Automatic |
| Performance | Good | Excellent |
| Setup Complexity | Moderate | Simple |

## Files

- `fastmcp_chat.py` - Main FastMCP chat interface
- `start_fastmcp_chat.py` - Demo startup script
- `fastmcp_bridge_server.py` - Standalone FastMCP server
- `fastmcp_client_example.py` - Programmatic client example
- `test_fastmcp_simple.py` - Simple functionality tests

## Next Steps

1. **Try the chat**: `python start_fastmcp_chat.py --with-devices`
2. **Read the comprehensive guide**: See `ESP32_MCP_BRIDGE_COMPREHENSIVE_GUIDE.md`
3. **Deploy to production**: Use the deployment configs in `../deployment/`
4. **Integrate with your app**: Use `fastmcp_client_example.py` as a template