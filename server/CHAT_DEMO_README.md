# 💬 IoT Chat Demo with OpenAI

Chat with an AI that can actually control your IoT devices! This demo creates a complete end-to-end system where you can have natural conversations with ChatGPT and it will control your mock ESP32 devices.

## 🎯 **What This Does**

```
You: "Turn on the kitchen LED"
🤖 AI: "I'll turn on the LED in the kitchen for you."
     🔧 Calling control_actuator with args: {'device_id': 'esp32_kitchen', 'actuator_type': 'led', 'action': 'on'}
     ✅ Successfully turned on the kitchen LED!

You: "What's the temperature in all rooms?"
🤖 AI: "Let me check the temperature in all your rooms."
     🔧 Calling read_sensor with args: {'sensor_type': 'temperature'}
     📊 Kitchen: 23.2°C, Living Room: 21.8°C, Bedroom: 22.5°C
```

## 🚀 **Quick Start**

### **1. Get OpenAI API Key**
```bash
# Get your API key from: https://platform.openai.com/api-keys
export OPENAI_API_KEY="your-api-key-here"
```

### **2. Install Requirements**
```bash
cd server
source venv/bin/activate
pip install -r requirements-chat.txt
```

### **3. Start Everything**
```bash
# This starts MQTT broker, mock devices, bridge, and chat interface
python start_chat_demo.py
```

**That's it!** 🎉 You can now chat with an AI that controls IoT devices!

---

## 🎮 **Example Conversations**

### **Device Discovery**
```
You: Show me all my devices
AI: You have 3 devices connected:
    • esp32_kitchen (Kitchen) - Temperature, humidity, LED, relay
    • esp32_living (Living Room) - Temperature, light sensor, LED  
    • esp32_bedroom (Bedroom) - Temperature, humidity, motion, LED
```

### **Sensor Reading**
```
You: Is it warm in the bedroom?
AI: Let me check the bedroom temperature for you.
    🔧 Reading temperature sensor from bedroom...
    The bedroom temperature is 22.5°C, which is quite comfortable!
```

### **Device Control**
```
You: Turn off all the lights
AI: I'll turn off all the LEDs for you.
    🔧 Turning off kitchen LED...
    🔧 Turning off living room LED...
    🔧 Turning off bedroom LED...
    ✅ All lights are now off!
```

### **Smart Automation**
```
You: If the kitchen is too hot, turn on the fan
AI: Let me check the kitchen temperature first.
    🔧 Reading kitchen temperature...
    The kitchen is 24.1°C. I'll turn on the relay (fan) to cool it down.
    🔧 Turning on kitchen relay...
    ✅ Kitchen fan is now running!
```

---

## 🛠️ **Manual Setup (Alternative)**

If you prefer to start components individually:

### **Terminal 1: MQTT Broker**
```bash
mosquitto -v
```

### **Terminal 2: Mock Devices**
```bash
cd server
source venv/bin/activate
python examples/mock_esp32_device.py --devices 3
```

### **Terminal 3: MCP Bridge**
```bash
cd server  
source venv/bin/activate
python -m mcp_mqtt_bridge --log-level INFO
```

### **Terminal 4: Chat Interface**
```bash
cd server
source venv/bin/activate
export OPENAI_API_KEY="your-key"
python chat_with_devices.py
```

---

## 💡 **Special Commands**

While chatting, you can use these special commands:

- **`devices`** - Show all available devices
- **`help`** - Show example commands
- **`quit`** / **`exit`** / **`bye`** - End the chat

---

## 🎯 **Try These Commands**

### **Basic Device Control**
- *"Turn on the kitchen LED"*
- *"Turn off all lights"*
- *"Toggle the living room LED"*
- *"Start the garage relay"*

### **Sensor Monitoring**  
- *"What's the temperature in the kitchen?"*
- *"Check humidity in all rooms"*
- *"Is there motion in the bedroom?"*
- *"Show me all sensor readings"*

### **Smart Queries**
- *"Which room is the warmest?"*
- *"Are there any device errors?"*
- *"Show me device info for the kitchen"*
- *"What devices are online?"*

### **Complex Automation**
- *"If the living room is too bright, dim the lights"*
- *"Turn on heating if any room is below 20°C"*
- *"Check all sensors and report any issues"*

---

## 🔧 **Troubleshooting**

### **"No OpenAI API Key"**
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

### **"MCP Connection Failed"**
Make sure the bridge is running:
```bash
python -m mcp_mqtt_bridge --log-level DEBUG
```

### **"No Devices Found"**
Check that mock devices are running:
```bash
python examples/mock_esp32_device.py --devices 2
```

### **"Mosquitto Not Found"**
Install MQTT broker:
```bash
sudo apt install mosquitto  # Ubuntu/Debian
brew install mosquitto       # macOS
```

---

## 🏗️ **How It Works**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   You (Chat)    │───▶│  OpenAI GPT-4   │───▶│  MCP Protocol   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Mock Devices   │◀───│  MQTT Broker    │◀───│  MCP-MQTT Bridge│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

1. **You** type a message in the console
2. **OpenAI GPT-4** processes your request and decides if it needs to use IoT tools
3. **MCP Protocol** carries the tool calls to the bridge
4. **MCP-MQTT Bridge** translates commands to MQTT messages
5. **Mock Devices** receive commands and respond with sensor data
6. **Response flows back** through the same path to you

---

## 🎉 **What Makes This Cool**

✅ **Natural Language Control** - Just talk normally to control devices  
✅ **Real IoT Integration** - Actual MQTT communication with realistic device simulation  
✅ **Smart Understanding** - AI understands context like "all lights" or "too hot"  
✅ **Live Feedback** - See exactly what commands are being sent to devices  
✅ **Extensible** - Easy to add new device types and capabilities  

---

## 🚀 **Next Steps**

1. **Try Different Models**: Change `gpt-4` to `gpt-3.5-turbo` in `chat_with_devices.py`
2. **Add More Devices**: Modify `mock_device_config.yaml` to create new device types
3. **Custom Commands**: Train the AI with specific phrases for your home automation
4. **Real Hardware**: Replace mock devices with actual ESP32 firmware
5. **Voice Interface**: Add speech-to-text for voice control

---

*Have fun chatting with your AI-controlled IoT devices!* 🏠🤖 