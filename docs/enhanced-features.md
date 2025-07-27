# Enhanced ESP32 MCP-MQTT Bridge System

A **production-ready** system that bridges ESP32 IoT devices with Large Language Models using MQTT and the Model Context Protocol (MCP). This enhanced version includes advanced security, comprehensive error handling, metrics collection, and a modular architecture.

## 🚀 **New Features & Enhancements**

### **🔒 Enhanced Security**
- **TLS/SSL Support**: Secure MQTT connections with certificate management
- **Device Authentication**: Username/password authentication for devices
- **Certificate Validation**: Configurable certificate verification
- **QoS Configuration**: Granular Quality of Service settings per message type

### **📊 Advanced Monitoring**
- **Real-time Metrics**: Message counts, connection failures, uptime tracking
- **Device Health Monitoring**: Automatic offline detection and recovery
- **Error Tracking**: Comprehensive error logging with severity levels
- **Performance Metrics**: Memory usage, response times, throughput stats

### **🛠 Improved Error Handling**
- **Specific Error Codes**: Detailed error classification and reporting
- **Automatic Recovery**: Self-healing connections and error recovery
- **Event-driven Architecture**: Rich event system for monitoring and debugging
- **Enhanced Logging**: Structured logging with multiple levels

### **⚡ Performance Optimizations**
- **Batch Operations**: Efficient batch sensor data publishing
- **Streaming Mode**: High-frequency data streaming for critical sensors
- **Memory Management**: Optimized memory usage with configurable limits
- **Connection Pooling**: Efficient MQTT connection management

### **🏗 Modular Architecture**
- **Separated Concerns**: Clean separation of MQTT, database, and MCP logic
- **Plugin Architecture**: Easy extension with custom handlers
- **Configuration Management**: Runtime configuration updates
- **Scalable Design**: Support for multiple devices and high throughput

## 📋 **Quick Start**

### **ESP32 Side (Enhanced)**

```c
#include "esp_mcp_bridge.h"

void app_main(void) {
    // Enhanced configuration with security
    mcp_bridge_config_t config = {
        .wifi_ssid = "YourWiFiSSID",
        .wifi_password = "YourWiFiPassword",
        .mqtt_broker_uri = "mqtts://your-broker.com:8883",
        .mqtt_username = "device_user",
        .mqtt_password = "device_pass",
        .sensor_publish_interval_ms = 10000,
        .command_timeout_ms = 5000,
        .enable_watchdog = true,
        .enable_device_auth = true,
        
        // Configure QoS levels
        .qos_config = {
            .sensor_qos = 0,     // Best effort
            .actuator_qos = 1,   // At least once
            .status_qos = 1,     // At least once
            .error_qos = 2       // Exactly once
        },
        
        // Configure TLS
        .tls_config = {
            .enable_tls = true,
            .ca_cert_pem = your_ca_cert,
            .client_cert_pem = your_client_cert,
            .client_key_pem = your_client_key,
            .skip_cert_verification = false
        }
    };
    
    ESP_ERROR_CHECK(mcp_bridge_init(&config));
    ESP_ERROR_CHECK(mcp_bridge_register_event_handler(event_handler, NULL));
    
    // Register sensors with enhanced metadata
    mcp_sensor_metadata_t temp_metadata = {
        .min_range = -40.0,
        .max_range = 85.0,
        .accuracy = 0.5,
        .description = "High-precision temperature sensor",
        .calibration_required = true,
        .calibration_interval_s = 86400
    };
    ESP_ERROR_CHECK(mcp_bridge_register_sensor("temperature", "temperature", "°C", 
                                              &temp_metadata, temp_read_cb, NULL));
    
    // Register actuators with enhanced metadata  
    const char *led_actions[] = {"read", "write", "toggle", NULL};
    mcp_actuator_metadata_t led_metadata = {
        .value_type = "boolean",
        .description = "RGB LED with brightness control",
        .supported_actions = led_actions,
        .response_time_ms = 100,
        .requires_confirmation = false
    };
    ESP_ERROR_CHECK(mcp_bridge_register_actuator("led", "led",
                                                &led_metadata, led_control_cb, NULL));
    
    ESP_ERROR_CHECK(mcp_bridge_start());
    
    // Main loop with enhanced monitoring
    while (1) {
        mcp_bridge_metrics_t metrics;
        mcp_bridge_get_metrics(&metrics);
        
        ESP_LOGI(TAG, "System health - Messages: %lu sent, %lu received, Uptime: %lu s",
                metrics.messages_sent, metrics.messages_received, metrics.uptime_seconds);
        
        vTaskDelay(pdMS_TO_TICKS(30000));
    }
}
```

### **Python MCP Server (Modular)**

```python
# main.py
import asyncio
from mcp_mqtt_bridge import MCPMQTTBridge

async def main():
    # Enhanced bridge with modular architecture
    bridge = MCPMQTTBridge(
        mqtt_broker="your-broker.com",
        mqtt_port=8883,
        mqtt_username="server_user", 
        mqtt_password="server_pass",
        db_path="./data/iot_bridge.db",
        enable_tls=True,
        ca_cert_path="./certs/ca.crt"
    )
    
    await bridge.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🔧 **Enhanced API Reference**

### **New ESP32 Functions**

```c
// Metrics and monitoring
esp_err_t mcp_bridge_get_metrics(mcp_bridge_metrics_t *metrics);
esp_err_t mcp_bridge_reset_metrics(void);

