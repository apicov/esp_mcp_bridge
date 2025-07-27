# MCP-MQTT Bridge Server Setup Guide

## Overview

The MCP-MQTT Bridge Server connects ESP32 IoT devices to Large Language Models (LLMs) using the Model Context Protocol. It acts as a translator between MQTT messages from ESP32 devices and MCP tools that LLMs can use.

## Architecture

```
ESP32 Devices  <--MQTT-->  Bridge Server  <--MCP-->  LLM/AI Assistant
     |                          |                           |
  Sensors &                 Database                   Natural Language
  Actuators              (Historical Data)              Interface
```

## Quick Start

### 1. Prerequisites

- Python 3.11 or higher
- MQTT broker (Mosquitto recommended)
- ESP32 devices with the MCP Bridge library

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/your-org/mcp-mqtt-bridge.git
cd mcp-mqtt-bridge

# Install dependencies
pip install -r requirements.txt

# Or use Docker
docker-compose up -d
```

### 3. Configuration

Create a `.env` file based on `.env.example`:

```bash
MQTT_BROKER=localhost
MQTT_PORT=1883
MQTT_USERNAME=your_username  # Optional
MQTT_PASSWORD=your_password  # Optional
DB_PATH=./data/iot_bridge.db
LOG_LEVEL=INFO
```

### 4. Running the Server

#### Option A: Direct Python
```bash
python mcp_mqtt_bridge.py --mqtt-broker localhost
```

#### Option B: Docker Compose
```bash
docker-compose up
```

#### Option C: As MCP Server (for LLM integration)
```bash
# The server implements stdio transport for MCP
python mcp_mqtt_bridge.py
```

## Features

### Available MCP Tools

1. **list_devices** - List all connected IoT devices
2. **read_sensor** - Read current or historical sensor data
3. **control_actuator** - Control device actuators (LED, relay, etc.)
4. **get_device_info** - Get detailed device information
5. **query_devices** - Search devices by capabilities
6. **get_alerts** - Retrieve device errors and alerts

### Data Persistence

- Sensor readings are stored in SQLite database
- Historical data can be queried via MCP tools
- Automatic cleanup of old data (configurable)

### Real-time Monitoring

- Device online/offline detection
- Automatic reconnection handling
- Error tracking and alerting

## Usage Examples

### With Claude Desktop

Add to your Claude configuration:

```json
{
  "mcp-servers": {
    "iot-bridge": {
      "command": "python",
      "args": ["/path/to/mcp_mqtt_bridge.py"],
      "env": {
        "MQTT_BROKER": "localhost"
      }
    }
  }
}
```

### Example Conversations

**User**: "What IoT devices are currently online?"

**Assistant**: I'll check the connected IoT devices for you.

*[Uses list_devices tool]*

Currently, there are 3 devices online:
- **esp32_kitchen_01**: Temperature and humidity sensors, LED control
- **esp32_garage_02**: Motion sensor, relay control  
- **esp32_garden_03**: Soil moisture sensor, water pump control

**User**: "What's the temperature in the kitchen?"

**Assistant**: *[Uses read_sensor tool]*

The kitchen temperature sensor is currently reading 23.5°C. The sensor has been providing stable readings with 100% quality score.

**User**: "Turn on the garage light"

**Assistant**: *[Uses control_actuator tool]*

I've sent the command to turn on the garage light. The LED actuator on device esp32_garage_02 has been activated.

## MQTT Message Format

### Topics Structure

```
devices/{device_id}/capabilities    # Device capabilities (retained)
devices/{device_id}/sensors/{type}/data    # Sensor data
devices/{device_id}/actuators/{type}/cmd    # Commands to device
devices/{device_id}/actuators/{type}/status    # Actuator status
devices/{device_id}/status    # Device online/offline (retained)
devices/{device_id}/error    # Error messages
```

### Message Examples

#### Sensor Data
```json
{
  "device_id": "esp32_kitchen_01",
  "timestamp": 1672531200,
  "type": "sensor",
  "component": "temperature",
  "action": "read",
  "value": {
    "reading": 23.5,
    "unit": "°C",
    "quality": 100
  }
}
```

#### Actuator Command
```json
{
  "action": "toggle",
  "timestamp": 1672531200
}
```

## Advanced Configuration

### Custom Database Location
```bash
python mcp_mqtt_bridge.py --db-path /var/lib/iot-bridge/data.db
```

### MQTT Authentication
```bash
python mcp_mqtt_bridge.py \
  --mqtt-broker broker.hivemq.com \
  --mqtt-username myuser \
  --mqtt-password mypass
```

### Debug Logging
```bash
python mcp_mqtt_bridge.py --log-level DEBUG
```

## Monitoring & Maintenance

### Health Check

The server logs important events:
- Device connections/disconnections
- MQTT broker connectivity
- Database operations
- Error conditions

### Database Maintenance

Historical data is automatically cleaned up:
- Sensor readings older than 30 days are removed
- Error logs older than 7 days are removed
- Configurable via environment variables

### Performance Tuning

For large deployments:
1. Use external database (PostgreSQL/TimescaleDB)
2. Implement MQTT topic filtering
3. Add Redis for caching
4. Use connection pooling

## Troubleshooting

### Common Issues

1. **MQTT Connection Failed**
   - Check broker address and port
   - Verify network connectivity
   - Check authentication credentials

2. **No Devices Showing**
   - Ensure ESP32 devices are publishing to correct topics
   - Check MQTT broker logs
   - Verify topic permissions

3. **Database Errors**
   - Check write permissions on database directory
   - Verify disk space
   - Check SQLite version compatibility

### Debug Mode

Enable debug logging to see all MQTT messages:
```bash
export LOG_LEVEL=DEBUG
python mcp_mqtt_bridge.py
```

## Security Considerations

1. **MQTT Security**
   - Always use authentication in production
   - Consider TLS/SSL for MQTT connections
   - Implement topic-based ACLs

2. **Database Security**
   - Encrypt database at rest
   - Regular backups
   - Access control for database files

3. **MCP Security**
   - Validate all input from MCP clients
   - Rate limiting for commands
   - Audit logging for actions

## Extension Points

### Adding Custom Tools

```python
@self.mcp_server.tool()
async def custom_analysis(device_id: str, duration_hours: int):
    """Custom analysis tool"""
    # Your implementation
    pass
```

### Custom MQTT Handlers

```python
def handle_custom_topic(device_id, topic_parts, payload):
    """Handle custom MQTT topics"""
    # Your implementation
    pass

mqtt.register_handler("custom", handle_custom_topic)
```

## Support

- GitHub Issues: [github.com/your-org/mcp-mqtt-bridge](https://github.com/your-org/mcp-mqtt-bridge)
- Documentation: [docs.your-org.com/mcp-mqtt-bridge](https://docs.your-org.com/mcp-mqtt-bridge)
- ESP32 Library: [github.com/your-org/esp_mcp_bridge](https://github.com/your-org/esp_mcp_bridge)
