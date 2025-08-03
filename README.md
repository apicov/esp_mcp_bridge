# ESP32 MCP-MQTT Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.1+-blue.svg)](https://docs.espressif.com/projects/esp-idf/en/latest/)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.0+-purple.svg)](https://modelcontextprotocol.io/)

A production-ready system that bridges ESP32 IoT devices with Large Language Models using MQTT and the Model Context Protocol (MCP). Enables natural language control and monitoring of IoT devices through AI assistants.

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

### 5. Try the Chat Demo
```bash
# Install OpenAI dependencies
cd server
pip install -r requirements-chat.txt

# Set OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Start complete demo (includes broker, mock devices, and chat interface)
python start_chat_demo.py
```

### 6. LLM Integration (Claude Desktop)
Add to your Claude Desktop configuration:
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

## Documentation

- **[Comprehensive Code Guide](ESP32_MCP_BRIDGE_COMPREHENSIVE_GUIDE.md)** - Complete architecture and code analysis
- **[Getting Started Guide](docs/setup_guide.md)** - Complete setup instructions
- **[ESP32 Firmware Guide](firmware/README.md)** - ESP32 development
- **[Python Server Guide](server/README.md)** - MCP server setup
- **[Chat Demo Guide](server/CHAT_DEMO_README.md)** - OpenAI chat interface
- **[Architecture Overview](docs/enhanced-features.md)** - System design
- **[Developer Guide](CLAUDE.md)** - Development commands and workflows

## Features

- **Enterprise Security**: TLS/SSL, device authentication, certificates
- **Real-time Monitoring**: Metrics, alerts, device health tracking
- **High Performance**: Batch operations, streaming, optimization
- **Production Ready**: Error recovery, logging, diagnostics
- **Modular Design**: Clean architecture, extensible components
- **Easy Integration**: Simple APIs, comprehensive examples

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
# Custom MQTT broker
python -m mcp_mqtt_bridge --mqtt-broker 192.168.1.100

# With authentication
python -m mcp_mqtt_bridge --mqtt-username user --mqtt-password pass

# Custom database location
python -m mcp_mqtt_bridge --db-path /tmp/test.db

# Longer device timeout
python -m mcp_mqtt_bridge --device-timeout 10

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
