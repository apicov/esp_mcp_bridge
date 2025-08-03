# MQTT Port and Configuration Guide

The ESP32 MCP Bridge system supports full MQTT configuration including custom ports, security, and broker settings for both the server and ESP32 firmware.

## 🖥️ Server Side Configuration

### Command Line Arguments

```bash
# Standard MQTT (port 1883)
python -m mcp_mqtt_bridge --mqtt-broker localhost --mqtt-port 1883

# Custom port
python -m mcp_mqtt_bridge --mqtt-broker 192.168.1.100 --mqtt-port 1884

# Secure MQTT (port 8883)
python -m mcp_mqtt_bridge --mqtt-broker localhost --mqtt-port 8883

# Non-standard port with authentication
python -m mcp_mqtt_bridge \
    --mqtt-broker mqtt.example.com \
    --mqtt-port 9001 \
    --mqtt-username iot_user \
    --mqtt-password secure_password

# Full remote setup with custom MQTT
python -m mcp_mqtt_bridge \
    --mqtt-broker 192.168.1.100 \
    --mqtt-port 1884 \
    --enable-mcp-server \
    --mcp-host 0.0.0.0 \
    --mcp-port 8000
```

### Environment Variables

```bash
# Set MQTT configuration
export MQTT_BROKER="192.168.1.100"
export MQTT_PORT="1884"
export MQTT_USERNAME="iot_device"
export MQTT_PASSWORD="super_secure_password"

# Set MCP server configuration
export MCP_PORT="8000"
export MCP_HOST="0.0.0.0"

# Start bridge (will use environment variables)
python -m mcp_mqtt_bridge --enable-mcp-server
```

### FastMCP Server with Custom MQTT

```bash
# FastMCP bridge with custom MQTT port
python fastmcp_bridge_server.py \
    --mqtt-broker 192.168.1.100 \
    --mqtt-port 1884 \
    --stdio

# Remote FastMCP chat connecting to custom MQTT bridge
python remote_fastmcp_chat.py \
    --remote-host your-server.com \
    --remote-port 8000
```

## 🔧 ESP32 Firmware Configuration

### Method 1: Kconfig (Build-time Configuration)

```bash
cd firmware/examples/basic_example

# Configure via menuconfig
idf.py menuconfig

# Navigate to: Component config → MCP Bridge Configuration
# Set "MQTT Broker URL" to: mqtt://192.168.1.100:1884
```

### Method 2: Code Configuration

Edit your ESP32 application code:

```c
#include "mcp_bridge.h"

void app_main() {
    // Configure MQTT broker with custom port
    mcp_bridge_config_t config = {
        .wifi_ssid = "Your_WiFi_SSID",
        .wifi_password = "Your_WiFi_Password",
        .mqtt_broker_url = "mqtt://192.168.1.100:1884",  // Custom port
        .device_id = "esp32_custom_device",
        .sensor_publish_interval = 10000
    };
    
    // For secure MQTT (TLS)
    // config.mqtt_broker_url = "mqtts://192.168.1.100:8883";
    
    mcp_bridge_init(&config);
    mcp_bridge_start();
}
```

### Method 3: Runtime Configuration (Advanced)

```c
#include "mcp_bridge.h"

void configure_custom_mqtt() {
    // Set MQTT broker at runtime
    mcp_bridge_set_mqtt_broker("192.168.1.100", 1884);
    
    // Set authentication
    mcp_bridge_set_mqtt_auth("iot_user", "password");
    
    // Enable TLS (for port 8883)
    mcp_bridge_enable_mqtt_tls(true);
}
```

## 🐳 Docker/Container Configuration

### Docker Compose with Custom MQTT

