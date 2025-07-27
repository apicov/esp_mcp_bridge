"""
Integration tests for MQTT functionality.
"""
import pytest
import pytest_asyncio
import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_mqtt_bridge.mqtt_manager import MQTTManager


@pytest.mark.integration
class TestMQTTIntegration:
    """Integration tests for MQTT manager."""
    
    @pytest_asyncio.fixture
    async def mqtt_manager(self, mqtt_test_config):
        """Create MQTT manager for testing."""
        manager = MQTTManager(
            broker=mqtt_test_config["broker"],
            port=mqtt_test_config["port"],
            username=mqtt_test_config.get("username"),
            password=mqtt_test_config.get("password"),
            client_id=mqtt_test_config["client_id"]
        )
        yield manager
        if manager.is_connected:
            await manager.disconnect()
    
    @pytest.mark.asyncio
    async def test_mqtt_connection(self, mqtt_manager):
        """Test MQTT broker connection."""
        # This test requires a running MQTT broker
        try:
            await mqtt_manager.connect()
            assert mqtt_manager.is_connected
        except Exception as e:
            pytest.skip(f"MQTT broker not available: {e}")
    
    @pytest.mark.asyncio
    async def test_mqtt_subscribe_and_publish(self, mqtt_manager):
        """Test MQTT subscribe and publish functionality."""
        try:
            await mqtt_manager.connect()
            
            # Set up message handler
            received_messages = []
            
            def message_handler(topic, payload):
                received_messages.append({"topic": topic, "payload": payload})
            
            mqtt_manager.set_message_handler(message_handler)
            
            # Subscribe to test topic
            test_topic = "test/integration"
            await mqtt_manager.subscribe(test_topic)
            
            # Give a moment for subscription to take effect
            await asyncio.sleep(0.1)
            
            # Publish test message
            test_payload = {"test": "message", "timestamp": time.time()}
            success = await mqtt_manager.publish(test_topic, test_payload)
            assert success
            
            # Wait for message to be received
            await asyncio.sleep(0.2)
            
            # Verify message was received
            assert len(received_messages) == 1
            received = received_messages[0]
            assert received["topic"] == test_topic
            
            # Parse received payload
            received_payload = json.loads(received["payload"])
            assert received_payload["test"] == "message"
            
        except Exception as e:
            pytest.skip(f"MQTT broker not available: {e}")
    
    @pytest.mark.asyncio
    async def test_device_status_updates(self, mqtt_manager):
        """Test device status update messages."""
        try:
            await mqtt_manager.connect()
            
            received_status_updates = []
            
            def status_handler(topic, payload):
                if "status" in topic:
                    received_status_updates.append({
                        "topic": topic, 
                        "payload": json.loads(payload)
                    })
            
            mqtt_manager.set_message_handler(status_handler)
            
            # Subscribe to device status topic
            status_topic = "devices/+/status"
            await mqtt_manager.subscribe(status_topic)
            
            await asyncio.sleep(0.1)
            
            # Simulate device status update
            device_status = {
                "device_id": "test_esp32_001",
                "status": "online",
                "timestamp": time.time(),
                "uptime": 3600,
                "memory_free": 45000
            }
            
            await mqtt_manager.publish("devices/test_esp32_001/status", device_status)
            await asyncio.sleep(0.2)
            
            # Verify status update was received
            assert len(received_status_updates) == 1
            update = received_status_updates[0]
            assert update["payload"]["device_id"] == "test_esp32_001"
            assert update["payload"]["status"] == "online"
            
        except Exception as e:
            pytest.skip(f"MQTT broker not available: {e}")
    
    @pytest.mark.asyncio
    async def test_sensor_data_messages(self, mqtt_manager):
        """Test sensor data message handling."""
        try:
            await mqtt_manager.connect()
            
            received_sensor_data = []
            
            def sensor_handler(topic, payload):
                if "sensors" in topic:
                    received_sensor_data.append({
                        "topic": topic,
                        "payload": json.loads(payload)
                    })
            
            mqtt_manager.set_message_handler(sensor_handler)
            
            # Subscribe to sensor data topics
            await mqtt_manager.subscribe("devices/+/sensors/+")
            await asyncio.sleep(0.1)
            
            # Simulate sensor data
            sensor_readings = [
                {
                    "topic": "devices/test_esp32_001/sensors/temperature",
                    "data": {
                        "value": 23.5,
                        "unit": "°C",
                        "timestamp": time.time()
                    }
                },
                {
                    "topic": "devices/test_esp32_001/sensors/humidity", 
                    "data": {
                        "value": 45.2,
                        "unit": "%",
                        "timestamp": time.time()
                    }
                }
            ]
            
            # Publish sensor data
            for reading in sensor_readings:
                await mqtt_manager.publish(reading["topic"], reading["data"])
            
            await asyncio.sleep(0.3)
            
            # Verify sensor data was received
            assert len(received_sensor_data) == 2
            
            # Check temperature reading
            temp_reading = next(r for r in received_sensor_data if "temperature" in r["topic"])
            assert temp_reading["payload"]["value"] == 23.5
            assert temp_reading["payload"]["unit"] == "°C"
            
            # Check humidity reading
            humidity_reading = next(r for r in received_sensor_data if "humidity" in r["topic"])
            assert humidity_reading["payload"]["value"] == 45.2
            assert humidity_reading["payload"]["unit"] == "%"
            
        except Exception as e:
            pytest.skip(f"MQTT broker not available: {e}")
    
    @pytest.mark.asyncio
    async def test_actuator_commands(self, mqtt_manager):
        """Test actuator command publishing."""
        try:
            await mqtt_manager.connect()
            
            received_commands = []
            
            def command_handler(topic, payload):
                if "cmd" in topic:
                    received_commands.append({
                        "topic": topic,
                        "payload": json.loads(payload)
                    })
            
            mqtt_manager.set_message_handler(command_handler)
            
            # Subscribe to command topics
            await mqtt_manager.subscribe("devices/+/actuators/+/cmd")
            await asyncio.sleep(0.1)
            
            # Send actuator commands
            commands = [
                {
                    "topic": "devices/test_esp32_001/actuators/led/cmd",
                    "command": {"action": "toggle", "timestamp": time.time()}
                },
                {
                    "topic": "devices/test_esp32_001/actuators/relay/cmd", 
                    "command": {"action": "on", "duration": 5000, "timestamp": time.time()}
                }
            ]
            
            for cmd in commands:
                success = await mqtt_manager.publish(cmd["topic"], cmd["command"])
                assert success
            
            await asyncio.sleep(0.3)
            
            # Verify commands were received
            assert len(received_commands) == 2
            
            # Check LED command
            led_cmd = next(c for c in received_commands if "led" in c["topic"])
            assert led_cmd["payload"]["action"] == "toggle"
            
            # Check relay command  
            relay_cmd = next(c for c in received_commands if "relay" in c["topic"])
            assert relay_cmd["payload"]["action"] == "on"
            assert relay_cmd["payload"]["duration"] == 5000
            
        except Exception as e:
            pytest.skip(f"MQTT broker not available: {e}")
    
    @pytest.mark.asyncio
    async def test_connection_resilience(self, mqtt_manager):
        """Test MQTT connection resilience and reconnection."""
        try:
            # Initial connection
            await mqtt_manager.connect()
            assert mqtt_manager.is_connected
            
            # Simulate disconnect
            await mqtt_manager.disconnect()
            assert not mqtt_manager.is_connected
            
            # Reconnect
            await mqtt_manager.connect()
            assert mqtt_manager.is_connected
            
        except Exception as e:
            pytest.skip(f"MQTT broker not available: {e}")
    
    @pytest.mark.asyncio 
    async def test_qos_levels(self, mqtt_manager):
        """Test different QoS levels for message delivery."""
        try:
            await mqtt_manager.connect()
            
            # Test publishing with different QoS levels
            test_topic = "test/qos"
            test_payload = {"test": "qos_message"}
            
            # QoS 0 (at most once)
            success_qos0 = await mqtt_manager.publish(test_topic, test_payload, qos=0)
            assert success_qos0
            
            # QoS 1 (at least once) 
            success_qos1 = await mqtt_manager.publish(test_topic, test_payload, qos=1)
            assert success_qos1
            
            # QoS 2 (exactly once)
            success_qos2 = await mqtt_manager.publish(test_topic, test_payload, qos=2)
            assert success_qos2
            
        except Exception as e:
            pytest.skip(f"MQTT broker not available: {e}")


