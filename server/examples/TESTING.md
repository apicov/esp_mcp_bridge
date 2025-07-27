# Testing Guide: Mock ESP32 Devices

This guide explains how to use the mock ESP32 device simulator for testing the MCP-MQTT Bridge without physical hardware.

## 🚀 Quick Start

### 1. **Setup**
```bash
# Navigate to server directory
cd server

# Activate virtual environment
source venv/bin/activate

# Ensure dependencies are installed
pip install paho-mqtt PyYAML
```

### 2. **Start MQTT Broker**
```bash
# Install mosquitto if not already installed
sudo apt install mosquitto mosquitto-clients  # Ubuntu/Debian
brew install mosquitto                        # macOS

# Start mosquitto broker
mosquitto -v
```

### 3. **Start Mock Devices**
```bash
# Start with default configuration (3 devices)
python examples/mock_esp32_device.py

# Or with custom configuration
python examples/mock_esp32_device.py --config examples/mock_device_config.yaml
```

### 4. **Start MCP Bridge**
```bash
# In another terminal
cd server
source venv/bin/activate
python -m mcp_mqtt_bridge --config config/development.yaml
```

### 5. **Test with MCP Client**
```bash
# In another terminal
cd server
source venv/bin/activate
python examples/basic_client.py
```

## 📱 Mock Device Types

The system creates 5 different mock devices by default:

### **esp32_kitchen**
- **Sensors**: temperature, humidity, gas
- **Actuators**: led, exhaust_fan
- **Location**: kitchen
- **Scenarios**: Cooking detection, air quality monitoring

### **esp32_living_room**
- **Sensors**: temperature, humidity, light, motion
- **Actuators**: led, relay
- **Location**: living_room  
- **Scenarios**: Occupancy detection, lighting control

### **esp32_bedroom**
- **Sensors**: temperature, humidity, noise, air_quality
- **Actuators**: led, heater, air_purifier
- **Location**: bedroom
- **Scenarios**: Sleep environment optimization

### **esp32_garage**
- **Sensors**: temperature, humidity, distance, vibration
- **Actuators**: led, garage_door, security_light
- **Location**: garage
- **Scenarios**: Vehicle detection, security monitoring

### **esp32_garden**
- **Sensors**: temperature, humidity, soil_moisture, light_intensity, wind_speed
- **Actuators**: led, water_pump, sprinkler, grow_light
- **Location**: garden
- **Scenarios**: Plant care automation, weather monitoring

## 🧪 Testing Scenarios

### **Basic Functionality Test**
```bash
# 1. List all devices
# Expected: See all 5 mock devices

# 2. Get device info
# Try: device_id='esp32_kitchen'
# Expected: Device details with sensors and actuators

# 3. Read sensor data
# Try: device_id='esp32_kitchen', sensor_type='temperature'
# Expected: Recent temperature readings

# 4. Control actuator
# Try: device_id='esp32_kitchen', actuator_type='led', action='toggle'
# Expected: LED state change confirmation
```

### **Error Handling Test**
The mock devices occasionally simulate errors:
- **Sensor read errors** (~0.1% chance)
- **Connection drops** (very rare)
- **Invalid commands** (when testing wrong actuator types)

### **Performance Test**
```bash
# Start more devices for load testing
python examples/mock_esp32_device.py --devices 10

# Monitor system performance
python scripts/health_check.py
```

## 🔧 Configuration

### **Custom Device Configuration**
Create your own `my_devices.yaml`:

```yaml
mqtt:
  broker: localhost
  port: 1883
  username: test_user      # Optional
  password: test_pass      # Optional

devices:
  - device_id: my_custom_device
    device_type: ESP32-S3
    firmware_version: 2.0.0
    location: test_bench
    sensors:
      - name: temperature
        sensor_type: temperature
        unit: °C
        min_value: 20.0
        max_value: 30.0
        base_value: 25.0
        variation: 1.0
        update_interval: 5.0
    actuators:
      - name: led
        actuator_type: led
        initial_state: off
        supported_actions: [on, off, toggle, blink]
```

### **Command Line Options**
```bash
# Basic options
python examples/mock_esp32_device.py \
  --devices 5 \
  --broker mqtt.example.com \
  --port 1883 \
  --username myuser \
  --password mypass

# With configuration file
python examples/mock_esp32_device.py \
  --config my_devices.yaml
```

## 📊 MQTT Topics

The mock devices use the same topic structure as real ESP32 devices:

### **Published by Devices**
```
devices/{device_id}/status           # Device status and uptime
devices/{device_id}/capabilities     # Device capabilities
devices/{device_id}/sensors/{name}   # Sensor readings
devices/{device_id}/actuators/{name}/status  # Actuator states
devices/{device_id}/error           # Error messages
devices/{device_id}/info            # Detailed device info
```

### **Subscribed by Devices**
```
devices/{device_id}/actuators/{name}/cmd    # Actuator commands
devices/{device_id}/cmd                     # General device commands
```

### **Example Messages**

**Sensor Reading:**
```json
{
  "device_id": "esp32_kitchen",
  "sensor": "temperature", 
  "type": "temperature",
  "value": 22.5,
  "unit": "°C",
  "quality": 98.5,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Actuator Command:**
```json
{
  "action": "toggle",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Device Status:**
```json
{
  "device_id": "esp32_kitchen",
  "status": "online",
  "uptime": 3600,
  "wifi_rssi": -45,
  "memory_usage": 65,
  "cpu_usage": 15,
  "message_count": 1250,
  "error_count": 2,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## 🐛 Troubleshooting

### **Mock Devices Won't Start**
```bash
# Check MQTT broker is running
mosquitto_pub -h localhost -t test -m "hello"

# Check Python dependencies
pip list | grep -E "(paho-mqtt|PyYAML)"

# Check for port conflicts
netstat -an | grep 1883
```

### **No Sensor Data**
- Verify MQTT broker is accessible
- Check device logs for connection errors
- Ensure topic subscriptions are correct

### **MCP Bridge Not Responding**
- Check bridge database initialization
- Verify MQTT topic compatibility  
- Review bridge logs for errors

### **Performance Issues**
- Reduce number of mock devices
- Increase sensor update intervals
- Monitor system resources

## 📈 Advanced Testing

### **Load Testing**
```bash
# Start many devices
python examples/mock_esp32_device.py --devices 50

# Monitor performance
python scripts/health_check.py --component database
python scripts/health_check.py --component mqtt
```

### **Reliability Testing**
```bash
# Test with connection interruptions
# 1. Start devices
# 2. Stop/start MQTT broker
# 3. Verify device reconnection
# 4. Check data integrity
```

### **Integration Testing**
```bash
# Full system test
python examples/test_with_mock_devices.py
```

## 🎯 Best Practices

1. **Start Simple**: Begin with 1-2 devices for basic testing
2. **Monitor Resources**: Watch CPU/memory usage with many devices
3. **Test Error Cases**: Verify error handling and recovery
4. **Use Realistic Data**: Configure sensors with real-world ranges
5. **Document Scenarios**: Create test cases for specific use cases

## 🔗 Related Tools

- **MQTT Explorer**: GUI for monitoring MQTT messages
- **mosquitto_sub/pub**: Command-line MQTT testing
- **MCP Client Examples**: Test MCP integration
- **Dashboard Example**: Web-based device monitoring 