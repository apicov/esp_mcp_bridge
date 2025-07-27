"""
MQTT client management for the MCP-MQTT bridge.
"""

import json
import logging
from typing import Dict, Callable, Any, Optional, List
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class MQTTManager:
    """Manages MQTT client and message handling"""
    
    def __init__(self, broker: str, port: int = 1883, 
                 username: Optional[str] = None, 
                 password: Optional[str] = None,
                 client_id: str = "mcp_bridge_server"):
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        
        if username and password:
            self.client.username_pw_set(username, password)
        
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.on_log = self._on_log
        
        self.message_handlers: Dict[str, Callable] = {}
        self.connected = False
        self._connection_callbacks: List[Callable] = []
        self._disconnection_callbacks: List[Callable] = []
    
    def add_connection_callback(self, callback: Callable[[bool], None]):
        """Add callback for connection state changes"""
        self._connection_callbacks.append(callback)
    
    def add_disconnection_callback(self, callback: Callable[[], None]):
        """Add callback for disconnection events"""
        self._disconnection_callbacks.append(callback)
    
    async def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()
    
    def _on_log(self, client, userdata, level, buf):
        """MQTT client logging callback"""
        logger.debug(f"MQTT: {buf}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            self.connected = True
            
            # Subscribe to all device topics
            subscriptions = [
                ("devices/+/capabilities", 1),
                ("devices/+/sensors/+/data", 0),
                ("devices/+/actuators/+/status", 1),
                ("devices/+/status", 1),
                ("devices/+/error", 1)
            ]
            
            for topic, qos in subscriptions:
                client.subscribe(topic, qos)
                logger.info(f"Subscribed to {topic}")
            
            # Notify connection callbacks
            for callback in self._connection_callbacks:
                try:
                    callback(True)
                except Exception as e:
                    logger.error(f"Error in connection callback: {e}")
                    
        else:
            logger.error(f"Connection failed with code {rc}")
            for callback in self._connection_callbacks:
                try:
                    callback(False)
                except Exception as e:
                    logger.error(f"Error in connection callback: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.connected = False
        logger.warning(f"Disconnected from MQTT broker (code: {rc})")
        
        if rc != 0:
            logger.info("Unexpected disconnection, will auto-reconnect")
        
        # Notify disconnection callbacks
        for callback in self._disconnection_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in disconnection callback: {e}")
    
    def _on_message(self, client, userdata, msg):
        """MQTT message callback"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            logger.debug(f"Received message on {topic}: {payload}")
            
            # Route to appropriate handler based on topic pattern
            topic_parts = topic.split('/')
            
            if len(topic_parts) >= 3:
                device_id = topic_parts[1]
                message_type = topic_parts[2]
                
                # Create handler key for routing
                if message_type == "sensors" and len(topic_parts) >= 5:
                    handler_key = "devices/+/sensors/+/data"
                elif message_type == "actuators" and len(topic_parts) >= 5:
                    handler_key = "devices/+/actuators/+/status"
                elif message_type == "capabilities":
                    handler_key = "devices/+/capabilities"
                elif message_type == "status":
                    handler_key = "devices/+/status"
                elif message_type == "error":
                    handler_key = "devices/+/error"
                else:
                    handler_key = None
                
                if handler_key and handler_key in self.message_handlers:
                    try:
                        self.message_handlers[handler_key](topic, payload)
                    except Exception as e:
                        logger.error(f"Error in message handler for {handler_key}: {e}")
                else:
                    logger.debug(f"No handler for topic pattern: {topic}")
                    
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in message from {msg.topic}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def add_message_handler(self, pattern: str, handler: Callable):
        """Register a message handler for a topic pattern"""
        self.message_handlers[pattern] = handler
        logger.debug(f"Registered handler for pattern: {pattern}")
    
    async def publish(self, topic: str, payload: Dict[str, Any], qos: int = 0, retain: bool = False) -> bool:
        """Publish a message to MQTT"""
        if not self.connected:
            logger.warning("Cannot publish - not connected to broker")
            return False
        
        try:
            json_payload = json.dumps(payload)
            result = self.client.publish(topic, json_payload, qos, retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published to {topic}")
                return True
            else:
                logger.error(f"Failed to publish to {topic}: {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            return False
    
    def subscribe(self, topic: str, qos: int = 0) -> bool:
        """Subscribe to a topic"""
        if not self.connected:
            logger.warning("Cannot subscribe - not connected to broker")
            return False
        
        try:
            result = self.client.subscribe(topic, qos)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Subscribed to {topic}")
                return True
            else:
                logger.error(f"Failed to subscribe to {topic}: {result[0]}")
                return False
        except Exception as e:
            logger.error(f"Error subscribing to topic: {e}")
            return False
    
    def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from a topic"""
        if not self.connected:
            return False
        
        try:
            result = self.client.unsubscribe(topic)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Unsubscribed from {topic}")
                return True
            else:
                logger.error(f"Failed to unsubscribe from {topic}: {result[0]}")
                return False
        except Exception as e:
            logger.error(f"Error unsubscribing from topic: {e}")
            return False 