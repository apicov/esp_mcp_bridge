# MCP-MQTT Bridge Server

Python server that bridges MQTT IoT devices with Large Language Models using the Model Context Protocol.

## 📁 **Structure**

```
server/
├── mcp_mqtt_bridge/            # Core server package
│   ├── __init__.py             # Package initialization
│   ├── data_models.py          # Data structures
│   ├── mqtt_manager.py         # MQTT client handling
│   ├── database.py             # Database operations
│   ├── device_manager.py       # Device state management
│   ├── mcp_server.py           # MCP protocol handling
│   └── bridge.py               # Main bridge coordinator
├── tests/
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── conftest.py             # Test configuration
├── examples/
│   ├── basic_client.py         # Simple MCP client
│   ├── dashboard.py            # Web dashboard example
│   ├── custom_tools.py         # Custom MCP tools
│   ├── mock_esp32_device.py    # Mock ESP32 device simulator
│   └── mock_device_config.yaml # Mock device configurations
├── scripts/
│   ├── setup_dev.py            # Development setup
│   ├── migrate_db.py           # Database migrations
│   └── health_check.py         # System health check
├── chat_with_devices.py        # OpenAI chat interface
├── start_chat_demo.py          # Complete demo launcher
├── CHAT_DEMO_README.md         # Chat demo documentation
└── config/
    ├── default.yaml            # Default configuration
    ├── development.yaml        # Development settings
    └── production.yaml.example # Production template
```

## 🛠️ **Development Setup**

### **Prerequisites**
- Python 3.11 or later
- Poetry (recommended) or pip
- MQTT broker (Mosquitto recommended)

### **Installation**

#### **Using Poetry (Recommended)**
```bash
cd server
poetry install
poetry shell
```

#### **Using pip**
```bash
cd server
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### **Development Dependencies**
```bash
poetry install --with dev
# or
pip install -r requirements-dev.txt
```

## 🚀 **Quick Start**

### **Basic Usage**
```bash
# Start with default configuration
python -m mcp_mqtt_bridge

# Or with custom settings
python -m mcp_mqtt_bridge --mqtt-broker localhost --db-path ./data/bridge.db
```

### **Configuration**
```bash
# Copy example configuration
cp config/production.yaml.example config/production.yaml

# Edit configuration
nano config/production.yaml

# Run with configuration file
python -m mcp_mqtt_bridge --config config/production.yaml
```

## 📋 **API Overview**

### **MCP Tools Available to LLMs**

1. **`list_devices`** - List connected IoT devices
   ```json
   {"online_only": true}
   ```

2. **`read_sensor`** - Read sensor data with history
   ```json
   {"device_id": "esp32_abc123", "sensor_type": "temperature", "history_minutes": 60}
   ```

3. **`control_actuator`** - Control device actuators
   ```json
   {"device_id": "esp32_abc123", "actuator_type": "led", "action": "toggle"}
   ```

4. **`get_device_info`** - Detailed device information
   ```json
   {"device_id": "esp32_abc123"}
   ```

5. **`query_devices`** - Search devices by capabilities
   ```json
   {"sensor_type": "temperature", "online_only": true}
   ```

6. **`get_alerts`** - Recent errors and alerts
   ```json
   {"severity_min": 1, "device_id": "esp32_abc123"}
   ```

### **Programmatic API**
```python
from mcp_mqtt_bridge import MCPMQTTBridge

# Create bridge instance
bridge = MCPMQTTBridge(
    mqtt_broker="localhost",
    mqtt_port=1883,
    db_path="bridge.db"
)

# Start the bridge
await bridge.start()

# Get device list
devices = bridge.device_manager.get_all_devices()