```yaml
version: '3.8'
services:
  mosquitto:
    image: eclipse-mosquitto:latest
    ports:
      - "1884:1884"  # Custom port
      - "8883:8883"  # TLS port
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
      - mosquitto_data:/mosquitto/data
      - mosquitto_log:/mosquitto/log

  mcp-bridge:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MQTT_BROKER=mosquitto
      - MQTT_PORT=1884
    depends_on:
      - mosquitto
    command: >
      python -m mcp_mqtt_bridge
      --mqtt-broker mosquitto
      --mqtt-port 1884
      --enable-mcp-server
      --mcp-host 0.0.0.0

volumes:
  mosquitto_data:
  mosquitto_log:
```

### Custom Mosquitto Configuration

Create `mosquitto.conf`:

```conf
# Custom port configuration
listener 1884
protocol mqtt

# TLS/SSL configuration
listener 8883
protocol mqtt
cafile /mosquitto/config/ca.crt
certfile /mosquitto/config/server.crt
keyfile /mosquitto/config/server.key

# Authentication
allow_anonymous false
password_file /mosquitto/config/passwords

# Logging
log_dest file /mosquitto/log/mosquitto.log
log_type all
```

## 🌐 Common MQTT Port Configurations

### Standard Ports
```bash
# Standard MQTT (unencrypted)
--mqtt-port 1883

# Secure MQTT over TLS
--mqtt-port 8883

# MQTT over WebSockets
--mqtt-port 9001

# MQTT over secure WebSockets
--mqtt-port 9002
```

### Cloud Provider Ports

#### AWS IoT Core
```bash
python -m mcp_mqtt_bridge \
    --mqtt-broker your-endpoint.iot.us-west-2.amazonaws.com \
    --mqtt-port 8883 \
    --mqtt-username your-device \
    --mqtt-password your-token
```

#### Azure IoT Hub
```bash
python -m mcp_mqtt_bridge \
    --mqtt-broker your-hub.azure-devices.net \
    --mqtt-port 8883 \
    --mqtt-username "your-device-id/?api-version=2021-04-12" \
    --mqtt-password "SharedAccessSignature sr=..."
```

#### Google Cloud IoT
```bash
python -m mcp_mqtt_bridge \
    --mqtt-broker mqtt.googleapis.com \
    --mqtt-port 8883 \
    --mqtt-username unused \
    --mqtt-password your-jwt-token
```

#### HiveMQ Cloud
```bash
python -m mcp_mqtt_bridge \
    --mqtt-broker your-cluster.s1.eu.hivemq.cloud \
    --mqtt-port 8883 \
    --mqtt-username your-username \
    --mqtt-password your-password
```

## 🔒 Security Configurations

### TLS/SSL MQTT (Port 8883)

#### Server Configuration
```bash
python -m mcp_mqtt_bridge \
    --mqtt-broker secure-broker.example.com \
    --mqtt-port 8883 \
    --mqtt-username device01 \
    --mqtt-password secure_password
```

#### ESP32 Firmware Configuration
```c
mcp_bridge_config_t config = {
    .mqtt_broker_url = "mqtts://secure-broker.example.com:8883",
    .mqtt_username = "device01",
    .mqtt_password = "secure_password",
    .mqtt_ca_cert = ca_cert_pem,  // CA certificate
    .mqtt_client_cert = client_cert_pem,  // Client certificate
    .mqtt_client_key = client_key_pem     // Client private key
};
```

### Client Certificate Authentication

```c
// ESP32 with client certificates
mcp_bridge_config_t config = {
    .mqtt_broker_url = "mqtts://192.168.1.100:8883",
    .mqtt_ca_cert = ca_cert_pem,
    .mqtt_client_cert = client_cert_pem,
    .mqtt_client_key = client_key_pem,
    .mqtt_verify_peer = true
};
```

## 🧪 Testing Different MQTT Configurations

### Test MQTT Connection

```bash
# Test server connection to custom MQTT port
python test_remote_connection.py --test-local

# Test with specific MQTT broker
MQTT_BROKER="192.168.1.100" MQTT_PORT="1884" python -m mcp_mqtt_bridge --log-level DEBUG
```

### Manual MQTT Testing