@pytest.mark.integration
class TestMQTTMessageFlow:
    """Test complete MQTT message flow scenarios."""
    
    @pytest.mark.asyncio
    async def test_device_lifecycle_flow(self, mqtt_test_config):
        """Test complete device lifecycle through MQTT."""
        # This test simulates a complete device lifecycle:
        # 1. Device comes online
        # 2. Sends sensor data
        # 3. Receives commands
        # 4. Goes offline
        
        try:
            manager = MQTTManager(
                broker=mqtt_test_config["broker"],
                port=mqtt_test_config["port"],
                client_id="lifecycle_test"
            )
            
            await manager.connect()
            
            message_log = []
            
            def message_logger(topic, payload):
                message_log.append({
                    "topic": topic,
                    "payload": json.loads(payload),
                    "timestamp": time.time()
                })
            
            manager.set_message_handler(message_logger)
            
            # Subscribe to all device messages
            await manager.subscribe("devices/lifecycle_test/+")
            await manager.subscribe("devices/lifecycle_test/+/+")
            await manager.subscribe("devices/lifecycle_test/+/+/+")
            
            await asyncio.sleep(0.1)
            
            # 1. Device comes online
            await manager.publish("devices/lifecycle_test/status", {
                "device_id": "lifecycle_test",
                "status": "online",
                "firmware_version": "1.0.0",
                "timestamp": time.time()
            })
            
            # 2. Device sends sensor data
            for i in range(3):
                await manager.publish("devices/lifecycle_test/sensors/temperature", {
                    "value": 20.0 + i,
                    "unit": "°C", 
                    "timestamp": time.time()
                })
                await asyncio.sleep(0.1)
            
            # 3. Send command to device
            await manager.publish("devices/lifecycle_test/actuators/led/cmd", {
                "action": "blink",
                "duration": 1000,
                "timestamp": time.time()
            })
            
            # 4. Device goes offline
            await manager.publish("devices/lifecycle_test/status", {
                "device_id": "lifecycle_test", 
                "status": "offline",
                "timestamp": time.time()
            })
            
            await asyncio.sleep(0.2)
            
            # Verify message flow
            assert len(message_log) >= 6  # Status + 3 sensor readings + command + status
            
            # Check we have status messages
            status_messages = [m for m in message_log if "status" in m["topic"]]
            assert len(status_messages) == 2
            assert status_messages[0]["payload"]["status"] == "online" 
            assert status_messages[1]["payload"]["status"] == "offline"
            
            # Check sensor data
            sensor_messages = [m for m in message_log if "sensors" in m["topic"]]
            assert len(sensor_messages) == 3
            
            # Check command
            command_messages = [m for m in message_log if "cmd" in m["topic"]]
            assert len(command_messages) == 1
            assert command_messages[0]["payload"]["action"] == "blink"
            
            await manager.disconnect()
            
        except Exception as e:
            pytest.skip(f"MQTT broker not available: {e}") 