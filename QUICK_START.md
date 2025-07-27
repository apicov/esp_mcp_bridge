# Quick Start Guide

This guide will help you test that the ESP32 MCP-MQTT Bridge is ready to use.

## 🛠️ **Prerequisites**

### **ESP32 Development**
- ESP-IDF v5.1 or later
- ESP32 development board

### **Python Server**
- Python 3.11+
- MQTT broker (Mosquitto recommended)

## 🚀 **Test the Python Server**

### **1. Install Dependencies**
```bash
cd server
pip install -r requirements.txt
```

### **2. Start MQTT Broker (using Docker)**
```bash
cd deployment
docker run -d -p 1883:1883 --name test-mosquitto eclipse-mosquitto
```

### **3. Run the Server**
```bash
cd server
python -m mcp_mqtt_bridge --mqtt-broker localhost
```

You should see:
```
INFO - Starting MCP-MQTT Bridge Server...
INFO - MQTT Broker: localhost:1883
INFO - MQTT connected successfully
```

## 🔌 **Test the ESP32 Firmware**

### **1. Setup ESP-IDF Environment**
```bash
cd firmware/examples/basic_example
source $IDF_PATH/export.sh
```

### **2. Configure WiFi and MQTT**
```bash
idf.py menuconfig
```
Navigate to: `Component config → MCP Bridge Configuration`
- Set your WiFi SSID and password
- Set MQTT broker URL to your server IP

### **3. Build and Flash**
```bash
idf.py build
idf.py flash monitor
```

You should see the counter sensor incrementing:
```
I (12345) MCP_EXAMPLE: Counter read: 1
I (14345) MCP_EXAMPLE: Counter read: 2
I (16345) MCP_EXAMPLE: Counter read: 3
```

## 🧪 **Test the Integration**

### **1. Verify Device Connection**
In the server logs, you should see:
```
INFO - Device capabilities from esp32_abc123: {...}
INFO - Sensor data from esp32_abc123/counter: {"value": {"reading": 5}}
```

### **2. Test MCP Tools (Future)**
Once connected to an LLM, you can ask:
- "List all IoT devices"
- "What's the current counter sensor value?"
- "Turn on the LED on device esp32_abc123"

## ✅ **Project Status**

| Component | Status | Lines of Code | Description |
|-----------|--------|---------------|-------------|
| **ESP32 Bridge Library** | ✅ Ready | 1,228 lines | Complete implementation |
| **ESP32 Device Utils** | ✅ Ready | 181 lines | Device abstraction layer |
| **Python MCP Server** | ✅ Ready | 1,573 lines | Modular server implementation |
| **Basic Example** | ✅ Ready | 538 lines | Working example with counter sensor |
| **Documentation** | ✅ Ready | Complete | READMEs, configuration, deployment |
| **Build System** | ✅ Ready | Complete | CMakeLists.txt, Kconfig, Docker |

## 🎯 **What Works**

### **ESP32 Features**
- ✅ WiFi and MQTT connectivity with auto-reconnection
- ✅ Sensor registration and automatic polling
- ✅ Actuator control with command processing
- ✅ JSON message formatting and parsing
- ✅ Error handling and event system
- ✅ **Counter sensor for easy testing**
- ✅ Batch sensor publishing
- ✅ TLS/SSL support configuration
- ✅ Configurable QoS levels
- ✅ Device metrics collection

### **Python Server Features**
- ✅ MQTT client with automatic subscriptions
- ✅ SQLite database with proper schema
- ✅ Device state management
- ✅ MCP tools for LLM integration
- ✅ Modular architecture
- ✅ CLI interface with configuration options
- ✅ Docker deployment support
- ✅ Comprehensive logging

### **Integration Features**
- ✅ Standardized MQTT topic structure
- ✅ JSON message protocol
- ✅ Device capability discovery
- ✅ Real-time sensor data streaming
- ✅ Actuator command routing
- ✅ Error reporting and alerting

## 🎉 **Ready to Use!**

Your ESP32 MCP-MQTT Bridge is **fully functional and ready for use**! 

The **counter sensor** in the basic example provides an easy way to verify that:
- ESP32 is reading sensors
- MQTT messages are being sent
- Python server is receiving data
- Database is storing readings
- System is working end-to-end

**Next Steps:**
1. Flash the ESP32 with your WiFi credentials
2. Start the Python server
3. Watch the counter increment
4. Integrate with your favorite LLM via MCP
5. Add your own real sensors and actuators! 