```bash
# Install MQTT client tools
sudo apt install mosquitto-clients

# Test publish to custom port
mosquitto_pub -h 192.168.1.100 -p 1884 -t "test/topic" -m "Hello World"

# Test subscribe from custom port
mosquitto_sub -h 192.168.1.100 -p 1884 -t "devices/+/sensors/+/data"

# Test with authentication
mosquitto_pub -h broker.example.com -p 1884 -u username -P password -t "test" -m "hello"
```

### ESP32 MQTT Testing

```c
// Test function in ESP32 code
void test_mqtt_connection() {
    esp_mqtt_client_config_t mqtt_cfg = {
        .broker.address.uri = "mqtt://192.168.1.100:1884",
        .credentials.username = "test_user",
        .credentials.authentication.password = "test_pass"
    };
    
    esp_mqtt_client_handle_t client = esp_mqtt_client_init(&mqtt_cfg);
    esp_mqtt_client_start(client);
}
```

## 📊 Configuration Examples for Different Scenarios

### Home Network Setup
```bash
# Router with port forwarding
python -m mcp_mqtt_bridge \
    --mqtt-broker 192.168.1.100 \
    --mqtt-port 1883 \
    --enable-mcp-server \
    --mcp-host 0.0.0.0 \
    --mcp-port 8000
```

### Corporate Network Setup
```bash
# Corporate network with custom ports
python -m mcp_mqtt_bridge \
    --mqtt-broker mqtt.corp.example.com \
    --mqtt-port 9883 \
    --mqtt-username corp_device \
    --mqtt-password $CORP_MQTT_PASSWORD \
    --enable-mcp-server \
    --mcp-port 8080
```

### Cloud Deployment
```bash
# Cloud server with load balancer
python -m mcp_mqtt_bridge \
    --mqtt-broker internal-mqtt.cloud \
    --mqtt-port 1883 \
    --enable-mcp-server \
    --mcp-host 0.0.0.0 \
    --mcp-port 8000
```

### IoT Farm/Industrial
```bash
# Industrial setup with high availability
python -m mcp_mqtt_bridge \
    --mqtt-broker ha-mqtt-cluster.industrial.local \
    --mqtt-port 8883 \
    --mqtt-username industrial_gateway \
    --mqtt-password $INDUSTRIAL_PASSWORD \
    --enable-mcp-server \
    --mcp-port 8443
```

## 🚨 Troubleshooting MQTT Port Issues

### Connection Problems

```bash
# Check if MQTT broker is running on custom port
telnet 192.168.1.100 1884

# Check with nmap
nmap -p 1884 192.168.1.100

# Test MQTT connectivity
mosquitto_pub -h 192.168.1.100 -p 1884 -t "test" -m "hello"
```

### Firewall Configuration

```bash
# Open custom MQTT port
sudo ufw allow 1884/tcp

# For secure MQTT
sudo ufw allow 8883/tcp

# Check firewall status
sudo ufw status
```

### ESP32 Connection Issues

```c
// Add debug logging in ESP32 code
#include "esp_log.h"

static const char *TAG = "MQTT_TEST";

void mqtt_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data) {
    switch (event_id) {
        case MQTT_EVENT_CONNECTED:
            ESP_LOGI(TAG, "MQTT Connected to broker:port");
            break;
        case MQTT_EVENT_DISCONNECTED:
            ESP_LOGI(TAG, "MQTT Disconnected");
            break;
        case MQTT_EVENT_ERROR:
            ESP_LOGE(TAG, "MQTT Error occurred");
            break;
    }
}
```

## Summary

✅ **Server MQTT Port**: Configurable via `--mqtt-port` or `MQTT_PORT` env var  
✅ **ESP32 MQTT Port**: Configurable via Kconfig or code  
✅ **Security**: Support for TLS, authentication, certificates  
✅ **Cloud Ready**: Works with AWS IoT, Azure IoT, Google Cloud IoT  
✅ **Testing Tools**: Built-in connection testing and debugging  

The system supports any MQTT port configuration you need, from simple local setups to enterprise-grade cloud deployments!