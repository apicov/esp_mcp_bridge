# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ESP32 MCP-MQTT Bridge is a production-ready system that bridges ESP32 IoT devices with Large Language Models using MQTT and the Model Context Protocol (MCP). The project consists of two main components:

1. **ESP32 Firmware** - C/C++ library using ESP-IDF for device-side MQTT communication
2. **Python MCP Server** - Python server that bridges MQTT messages to LLM tools via MCP

## Development Commands

### ESP32 Firmware Development
```bash
# Setup ESP-IDF environment (required before any ESP32 work)
source $IDF_PATH/export.sh

# Navigate to firmware example
cd firmware/examples/basic_example

# Configure project (WiFi credentials, MQTT broker, etc.)
idf.py menuconfig

# Build firmware
idf.py build

# Flash to device and monitor
idf.py flash monitor

# Build only
idf.py build

# Set target (if needed)
idf.py set-target esp32
```

### Python Server Development
```bash
# Navigate to server directory
cd server

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Run server with default settings
python -m mcp_mqtt_bridge

# Run server with custom MQTT broker
python -m mcp_mqtt_bridge --mqtt-broker localhost --db-path ./data/bridge.db

# Run tests
pytest

# Run tests with coverage
pytest --cov=mcp_mqtt_bridge --cov-report=html

# Run integration tests
pytest tests/integration/

# Run specific test
pytest tests/unit/test_database.py
```

### MQTT Broker Setup (for testing)
```bash
# Start MQTT broker with Docker
docker run -d -p 1883:1883 --name test-mosquitto eclipse-mosquitto

# Or using deployment config
cd deployment
docker-compose up -d
```

## Architecture Overview

### ESP32 Firmware Architecture
- **esp_mcp_bridge** - Main library providing MQTT-MCP bridge functionality
- **mcp_device** - Device abstraction layer for sensors and actuators
- Component-based ESP-IDF structure with proper CMakeLists.txt configuration
- Uses standardized MQTT topic structure: `devices/{device_id}/{sensors|actuators}/{name}/{data|command|status}`

### Python Server Architecture
The server follows a modular design with clear separation of concerns:

- **MCPMQTTBridge** (`bridge.py`) - Main coordinator orchestrating all components
- **MQTTManager** (`mqtt_manager.py`) - Handles MQTT client connections and message routing
- **DeviceManager** (`device_manager.py`) - Manages device state, timeouts, and capabilities
- **DatabaseManager** (`database.py`) - SQLite database operations for device data persistence
- **MCPServerManager** (`mcp_server.py`) - Implements MCP protocol tools for LLM integration
- **Data Models** (`data_models.py`) - Pydantic models for type-safe data structures

### Key Data Flow
1. ESP32 devices publish sensor data and capabilities via MQTT
2. MQTT Manager receives messages and routes to appropriate handlers
3. Device Manager updates device state and stores in database
4. MCP Server exposes LLM tools for device interaction
5. LLM commands flow back through the system to control actuators

### MQTT Topic Structure
- `devices/{device_id}/sensors/{sensor_name}/data` - Sensor readings
- `devices/{device_id}/actuators/{actuator_name}/command` - Actuator commands
- `devices/{device_id}/actuators/{actuator_name}/status` - Actuator status
- `devices/{device_id}/capabilities` - Device capability announcements
- `devices/{device_id}/status` - Device online/offline status
- `devices/{device_id}/error` - Error messages

## Configuration

### ESP32 Configuration
Use `idf.py menuconfig` to configure:
- WiFi credentials (Component config → MCP Bridge Configuration)
- MQTT broker settings
- TLS/SSL settings
- Device-specific settings

### Python Server Configuration
Configuration via YAML files in `server/config/`:
- `default.yaml` - Default settings
- `development.yaml` - Development overrides
- `production.yaml.example` - Production template

Key configuration options:
- MQTT broker connection details
- Database path
- Device timeout settings
- Logging configuration

## Testing Strategy

### ESP32 Testing
- Unit tests using ESP-IDF test framework
- Integration tests with mock MQTT broker
- Hardware-in-the-loop testing with actual devices

### Python Server Testing
- Unit tests in `tests/unit/` using pytest
- Integration tests in `tests/integration/` with real MQTT broker
- Mock ESP32 device simulator for system testing (`examples/mock_esp32_device.py`)

### System Integration Testing
Use `examples/system_integration_test.py` for end-to-end testing of the complete system.

## Important Development Notes

### ESP32 Development
- Always source ESP-IDF environment before building
- Use `idf.py menuconfig` to configure WiFi and MQTT settings
- Monitor ESP32 output with `idf.py monitor` for debugging
- ESP32 components follow ESP-IDF conventions with proper Kconfig integration

### Python Development
- All modules use type hints and Pydantic models for data validation
- Database operations are handled through the DatabaseManager abstraction
- MQTT message handling is event-driven with proper error handling
- MCP tools are automatically exposed to LLMs when the server runs

### Common Workflows
1. **Adding new sensor types**: Update both ESP32 device definitions and Python data models
2. **Adding MCP tools**: Extend MCPServerManager with new tool definitions
3. **Database changes**: Use migration scripts in `server/scripts/migrate_db.py`

## Demo and Examples

The project includes a complete chat demo:
```bash
# Start the complete chat demo
cd server
python start_chat_demo.py
```

This launches:
- Mock ESP32 devices
- MCP-MQTT bridge server
- OpenAI chat interface for natural language device control

The demo demonstrates real-time sensor monitoring and actuator control through natural language commands.