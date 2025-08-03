# ESP32 MCP-MQTT Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.1+-blue.svg)](https://docs.espressif.com/projects/esp-idf/en/latest/)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.0+-purple.svg)](https://modelcontextprotocol.io/)

A production-ready system that bridges ESP32 IoT devices with Large Language Models using MQTT and the Model Context Protocol (MCP). Features FastMCP support for high-performance communication, remote server capabilities, and natural language control of IoT devices through AI assistants.

## Project Structure

```
esp32-mcp-bridge/
├── firmware/                   # ESP32 firmware components
│   ├── components/             # ESP-IDF components
│   │   └── esp_mcp_bridge/     # Main bridge library
│   ├── examples/               # Example projects
│   └── tests/                  # Firmware tests
├── server/                     # Python MCP server
│   ├── mcp_mqtt_bridge/        # Core server modules
│   ├── tests/                  # Server tests
│   └── examples/               # Usage examples
├── docs/                       # Documentation
├── deployment/                 # Deployment configurations
├── tools/                      # Development tools
└── config/                     # Configuration templates
```

## Quick Start

### Prerequisites
- Python 3.11+ 
- MQTT broker (install Mosquitto: `sudo apt install mosquitto` or `brew install mosquitto`)
- ESP-IDF v5.1+ (for ESP32 development)

### 1. Start MQTT Broker
```bash
# Start Mosquitto MQTT broker
mosquitto

# Or using Docker
docker run -it -p 1883:1883 eclipse-mosquitto
```

### 2. Python MCP Server Setup
```bash
# Navigate to server directory
cd server

# Install dependencies
pip install -r requirements.txt

# Start the server with default settings
python -m mcp_mqtt_bridge

# Or with custom MQTT broker
python -m mcp_mqtt_bridge --mqtt-broker localhost --mqtt-port 1883

# Or with database path
python -m mcp_mqtt_bridge --db-path ./data/bridge.db

# See all options
python -m mcp_mqtt_bridge --help
```

### 3. Test with Mock Devices (No ESP32 needed)
```bash
# In a new terminal, start mock ESP32 devices
cd server
python examples/mock_esp32_device.py

# This creates simulated ESP32 devices for testing
```

### 4. ESP32 Firmware (Real Hardware)
```bash
# Setup ESP-IDF environment
source $IDF_PATH/export.sh

# Navigate to firmware example
cd firmware/examples/basic_example

# Configure WiFi and MQTT settings
idf.py menuconfig

# Build and flash to ESP32
idf.py build flash monitor
```

### 5. Try the Chat Demos

#### FastMCP Chat (Recommended)
```bash
# Install dependencies
cd server
pip install -r requirements.txt
pip install -r requirements-remote.txt

# Set OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Start FastMCP chat with mock devices
python start_fastmcp_chat.py --with-devices

# Or original chat demo
python start_chat_demo.py
```

#### Remote Chat (Server + Desktop)
```bash
# On server (Raspberry Pi, VPS, etc.)
python -m mcp_mqtt_bridge --enable-mcp-server --mcp-host 0.0.0.0

# On your desktop
python remote_fastmcp_chat.py --remote-host your-server-ip
```

### 6. LLM Integration

#### Claude Desktop (Standard MCP)
```json
{
  "mcp-servers": {
    "iot-bridge": {
      "command": "python",
      "args": ["-m", "mcp_mqtt_bridge"],
      "env": {"MQTT_BROKER": "localhost"},
      "cwd": "/path/to/esp_mcp_bridge/server"
    }
  }
}
```

#### FastMCP Integration
```bash
# Use FastMCP bridge server for direct integration
python fastmcp_bridge_server.py --stdio

# Or programmatic client
python fastmcp_client_example.py
```

## Documentation