# Publish command to device
success = bridge.mqtt.publish(
    "devices/esp32_abc123/actuators/led/cmd",
    {"action": "toggle"}
)
```

## 🧪 **Testing**

### **Run All Tests**
```bash
pytest
```

### **Unit Tests Only**
```bash
pytest tests/unit/
```

### **Integration Tests**
```bash
# Requires MQTT broker running
docker run -it -p 1883:1883 eclipse-mosquitto
pytest tests/integration/
```

### **Coverage Report**
```bash
pytest --cov=mcp_mqtt_bridge --cov-report=html
open htmlcov/index.html
```

## 🧪 **Testing with Mock Devices**

### **Mock ESP32 Device Simulator**

For testing without physical hardware, use the included mock ESP32 device simulator:

```bash
# Start mock devices with default configuration (3 devices)
python examples/mock_esp32_device.py

# Start with custom number of devices
python examples/mock_esp32_device.py --devices 5

# Start with custom MQTT broker
python examples/mock_esp32_device.py --broker mqtt.example.com --port 1883

# Start with configuration file
python examples/mock_esp32_device.py --config examples/mock_device_config.yaml
```

### **💬 Chat Demo with OpenAI**

Experience the full power of AI-controlled IoT with our interactive chat demo:

```bash
# Install chat requirements
pip install -r requirements-chat.txt

# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Start everything with one command!
python start_chat_demo.py
```

This creates a complete end-to-end system where you can:
- **Chat naturally** with GPT-4 about your devices
- **Control devices** by voice: *"Turn on the kitchen LED"*
- **Read sensors** by asking: *"What's the temperature in the bedroom?"*
- **Read all sensors**: *"Show me all sensors"* - reads multiple sensors efficiently
- **Device-specific queries**: *"Read all sensors from the kitchen"*
- **Get intelligent responses** that understand your home automation

**Recent Enhancements:**
- ✅ **Fixed multi-sensor reading** - No more stopping after each sensor
- ✅ **Added `read_all_sensors` function** - Efficient batch sensor reading
- ✅ **Added `read_device_sensors` function** - Read all sensors from specific device
- ✅ **Improved OpenAI function calling** - Parallel execution and better prompts

See `CHAT_DEMO_README.md` for complete instructions and example conversations!

### **Mock Device Features**
- **Realistic Sensor Simulation**: Temperature, humidity, light, motion, air quality, etc.
- **Actuator Control**: LEDs, relays, pumps, motors with state feedback
- **Error Simulation**: Occasional sensor errors and connection issues
- **Configurable Behavior**: YAML-based device configuration
- **Multiple Device Types**: Kitchen, living room, bedroom, garage, garden scenarios
- **MQTT Topic Compatibility**: Matches firmware MQTT topic structure

### **Testing Scenarios**

Run the comprehensive test suite:

```bash
python examples/test_with_mock_devices.py
```

**Manual Testing Steps:**
1. Start mosquitto MQTT broker: `mosquitto`
2. Start mock devices: `python examples/mock_esp32_device.py`
3. Start MCP bridge: `python -m mcp_mqtt_bridge`
4. Connect MCP client and test commands

**Device Configuration (mock_device_config.yaml):**
```yaml
mqtt:
  broker: localhost
  port: 1883

devices:
  - device_id: esp32_kitchen
    location: kitchen
    sensors:
      - name: temperature
        sensor_type: temperature
        unit: °C
        base_value: 22.0
        variation: 1.5
    actuators:
      - name: led
        actuator_type: led
        supported_actions: [on, off, toggle]
```

## 🔧 **Configuration**

### **Environment Variables**
```bash
export MQTT_BROKER=localhost
export MQTT_PORT=1883
export MQTT_USERNAME=your_user
export MQTT_PASSWORD=your_pass
export DB_PATH=./data/bridge.db
export LOG_LEVEL=INFO
```

### **Configuration File (YAML)**
```yaml
mqtt:
  broker: localhost
  port: 1883
  username: ${MQTT_USERNAME}
  password: ${MQTT_PASSWORD}
  client_id: mcp_bridge_server

