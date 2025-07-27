#!/usr/bin/env python3
"""
Debug MQTT message flow
"""

import time
import json
import paho.mqtt.client as mqtt
import threading
from datetime import datetime

messages_received = []

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"🔗 Connected to MQTT broker (rc: {rc})")
    if rc == 0:
        # Subscribe to all device topics
        topics = [
            "devices/+/capabilities",
            "devices/+/sensors/+/data", 
            "devices/+/actuators/+/status",
            "devices/+/status",
            "devices/+/error"
        ]
        for topic in topics:
            client.subscribe(topic)
            print(f"📡 Subscribed to: {topic}")

def on_message(client, userdata, msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    topic = msg.topic
    try:
        payload = json.loads(msg.payload.decode())
    except:
        payload = msg.payload.decode()
    
    message_info = f"[{timestamp}] {topic}: {payload}"
    print(f"📨 {message_info}")
    messages_received.append(message_info)

def main():
    print("🔍 MQTT Message Flow Debugger")
    print("=" * 50)
    
    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="debug_monitor")
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        # Connect to broker
        print("🚀 Connecting to MQTT broker...")
        client.connect("localhost", 1883, 60)
        client.loop_start()
        
        print("⏱️  Monitoring for 20 seconds...")
        print("   (Start mock devices in another terminal)")
        print("   Command: python examples/mock_esp32_device.py --devices 1")
        
        # Monitor for messages
        for i in range(20):
            time.sleep(1)
            if i % 5 == 0:
                print(f"   ... {20-i} seconds remaining ...")
        
        print(f"\n📊 Summary:")
        print(f"   📨 Total messages received: {len(messages_received)}")
        
        if messages_received:
            print("\n📋 Message log:")
            for msg in messages_received[-10:]:  # Show last 10 messages
                print(f"   {msg}")
        else:
            print("   ⚠️  No messages received!")
            print("   Possible issues:")
            print("     - Mock devices not connecting")
            print("     - MQTT topics mismatch")
            print("     - Network connectivity issues")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.disconnect()
        client.loop_stop()

if __name__ == "__main__":
    main() 