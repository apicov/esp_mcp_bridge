# Remote FastMCP Setup Guide

This guide shows you how to run the MCP bridge on a remote server and connect to it from your desktop.

## Architecture Overview

```
┌─────────────────┐    Network    ┌─────────────────┐    MQTT     ┌─────────────────┐
│  Your Desktop   │◄─────────────►│  Remote Server  │◄──────────►│   ESP32 Devices │
│                 │               │                 │            │                 │
│ • Chat Client   │               │ • FastMCP Bridge│            │ • Sensors       │
│ • OpenAI API    │               │ • HTTP Server   │            │ • Actuators     │
│                 │               │ • Database      │            │                 │
└─────────────────┘               └─────────────────┘            └─────────────────┘
```

## Setup Methods

### Method 1: HTTP/REST API (Recommended)

This uses the existing HTTP server for remote connections.

#### On Remote Server (e.g., Raspberry Pi, VPS):

```bash
# 1. Start bridge with HTTP server
python -m mcp_mqtt_bridge \
    --enable-mcp-server \
    --mcp-host 0.0.0.0 \
    --mcp-port 8000 \
    --mqtt-broker localhost

# 2. Or use the enhanced remote server
python -m mcp_mqtt_bridge \
    --enable-mcp-server \
    --use-fastmcp \
    --mcp-host 0.0.0.0 \
    --mcp-port 8000
```

#### On Your Desktop:

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key-here"

# Connect to remote server
python remote_fastmcp_chat.py --remote-host 192.168.1.100

# Custom port
python remote_fastmcp_chat.py --remote-host server.example.com --remote-port 8000
```

### Method 2: Direct REST API Access

You can also use the existing chat with remote capabilities:

```bash
# On your desktop
python chat_with_devices.py --remote-host 192.168.1.100 --remote-port 8000
```

## Server Setup Examples

### 1. Local Network Server (Raspberry Pi)

```bash
# On Raspberry Pi
cd /path/to/esp_mcp_bridge/server

# Install dependencies
pip install -r requirements.txt

# Start with mock devices for testing
python examples/mock_esp32_device.py --devices 3 &

# Start bridge server
python -m mcp_mqtt_bridge \
    --enable-mcp-server \
    --mcp-host 0.0.0.0 \
    --mcp-port 8000 \
    --mqtt-broker localhost \
    --log-level INFO
```

### 2. Cloud Server (VPS/AWS/DigitalOcean)

```bash
# On cloud server
cd /path/to/esp_mcp_bridge/server

# Install dependencies
pip install -r requirements.txt

# Start MQTT broker
docker run -d -p 1883:1883 --name mosquitto eclipse-mosquitto

# Start bridge with external access
python -m mcp_mqtt_bridge \
    --enable-mcp-server \
    --mcp-host 0.0.0.0 \
    --mcp-port 8000 \
    --mqtt-broker localhost \
    --db-path /data/iot_bridge.db
```

### 3. Docker Deployment

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  mosquitto:
    image: eclipse-mosquitto
    ports:
      - "1883:1883"
    volumes:
      - mosquitto_data:/mosquitto/data
      - mosquitto_log:/mosquitto/log

  mcp-bridge:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MQTT_BROKER=mosquitto
      - MCP_HOST=0.0.0.0
      - MCP_PORT=8000
    depends_on:
      - mosquitto
    volumes:
      - bridge_data:/app/data
    command: >
      python -m mcp_mqtt_bridge
      --enable-mcp-server
      --mqtt-broker mosquitto
      --mcp-host 0.0.0.0
      --mcp-port 8000
      --db-path /app/data/bridge.db

volumes:
  mosquitto_data:
  mosquitto_log:
  bridge_data:
```

## Network Configuration

### Firewall Rules

On the remote server, ensure these ports are open:

```bash
# HTTP/REST API
sudo ufw allow 8000/tcp

# MQTT (if devices connect from external network)
sudo ufw allow 1883/tcp

# Check status
sudo ufw status
```

### Port Forwarding (if behind router)

Forward these ports on your router:
- `8000` → Server IP:8000 (FastMCP HTTP)
- `1883` → Server IP:1883 (MQTT, if needed)

## Connection Testing

### 1. Test Server Health