database:
  path: ./data/bridge.db
  retention_days: 30
  cleanup_interval_hours: 24

monitoring:
  device_timeout_minutes: 5
  metrics_interval_seconds: 60
  log_level: INFO
  max_errors_per_device: 100

security:
  enable_tls: false
  ca_cert_path: ./certs/ca.crt
  cert_path: ./certs/client.crt
  key_path: ./certs/client.key
```

## 📊 **Monitoring & Debugging**

### **Logging Configuration**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bridge.log'),
        logging.StreamHandler()
    ]
)
```

### **Health Check**
```bash
python scripts/health_check.py
```

### **Database Management**
```bash
# View database statistics
python -c "from mcp_mqtt_bridge.database import DatabaseManager; db = DatabaseManager(); print(db.get_database_stats())"

# Clean up old data
python scripts/migrate_db.py --cleanup --retention-days 30
```

## 🐳 **Docker Deployment**

### **Build Image**
```bash
docker build -t mcp-mqtt-bridge .
```

### **Run Container**
```bash
docker run -d \
  --name mcp-bridge \
  -p 1883:1883 \
  -e MQTT_BROKER=localhost \
  -e DB_PATH=/data/bridge.db \
  -v ./data:/data \
  mcp-mqtt-bridge
```

### **Docker Compose**
```yaml
version: '3.8'
services:
  mcp-bridge:
    build: .
    environment:
      - MQTT_BROKER=mosquitto
      - DB_PATH=/data/bridge.db
    volumes:
      - ./data:/data
    depends_on:
      - mosquitto
      
  mosquitto:
    image: eclipse-mosquitto:latest
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
```

## 🔒 **Security**

### **TLS/SSL Configuration**
```python
bridge = MCPMQTTBridge(
    mqtt_broker="secure-broker.com",
    mqtt_port=8883,
    enable_tls=True,
    ca_cert_path="./certs/ca.crt",
    cert_path="./certs/client.crt",
    key_path="./certs/client.key"
)
```

### **Authentication**
```python
bridge = MCPMQTTBridge(
    mqtt_broker="broker.com",
    mqtt_username="secure_user",
    mqtt_password="secure_password"
)
```

## 📈 **Performance Tuning**

### **Database Optimization**
- Regular cleanup of old data
- Proper indexing on query columns
- Connection pooling for high load

### **MQTT Optimization**
- Appropriate QoS levels for message types
- Connection keep-alive tuning
- Message batching for high-frequency data

### **Memory Management**
- Limit device error history
- Periodic cleanup of disconnected devices
- Configurable retention policies

## 🔗 **Integration Examples**

### **Claude Desktop**
```json
{
  "mcp-servers": {
    "iot-bridge": {
      "command": "python",
      "args": ["-m", "mcp_mqtt_bridge"],
      "env": {
        "MQTT_BROKER": "your-broker.com",
        "MQTT_USERNAME": "your_user",
        "MQTT_PASSWORD": "your_pass"
      }
    }
  }
}
```

### **Custom MCP Client**
```python
from mcp import ClientSession
from mcp.client.stdio import stdio_client

async def control_devices():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List devices
            devices = await session.call_tool("list_devices", {})
            
            # Control LED
            result = await session.call_tool("control_actuator", {
                "device_id": "esp32_kitchen",
                "actuator_type": "led", 
                "action": "toggle"
            })
```

## 📝 **Development Guidelines**

### **Code Style**
- Follow PEP 8
- Use type hints
- Docstrings for all public functions
- Maximum line length: 100 characters

### **Testing**
- Unit tests for all modules
- Integration tests for MQTT/database interactions
- Mock external dependencies in unit tests
- Aim for >90% code coverage

### **Contributing**
1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 🔗 **Related Documentation**

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Paho MQTT Client](https://www.eclipse.org/paho/clients/python/)
- [SQLite Documentation](https://docs.python.org/3/library/sqlite3.html) 