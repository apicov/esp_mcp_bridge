#!/usr/bin/env python3
"""
Mock ESP32 Device Simulator for MCP-MQTT Bridge Testing

This script simulates one or more ESP32 devices connected via MQTT,
allowing testing of the MCP-MQTT bridge without physical hardware.
"""

import asyncio
import json
import logging
import random
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import argparse

try:
    import paho.mqtt.client as mqtt
    import yaml
except ImportError:
    print("Required packages missing. Install with:")
    print("pip install paho-mqtt PyYAML")
    exit(1)


@dataclass
class SensorConfig:
    """Configuration for a simulated sensor"""
    name: str
    sensor_type: str
    unit: str
    min_value: float
    max_value: float
    base_value: float
    variation: float = 2.0  # Standard deviation for noise
    update_interval: float = 10.0  # Seconds between updates
    drift_rate: float = 0.01  # Slow drift rate per update


@dataclass
class ActuatorConfig:
    """Configuration for a simulated actuator"""
    name: str
    actuator_type: str
    initial_state: str = "off"
    supported_actions: List[str] = field(default_factory=lambda: ["on", "off", "toggle"])


@dataclass
class DeviceConfig:
    """Configuration for a mock ESP32 device"""
    device_id: str
    device_type: str = "ESP32"
    firmware_version: str = "1.0.0"
    location: str = "test_lab"
    sensors: List[SensorConfig] = field(default_factory=list)
    actuators: List[ActuatorConfig] = field(default_factory=list)
    wifi_rssi_range: tuple = (-80, -40)  # Fixed: min first, max second
    memory_usage_range: tuple = (60, 85)
    cpu_usage_range: tuple = (10, 30)


