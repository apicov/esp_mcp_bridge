# ESP32 MCP-MQTT Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![ESP-IDF](https://img.shields.io/badge/ESP--IDF-v5.1+-blue.svg)](https://docs.espressif.com/projects/esp-idf/en/latest/)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-1.0+-purple.svg)](https://modelcontextprotocol.io/)

A production-ready system that bridges ESP32 IoT devices with Large Language Models using MQTT and the Model Context Protocol (MCP). Enables natural language control and monitoring of IoT devices through AI assistants.

## 🏗️ **Project Structure**

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

## 🚀 **Quick Start**

### **1. ESP32 Firmware**
```bash
cd firmware/examples/basic_example
idf.py build flash monitor
```

### **2. Python MCP Server**
```bash
cd server
pip install -r requirements.txt
python -m mcp_mqtt_bridge
```

### **3. LLM Integration**
Add to your Claude Desktop configuration:
```json
{
  "mcp-servers": {
    "iot-bridge": {
      "command": "python",
      "args": ["-m", "mcp_mqtt_bridge"],
      "env": {"MQTT_BROKER": "localhost"}
    }
  }
}
```

## 📚 **Documentation**

- **[Comprehensive Code Guide](ESP32_MCP_BRIDGE_COMPREHENSIVE_GUIDE.md)** - Complete architecture and code analysis
- **[Getting Started Guide](docs/setup_guide.md)** - Complete setup instructions
- **[ESP32 Firmware Guide](firmware/README.md)** - ESP32 development
- **[Python Server Guide](server/README.md)** - MCP server setup
- **[Chat Demo Guide](server/CHAT_DEMO_README.md)** - OpenAI chat interface
- **[Architecture Overview](docs/enhanced-features.md)** - System design
- **[Developer Guide](CLAUDE.md)** - Development commands and workflows

## ✨ **Features**

- 🔒 **Enterprise Security**: TLS/SSL, device authentication, certificates
- 📊 **Real-time Monitoring**: Metrics, alerts, device health tracking
- ⚡ **High Performance**: Batch operations, streaming, optimization
- 🛠️ **Production Ready**: Error recovery, logging, diagnostics
- 🏗️ **Modular Design**: Clean architecture, extensible components
- 🔧 **Easy Integration**: Simple APIs, comprehensive examples

## 🎯 **Use Cases**

- **Smart Home**: Control lights, sensors, HVAC through natural language
- **Industrial IoT**: Monitor equipment, control processes via AI
- **Agriculture**: Manage irrigation, environmental controls with LLMs
- **Research**: Rapid prototyping of IoT-AI integration projects

## 🤝 **Contributing**

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## 📄 **License**

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 **Links**

- [ESP-IDF Documentation](https://docs.espressif.com/projects/esp-idf/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MQTT Protocol](https://mqtt.org/)
- [Issue Tracker](https://github.com/your-org/esp32-mcp-bridge/issues)