```bash
# Check if server is running
curl http://your-server-ip:8000/health

# Expected response:
# {"status": "healthy", "service": "mcp-mqtt-bridge", "version": "1.0.0"}
```

### 2. Test Available Tools

```bash
# List available tools
curl http://your-server-ip:8000/tools

# Expected response with list of available tools
```

### 3. Test Tool Execution

```bash
# List devices
curl -X POST http://your-server-ip:8000/tools/list_devices \
  -H "Content-Type: application/json" \
  -d '{"arguments": {}}'
```

## Desktop Client Usage

### Quick Start

```bash
# Set API key
export OPENAI_API_KEY="your-openai-api-key"

# Connect to remote server
python remote_fastmcp_chat.py --remote-host 192.168.1.100

# Chat with your devices
💬 You: Show me all devices
🤖 Assistant: I can see 3 ESP32 devices connected to your remote system...

💬 You: Read all sensors  
🤖 Assistant: Here are the current readings from all sensors on the remote system...
```

### Advanced Usage

```bash
# Different server
python remote_fastmcp_chat.py --remote-host my-iot-server.com --remote-port 8000

# With custom timeout settings
python remote_fastmcp_chat.py --remote-host 192.168.1.100 --timeout 30
```

## Troubleshooting

### Connection Issues

1. **Server not reachable**:
   ```bash
   # Test basic connectivity
   ping your-server-ip
   telnet your-server-ip 8000
   ```

2. **Port blocked**:
   ```bash
   # Check if port is open
   nmap -p 8000 your-server-ip
   ```

3. **Server not running**:
   ```bash
   # On server, check if process is running
   ps aux | grep mcp_mqtt_bridge
   netstat -tulpn | grep :8000
   ```

### Performance Issues

1. **Slow responses**:
   - Check network latency: `ping your-server-ip`
   - Use local network instead of internet when possible
   - Consider running OpenAI API calls locally

2. **Connection timeouts**:
   - Increase timeout values in client
   - Check server logs for errors
   - Verify server has sufficient resources

### Security Considerations

1. **Authentication** (Future enhancement):
   - Consider adding API key authentication
   - Use HTTPS in production
   - Implement rate limiting

2. **Network Security**:
   - Use VPN for internet connections
   - Restrict access by IP address
   - Use firewall rules

## Configuration Files

### Server Config (`server_config.yaml`)

```yaml
mqtt:
  broker: localhost
  port: 1883
  username: null
  password: null

database:
  path: ./data/bridge.db

mcp_server:
  host: 0.0.0.0
  port: 8000
  enable: true

logging:
  level: INFO
```

### Client Config (`client_config.yaml`)

```yaml
remote_server:
  host: 192.168.1.100
  port: 8000
  timeout: 30

openai:
  model: gpt-4
  temperature: 0.1
```

## Advanced Scenarios

### 1. Multiple Remote Servers

Connect to different IoT systems:

```bash
# Home system
python remote_fastmcp_chat.py --remote-host home.example.com

# Office system  
python remote_fastmcp_chat.py --remote-host office.example.com

# Factory system
python remote_fastmcp_chat.py --remote-host factory.example.com
```

### 2. Load Balancing

Use nginx for load balancing multiple bridge servers:

```nginx
upstream mcp_bridge {
    server 192.168.1.100:8000;
    server 192.168.1.101:8000;
    server 192.168.1.102:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://mcp_bridge;
    }
}
```

### 3. Monitoring and Alerting

Set up monitoring for your remote bridge:

```bash
# Health check script
#!/bin/bash
if curl -f http://your-server:8000/health > /dev/null 2>&1; then
    echo "Bridge is healthy"
else
    echo "Bridge is down - sending alert"
    # Send notification
fi
```

## Summary

The remote setup allows you to:

✅ **Run bridge on any server** (Raspberry Pi, VPS, cloud)  
✅ **Connect from anywhere** with internet access  
✅ **Use local OpenAI API** (stays on your desktop)  
✅ **Real-time device control** over network  
✅ **Multiple connection methods** (HTTP, WebSocket)  
✅ **Production-ready deployment** with Docker  

This setup gives you the flexibility to centralize your IoT infrastructure while maintaining a responsive chat interface on your local machine!