### Core Documentation
- **[Comprehensive Code Guide](ESP32_MCP_BRIDGE_COMPREHENSIVE_GUIDE.md)** - Complete architecture and code analysis
- **[Getting Started Guide](docs/setup_guide.md)** - Complete setup instructions
- **[ESP32 Firmware Guide](firmware/README.md)** - ESP32 development
- **[Python Server Guide](server/README.md)** - MCP server setup
- **[Developer Guide](CLAUDE.md)** - Development commands and workflows

### Chat and Remote Features
- **[FastMCP Chat Guide](server/FASTMCP_CHAT_README.md)** - FastMCP chat interface
- **[Remote Setup Guide](server/REMOTE_SETUP_GUIDE.md)** - Server and desktop setup
- **[MQTT Configuration Guide](server/MQTT_CONFIGURATION_GUIDE.md)** - Custom ports and security

### Legacy and Examples
- **[Original Chat Demo](server/CHAT_DEMO_README.md)** - OpenAI chat interface
- **[Architecture Overview](docs/enhanced-features.md)** - System design

## Features

### Core Features
- **Enterprise Security**: TLS/SSL, device authentication, certificates
- **Real-time Monitoring**: Metrics, alerts, device health tracking
- **High Performance**: Batch operations, streaming, optimization
- **Production Ready**: Error recovery, logging, diagnostics
- **Modular Design**: Clean architecture, extensible components

### FastMCP Features
- **FastMCP Support**: High-performance MCP implementation
- **Remote Connectivity**: Server-desktop architecture
- **Parallel Operations**: Simultaneous device control
- **Custom MQTT Ports**: Configurable broker settings
- **Multiple Chat Interfaces**: Local and remote options

### Integration Options
- **OpenAI Chat**: Natural language device control
- **Claude Desktop**: Direct MCP integration
- **REST API**: HTTP endpoints for web integration
- **WebSocket**: Real-time communication
- **Programmatic Client**: Python SDK for automation

## Use Cases

- **Smart Home**: Control lights, sensors, HVAC through natural language
- **Industrial IoT**: Monitor equipment, control processes via AI
- **Agriculture**: Manage irrigation, environmental controls with LLMs
- **Research**: Rapid prototyping of IoT-AI integration projects

## Troubleshooting

### Server Won't Start
```bash
# Check if MQTT broker is running
mosquitto_pub -h localhost -t test/topic -m "test"

# Check Python dependencies
pip list | grep -E "(mcp|paho-mqtt|pydantic)"

# Run with debug logging
python -m mcp_mqtt_bridge --log-level DEBUG
```

### No Devices Showing Up
```bash
# Test with mock devices first
python server/examples/mock_esp32_device.py

# Check MQTT messages
mosquitto_sub -h localhost -t "devices/+/+/+/+"

# Verify server is receiving messages
python -m mcp_mqtt_bridge --log-level DEBUG
```

### ESP32 Connection Issues
```bash
# Check ESP32 serial output
idf.py monitor

# Verify WiFi and MQTT settings
idf.py menuconfig

# Check MQTT broker connectivity from ESP32 location
```

### Common Command Line Options
```bash
# Custom MQTT broker and port
python -m mcp_mqtt_bridge --mqtt-broker 192.168.1.100 --mqtt-port 1884

# With authentication
python -m mcp_mqtt_bridge --mqtt-username user --mqtt-password pass

# Remote server with FastMCP
python -m mcp_mqtt_bridge --enable-mcp-server --mcp-host 0.0.0.0 --use-fastmcp

# FastMCP bridge server
python fastmcp_bridge_server.py --mqtt-broker localhost --mqtt-port 1883

# Remote FastMCP chat
python remote_fastmcp_chat.py --remote-host 192.168.1.100

# All options
python -m mcp_mqtt_bridge --help
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Links

- [ESP-IDF Documentation](https://docs.espressif.com/projects/esp-idf/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MQTT Protocol](https://mqtt.org/)
- [Issue Tracker](https://github.com/your-org/esp32-mcp-bridge/issues)