class MockESP32Device:
    """Simulates an ESP32 device with realistic behavior"""
    
    def __init__(self, config: DeviceConfig, mqtt_broker: str = "localhost", 
                 mqtt_port: int = 1883, mqtt_username: str = None, 
                 mqtt_password: str = None):
        self.config = config
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        
        # Device state
        self.online = False
        self.sensor_values = {}
        self.actuator_states = {}
        self.last_sensor_update = {}
        self.uptime_start = datetime.now()
        self.message_count = 0
        self.error_count = 0
        
        # MQTT client setup
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, 
                                 client_id=f"{config.device_id}_mock")
        if mqtt_username and mqtt_password:
            self.client.username_pw_set(mqtt_username, mqtt_password)
        
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Initialize sensor values and actuator states
        self._initialize_sensors()
        self._initialize_actuators()
        
        # Setup logging
        self.logger = logging.getLogger(f"MockESP32.{config.device_id}")
        
        # Task management
        self.tasks = []
        self.running = False
    
    def _initialize_sensors(self):
        """Initialize sensor values with realistic starting points"""
        for sensor in self.config.sensors:
            self.sensor_values[sensor.name] = {
                "current_value": sensor.base_value + random.uniform(-sensor.variation, sensor.variation),
                "drift_offset": 0.0,
                "config": sensor
            }
            self.last_sensor_update[sensor.name] = 0
    
    def _initialize_actuators(self):
        """Initialize actuator states"""
        for actuator in self.config.actuators:
            self.actuator_states[actuator.name] = {
                "state": actuator.initial_state,
                "config": actuator,
                "last_action": datetime.now().isoformat()
            }
    
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Handle MQTT connection"""
        if rc == 0:
            self.online = True
            self.logger.info(f"Connected to MQTT broker")
            
            # Subscribe to command topics
            for actuator in self.config.actuators:
                topic = f"devices/{self.config.device_id}/actuators/{actuator.name}/cmd"
                client.subscribe(topic)
                self.logger.info(f"Subscribed to {topic}")
            
            # Subscribe to general device commands
            client.subscribe(f"devices/{self.config.device_id}/cmd")
            
            # Publish device capabilities and initial status (sync versions)
            try:
                # Call sync versions since we're not in an async context
                import threading
                threading.Thread(target=self._publish_capabilities_sync).start()
                threading.Thread(target=self._publish_status_sync).start()
            except Exception as e:
                self.logger.error(f"Error publishing initial data: {e}")
        else:
            self.logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        """Handle MQTT disconnection"""
        self.online = False
        self.logger.warning(f"Disconnected from MQTT broker: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            self.logger.info(f"Received command on {topic}: {payload}")
            
            if "/actuators/" in topic and "/cmd" in topic:
                # Extract actuator name from topic
                parts = topic.split("/")
                actuator_name = parts[3]  # devices/{id}/actuators/{name}/cmd
                # Use thread to handle command since we're not in async context
                import threading
                threading.Thread(target=self._handle_actuator_command_sync, args=(actuator_name, payload)).start()
            elif topic.endswith("/cmd"):
                # General device command
                import threading
                threading.Thread(target=self._handle_device_command_sync, args=(payload,)).start()
                
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")
            self.error_count += 1
    
    def _handle_actuator_command_sync(self, actuator_name: str, command: Dict[str, Any]):
        """Sync version of actuator command handler"""
        try:
            if actuator_name not in self.actuator_states:
                self.logger.warning(f"Unknown actuator: {actuator_name}")
                return
            
            actuator_state = self.actuator_states[actuator_name]
            action = command.get("action", "").lower()
            
            if action in actuator_state["config"].supported_actions:
                old_state = actuator_state["state"]
                
                if action == "toggle":
                    # Toggle between on/off
                    new_state = "off" if actuator_state["state"] == "on" else "on"
                else:
                    new_state = action
                
                actuator_state["state"] = new_state
                actuator_state["last_action"] = datetime.now().isoformat()
                
                self.logger.info(f"Actuator {actuator_name}: {old_state} -> {new_state}")
                
                # Publish actuator status update
                self._publish_actuator_status_sync(actuator_name)
                
                # Simulate actuator affecting sensors (e.g., LED affecting light sensor)
                if actuator_name == "led" and "light" in self.sensor_values:
                    # LED on increases ambient light reading
                    offset = 50 if new_state == "on" else -50
                    self.sensor_values["light"]["current_value"] = max(0, 
                        self.sensor_values["light"]["current_value"] + offset)
            else:
                self.logger.warning(f"Unsupported action '{action}' for actuator {actuator_name}")
        except Exception as e:
            self.logger.error(f"Error handling actuator command: {e}")
    
    def _handle_device_command_sync(self, command: Dict[str, Any]):
        """Sync version of device command handler"""
        try:
            cmd_type = command.get("command", "").lower()
            
            if cmd_type == "restart":
                self.logger.info("Simulating device restart...")
                self._publish_status_sync()  # Use sync version
                time.sleep(2)  # Simulate restart time
                self.uptime_start = datetime.now()
                self._publish_status_sync()
                self._publish_capabilities_sync()
                
            elif cmd_type == "get_info":
                self._publish_device_info_sync()
                
            elif cmd_type == "set_interval":
                # Change sensor update interval
                interval = command.get("interval", 10)
                for sensor_name in self.sensor_values:
                    sensor_config = self.sensor_values[sensor_name]["config"]
                    sensor_config.update_interval = max(1, interval)
                self.logger.info(f"Updated sensor interval to {interval} seconds")
        except Exception as e:
            self.logger.error(f"Error handling device command: {e}")
    
    def _publish_actuator_status_sync(self, actuator_name: str):
        """Sync version of publish actuator status"""
        try:
            actuator_state = self.actuator_states[actuator_name]
            
            status = {
                "device_id": self.config.device_id,
                "actuator": actuator_name,
                "state": actuator_state["state"],
                "last_action": actuator_state["last_action"],
                "timestamp": datetime.now().isoformat()
            }
            
            topic = f"devices/{self.config.device_id}/actuators/{actuator_name}/status"
            self.client.publish(topic, json.dumps(status))
            self.logger.info(f"Published actuator status for {actuator_name}")
        except Exception as e:
            self.logger.error(f"Error publishing actuator status: {e}")
    
    def _publish_device_info_sync(self):
        """Sync version of publish device info"""
        try:
            info = {
                "device_id": self.config.device_id,
                "device_type": self.config.device_type,
                "firmware_version": self.config.firmware_version,
                "hardware_version": "Rev 1.0",
                "mac_address": f"AA:BB:CC:DD:EE:{random.randint(10,99):02X}",
                "location": self.config.location,
                "uptime_start": self.uptime_start.isoformat(),
                "current_sensors": len(self.config.sensors),
                "current_actuators": len(self.config.actuators),
                "timestamp": datetime.now().isoformat()
            }
            
            topic = f"devices/{self.config.device_id}/info"
            self.client.publish(topic, json.dumps(info))
            self.logger.info("Published device info")
        except Exception as e:
            self.logger.error(f"Error publishing device info: {e}")
    
    async def _handle_actuator_command(self, actuator_name: str, command: Dict[str, Any]):
        """Handle actuator control commands"""
        if actuator_name not in self.actuator_states:
            self.logger.warning(f"Unknown actuator: {actuator_name}")
            return
        
        actuator_state = self.actuator_states[actuator_name]
        action = command.get("action", "").lower()
        
        if action in actuator_state["config"].supported_actions:
            old_state = actuator_state["state"]
            
            if action == "toggle":
                # Toggle between on/off
                new_state = "off" if actuator_state["state"] == "on" else "on"
            else:
                new_state = action
            
            actuator_state["state"] = new_state
            actuator_state["last_action"] = datetime.now().isoformat()
            
            self.logger.info(f"Actuator {actuator_name}: {old_state} -> {new_state}")
            
            # Publish actuator status update
            await self._publish_actuator_status(actuator_name)
            
            # Simulate actuator affecting sensors (e.g., LED affecting light sensor)
            if actuator_name == "led" and "light" in self.sensor_values:
                # LED on increases ambient light reading
                offset = 50 if new_state == "on" else -50
                self.sensor_values["light"]["current_value"] = max(0, 
                    self.sensor_values["light"]["current_value"] + offset)
        else:
            self.logger.warning(f"Unsupported action '{action}' for actuator {actuator_name}")
    
    async def _handle_device_command(self, command: Dict[str, Any]):
        """Handle general device commands"""
        cmd_type = command.get("command", "").lower()
        
        if cmd_type == "restart":
            self.logger.info("Simulating device restart...")
            await self._publish_device_status("restarting")
            await asyncio.sleep(2)  # Simulate restart time
            self.uptime_start = datetime.now()
            await self._publish_device_status("online")
            await self._publish_device_capabilities()
            
        elif cmd_type == "get_info":
            await self._publish_device_info()
            
        elif cmd_type == "set_interval":
            # Change sensor update interval
            interval = command.get("interval", 10)
            for sensor_name in self.sensor_values:
                sensor_config = self.sensor_values[sensor_name]["config"]
                sensor_config.update_interval = max(1, interval)
            self.logger.info(f"Updated sensor interval to {interval} seconds")
    
    async def _publish_device_capabilities(self):
        """Publish device capabilities"""
        capabilities = {
            "device_id": self.config.device_id,
            "device_type": self.config.device_type,
            "firmware_version": self.config.firmware_version,
            "sensors": [
                {
                    "name": s.name,
                    "type": s.sensor_type,
                    "unit": s.unit,
                    "min_value": s.min_value,
                    "max_value": s.max_value,
                    "update_interval": s.update_interval
                }
                for s in self.config.sensors
            ],
            "actuators": [
                {
                    "name": a.name,
                    "type": a.actuator_type,
                    "supported_actions": a.supported_actions
                }
                for a in self.config.actuators
            ],
            "location": self.config.location,
            "timestamp": datetime.now().isoformat()
        }
        
        topic = f"devices/{self.config.device_id}/capabilities"
        self.client.publish(topic, json.dumps(capabilities))
        self.logger.info("Published device capabilities")
    
    async def _publish_device_status(self, status: str = "online"):
        """Publish device status"""
        uptime_seconds = int((datetime.now() - self.uptime_start).total_seconds())
        
        status_data = {
            "device_id": self.config.device_id,
            "status": status,
            "uptime": uptime_seconds,
            "wifi_rssi": random.randint(self.config.wifi_rssi_range[0], self.config.wifi_rssi_range[1]),
            "memory_usage": random.randint(*self.config.memory_usage_range),
            "cpu_usage": random.randint(*self.config.cpu_usage_range),
            "message_count": self.message_count,
            "error_count": self.error_count,
            "timestamp": datetime.now().isoformat()
        }
        
        topic = f"devices/{self.config.device_id}/status"
        self.client.publish(topic, json.dumps(status_data))
        self.message_count += 1
    
    def _publish_capabilities_sync(self):
        """Sync version of publish device capabilities for use in threads"""
        try:
            capabilities = {
                "device_id": self.config.device_id,
                "device_type": self.config.device_type,
                "firmware_version": self.config.firmware_version,
                "sensors": [
                    {
                        "name": s.name,
                        "type": s.sensor_type,
                        "unit": s.unit,
                        "min_value": s.min_value,
                        "max_value": s.max_value,
                        "update_interval": s.update_interval
                    }
                    for s in self.config.sensors
                ],
                "actuators": [
                    {
                        "name": a.name,
                        "type": a.actuator_type,
                        "supported_actions": a.supported_actions
                    }
                    for a in self.config.actuators
                ],
                "location": self.config.location,
                "timestamp": datetime.now().isoformat()
            }
            
            topic = f"devices/{self.config.device_id}/capabilities"
            self.client.publish(topic, json.dumps(capabilities))
            self.logger.info("Published device capabilities")
        except Exception as e:
            self.logger.error(f"Error publishing capabilities: {e}")
    
    def _publish_status_sync(self):
        """Sync version of publish device status for use in threads"""
        try:
            uptime_seconds = int((datetime.now() - self.uptime_start).total_seconds())
            
            status_data = {
                "device_id": self.config.device_id,
                "status": "online",
                "uptime": uptime_seconds,
                "wifi_rssi": random.randint(self.config.wifi_rssi_range[0], self.config.wifi_rssi_range[1]),
                "memory_usage": random.randint(*self.config.memory_usage_range),
                "cpu_usage": random.randint(*self.config.cpu_usage_range),
                "message_count": self.message_count,
                "error_count": self.error_count,
                "timestamp": datetime.now().isoformat()
            }
            
            topic = f"devices/{self.config.device_id}/status"
            self.client.publish(topic, json.dumps(status_data))
            self.message_count += 1
            self.logger.info("Published device status")
        except Exception as e:
            self.logger.error(f"Error publishing status: {e}")
    
    async def _publish_device_info(self):
        """Publish detailed device information"""
        info = {
            "device_id": self.config.device_id,
            "device_type": self.config.device_type,
            "firmware_version": self.config.firmware_version,
            "hardware_version": "Rev 1.0",
            "mac_address": f"AA:BB:CC:DD:EE:{random.randint(10,99):02X}",
            "location": self.config.location,
            "uptime_start": self.uptime_start.isoformat(),
            "current_sensors": len(self.config.sensors),
            "current_actuators": len(self.config.actuators),
            "timestamp": datetime.now().isoformat()
        }
        
        topic = f"devices/{self.config.device_id}/info"
        self.client.publish(topic, json.dumps(info))
    
    async def _publish_actuator_status(self, actuator_name: str):
        """Publish actuator status"""
        actuator_state = self.actuator_states[actuator_name]
        
        status = {
            "device_id": self.config.device_id,
            "actuator": actuator_name,
            "state": actuator_state["state"],
            "last_action": actuator_state["last_action"],
            "timestamp": datetime.now().isoformat()
        }
        
        topic = f"devices/{self.config.device_id}/actuators/{actuator_name}/status"
        self.client.publish(topic, json.dumps(status))
    
    def _generate_realistic_sensor_value(self, sensor_name: str) -> float:
        """Generate realistic sensor values with noise and drift"""
        sensor_data = self.sensor_values[sensor_name]
        config = sensor_data["config"]
        
        # Add some drift over time
        sensor_data["drift_offset"] += random.uniform(-config.drift_rate, config.drift_rate)
        
        # Base value with drift
        base_with_drift = config.base_value + sensor_data["drift_offset"]
        
        # Add noise
        noise = random.gauss(0, config.variation)
        
        # Add time-based variation (e.g., temperature cycles)
        time_factor = math.sin(time.time() / 3600) * config.variation * 0.5  # Hourly cycle
        
        new_value = base_with_drift + noise + time_factor
        
        # Clamp to realistic range
        new_value = max(config.min_value, min(config.max_value, new_value))
        
        # Add some sensor-specific behaviors
        if config.sensor_type == "temperature":
            # Temperature affected by actuators (e.g., heater)
            if "heater" in self.actuator_states and self.actuator_states["heater"]["state"] == "on":
                new_value += 2.0
        elif config.sensor_type == "humidity":
            # Humidity inversely related to temperature
            if "temperature" in self.sensor_values:
                temp = self.sensor_values["temperature"]["current_value"]
                humidity_offset = (25 - temp) * 0.5  # Rough inverse relationship
                new_value += humidity_offset
        
        sensor_data["current_value"] = new_value
        return new_value
    
    async def _sensor_update_loop(self):
        """Main loop for updating and publishing sensor data"""
        while self.running:
            try:
                current_time = time.time()
                
                for sensor_name, sensor_data in self.sensor_values.items():
                    config = sensor_data["config"]
                    
                    # Check if it's time to update this sensor
                    if current_time - self.last_sensor_update[sensor_name] >= config.update_interval:
                        value = self._generate_realistic_sensor_value(sensor_name)
                        
                        # Occasionally simulate sensor errors
                        if random.random() < 0.001:  # 0.1% chance of error
                            self.logger.warning(f"Simulated sensor error for {sensor_name}")
                            await self._publish_error("sensor_error", f"Sensor {sensor_name} read error", 1)
                            continue
                        
                        # Publish sensor data
                        sensor_reading = {
                            "device_id": self.config.device_id,
                            "sensor": sensor_name,
                            "type": config.sensor_type,
                            "value": round(value, 2),
                            "unit": config.unit,
                            "quality": random.uniform(95, 100),  # Simulate data quality
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        topic = f"devices/{self.config.device_id}/sensors/{sensor_name}"
                        self.client.publish(topic, json.dumps(sensor_reading))
                        
                        self.last_sensor_update[sensor_name] = current_time
                        self.message_count += 1
                
                # Periodically publish status
                if random.random() < 0.1:  # 10% chance each loop
                    await self._publish_device_status()
                
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                self.logger.error(f"Error in sensor update loop: {e}")
                self.error_count += 1
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _publish_error(self, error_type: str, message: str, severity: int = 1):
        """Publish device error"""
        error = {
            "device_id": self.config.device_id,
            "error_type": error_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }
        
        topic = f"devices/{self.config.device_id}/error"
        self.client.publish(topic, json.dumps(error))
        self.error_count += 1
    
    async def _connection_monitor(self):
        """Monitor and maintain MQTT connection"""
        while self.running:
            try:
                if not self.online:
                    self.logger.info("Attempting to reconnect...")
                    self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
                    self.client.loop_start()
                
                # Simulate occasional connection issues
                if random.random() < 0.0001:  # Very rare connection issues
                    self.logger.warning("Simulating connection issue")
                    self.client.disconnect()
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Connection error: {e}")
                await asyncio.sleep(30)  # Wait longer before retrying
    
    async def start(self):
        """Start the mock device"""
        self.running = True
        self.logger.info(f"Starting mock ESP32 device: {self.config.device_id}")
        
        # Connect to MQTT
        try:
            self.client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.client.loop_start()
        except Exception as e:
            self.logger.error(f"Failed to connect to MQTT broker: {e}")
            return
        
        # Start background tasks
        self.tasks = [
            asyncio.create_task(self._sensor_update_loop()),
            asyncio.create_task(self._connection_monitor())
        ]
        
        # Wait for all tasks
        try:
            await asyncio.gather(*self.tasks)
        except asyncio.CancelledError:
            self.logger.info("Tasks cancelled")
    
    async def stop(self):
        """Stop the mock device"""
        self.running = False
        self.logger.info(f"Stopping mock ESP32 device: {self.config.device_id}")
        
        # Publish offline status
        if self.online:
            await self._publish_device_status("offline")
        
        # Cancel tasks
        for task in self.tasks:
            task.cancel()
        
        # Disconnect MQTT
        self.client.loop_stop()
        self.client.disconnect()


class MockDeviceManager:
    """Manages multiple mock ESP32 devices"""
    
    def __init__(self, config_file: str = None):
        self.devices = []
        self.config_file = config_file
        self.running = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("MockDeviceManager")
    
    def load_config(self, config_file: str):
        """Load device configurations from YAML file"""
        try:
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            mqtt_config = config_data.get('mqtt', {})
            devices_config = config_data.get('devices', [])
            
            for device_data in devices_config:
                # Create sensor configs
                sensors = []
                for sensor_data in device_data.get('sensors', []):
                    sensors.append(SensorConfig(**sensor_data))
                
                # Create actuator configs
                actuators = []
                for actuator_data in device_data.get('actuators', []):
                    actuators.append(ActuatorConfig(**actuator_data))
                
                # Create device config
                device_config = DeviceConfig(
                    device_id=device_data['device_id'],
                    device_type=device_data.get('device_type', 'ESP32'),
                    firmware_version=device_data.get('firmware_version', '1.0.0'),
                    location=device_data.get('location', 'test_lab'),
                    sensors=sensors,
                    actuators=actuators
                )
                
                # Create mock device
                device = MockESP32Device(
                    config=device_config,
                    mqtt_broker=mqtt_config.get('broker', 'localhost'),
                    mqtt_port=mqtt_config.get('port', 1883),
                    mqtt_username=mqtt_config.get('username'),
                    mqtt_password=mqtt_config.get('password')
                )
                
                self.devices.append(device)
                self.logger.info(f"Loaded device config: {device_config.device_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to load config file: {e}")
            raise
    
    def create_default_devices(self, count: int = 3):
        """Create default mock devices for testing"""
        base_sensors = [
            SensorConfig("temperature", "temperature", "°C", 15.0, 35.0, 22.0, 1.5, 10.0),
            SensorConfig("humidity", "humidity", "%", 30.0, 80.0, 55.0, 5.0, 15.0),
            SensorConfig("pressure", "pressure", "hPa", 980.0, 1040.0, 1013.25, 2.0, 60.0)
        ]
        
        base_actuators = [
            ActuatorConfig("led", "led", "off", ["on", "off", "toggle"]),
            ActuatorConfig("relay", "relay", "off", ["on", "off", "toggle"])
        ]
        
        locations = ["kitchen", "living_room", "bedroom", "garage", "office"]
        
        for i in range(count):
            # Vary sensors and actuators per device
            device_sensors = base_sensors.copy()
            device_actuators = base_actuators.copy()
            
            if i == 1:  # Second device has light sensor
                device_sensors.append(
                    SensorConfig("light", "light", "lux", 0.0, 1000.0, 300.0, 50.0, 20.0)
                )
            
            if i == 2:  # Third device has heater
                device_actuators.append(
                    ActuatorConfig("heater", "heater", "off", ["on", "off", "toggle"])
                )
            
            device_config = DeviceConfig(
                device_id=f"esp32_{locations[i % len(locations)]}",
                device_type="ESP32",
                firmware_version=f"1.{i}.0",
                location=locations[i % len(locations)],
                sensors=device_sensors,
                actuators=device_actuators
            )
            
            device = MockESP32Device(device_config)
            self.devices.append(device)
    
    async def start_all(self):
        """Start all mock devices"""
        self.running = True
        self.logger.info(f"Starting {len(self.devices)} mock devices...")
        
        # Start all devices concurrently
        tasks = [device.start() for device in self.devices]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal")
        except Exception as e:
            self.logger.error(f"Error running devices: {e}")
        finally:
            await self.stop_all()
    
    async def stop_all(self):
        """Stop all mock devices"""
        self.running = False
        self.logger.info("Stopping all mock devices...")
        
        # Stop all devices
        tasks = [device.stop() for device in self.devices]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.logger.info("All devices stopped")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Mock ESP32 Device Simulator")
    parser.add_argument("--config", "-c", help="Configuration file (YAML)")
    parser.add_argument("--devices", "-d", type=int, default=3, 
                       help="Number of default devices to create")
    parser.add_argument("--broker", "-b", default="localhost",
                       help="MQTT broker address")
    parser.add_argument("--port", "-p", type=int, default=1883,
                       help="MQTT broker port")
    parser.add_argument("--username", "-u", help="MQTT username")
    parser.add_argument("--password", "-P", help="MQTT password")
    
    args = parser.parse_args()
    
    manager = MockDeviceManager()
    
    if args.config:
        manager.load_config(args.config)
    else:
        manager.create_default_devices(args.devices)
        
        # Update MQTT settings for default devices
        for device in manager.devices:
            device.mqtt_broker = args.broker
            device.mqtt_port = args.port
            device.mqtt_username = args.username
            device.mqtt_password = args.password
    
    # Start all devices
    await manager.start_all()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user") 