// Batch operations
esp_err_t mcp_bridge_publish_sensor_batch(const mcp_sensor_reading_t *readings, size_t count);

// Streaming mode
esp_err_t mcp_bridge_set_sensor_streaming(const char *sensor_id, bool enable, uint32_t interval_ms);

// Runtime configuration
esp_err_t mcp_bridge_update_config(const mcp_bridge_config_t *config);

// Enhanced error handling
esp_err_t mcp_bridge_publish_error(const char *error_type, const char *message, uint8_t severity);
```

### **Enhanced Python Tools**

The MCP server now provides these tools to LLM agents:

1. **`list_devices`** - List connected devices with enhanced filtering
2. **`read_sensor`** - Read sensor data with historical analysis  
3. **`control_actuator`** - Control actuators with confirmation
4. **`get_device_info`** - Comprehensive device information
5. **`query_devices`** - Advanced device querying by capabilities
6. **`get_alerts`** - Real-time alert and error monitoring
7. **`get_metrics`** - System performance metrics
8. **`device_diagnostics`** - Advanced device diagnostics

## 🏗 **Modular Architecture**

```
mcp_mqtt_bridge/
├── __init__.py              # Package initialization
├── data_models.py           # Data structures and models
├── mqtt_manager.py          # MQTT client management
├── database.py              # Database operations
├── device_manager.py        # Device state management
├── mcp_server.py           # MCP protocol handling
└── bridge.py               # Main bridge coordinator
```

## 📊 **Enhanced Monitoring**

### **Real-time Metrics**

```python
# Get comprehensive system metrics
metrics = await bridge.get_system_metrics()

print(f"Devices online: {metrics['devices_online']}")
print(f"Messages/minute: {metrics['message_rate']}")
print(f"Error rate: {metrics['error_rate']}%")
print(f"Database size: {metrics['db_size_mb']} MB")
```

### **Device Health Dashboard**

```python
# Monitor device health
for device in bridge.get_devices():
    health = bridge.get_device_health(device.device_id)
    print(f"{device.device_id}: {health['status']} - Last seen: {health['last_seen']}")
```

## 🔒 **Security Features**

### **TLS Configuration**

```c
mcp_tls_config_t tls_config = {
    .enable_tls = true,
    .ca_cert_pem = ca_certificate_pem,
    .client_cert_pem = client_certificate_pem, 
    .client_key_pem = client_private_key_pem,
    .skip_cert_verification = false,  // Always false in production
    .alpn_protocols = {"mqtt", NULL}
};
```

### **Device Authentication**

```c
mcp_bridge_config_t config = {
    .mqtt_username = "device_12345",
    .mqtt_password = "secure_device_password",
    .enable_device_auth = true,
    // ... other config
};
```

## 📈 **Performance Optimizations**

### **Batch Sensor Publishing**

```c
// Efficient batch publishing
mcp_sensor_reading_t readings[3] = {
    {"temp", "temperature", 23.5, "°C", time_now, 95.0},
    {"humidity", "humidity", 60.2, "%", time_now, 90.0},
    {"pressure", "pressure", 1013.2, "hPa", time_now, 98.0}
};

mcp_bridge_publish_sensor_batch(readings, 3);
```

### **Streaming Mode**

```c
// Enable high-frequency streaming for critical sensors
mcp_bridge_set_sensor_streaming("critical_temp", true, 1000); // 1 second
```

## 🎯 **Production Deployment**

### **Docker Deployment**

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY mcp_mqtt_bridge/ ./mcp_mqtt_bridge/
COPY main.py .

CMD ["python", "main.py"]
```

### **Configuration Management**

```yaml
# config.yaml
mqtt:
  broker: "production-broker.com"
  port: 8883
  username: "${MQTT_USERNAME}"
  password: "${MQTT_PASSWORD}"
  
security:
  enable_tls: true
  ca_cert: "/certs/ca.crt"
  verify_certificates: true
  
monitoring:
  metrics_interval: 60
  log_level: "INFO"
  alert_threshold: 10
```

## 🐛 **Debugging & Troubleshooting**

### **Enhanced Logging**

```c
// ESP32 - Enable verbose logging
esp_log_level_set("MCP_BRIDGE", ESP_LOG_VERBOSE);

// Python - Configure structured logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### **Diagnostic Tools**

```python
# Check system health
health = await bridge.run_diagnostics()
print(f"System status: {health['overall_status']}")

# Monitor real-time events
await bridge.start_event_monitoring(callback=handle_event)
```

## 🚀 **What's New Summary**

| Feature | Before | After |
|---------|--------|-------|
| **Security** | Basic MQTT | TLS + Authentication + Certificates |
| **Error Handling** | Basic logging | Specific error codes + recovery |
| **Architecture** | Monolithic | Modular + extensible |
| **Monitoring** | Limited | Comprehensive metrics + alerts |
| **Performance** | Basic | Optimized + batch + streaming |
| **Configuration** | Static | Runtime updates + validation |
| **Testing** | Manual | Automated + comprehensive |

## 🔮 **Future Enhancements**

- **Multi-protocol Support**: Support for CoAP, LoRaWAN
- **Cloud Integration**: AWS IoT, Azure IoT Hub connectors  
- **Advanced Analytics**: ML-based anomaly detection
- **Mobile App**: React Native management app
- **Kubernetes Operator**: K8s native deployment
- **Edge Computing**: Edge AI processing capabilities

---

**Ready for production use with enterprise-grade features!** 🎉 