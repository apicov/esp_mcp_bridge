"""
Test configuration and fixtures for MCP-MQTT Bridge tests.
"""
import pytest
import asyncio
import sqlite3
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from mcp_mqtt_bridge.bridge import MCPMQTTBridge
from mcp_mqtt_bridge.database import DatabaseManager
from mcp_mqtt_bridge.device_manager import DeviceManager
from mcp_mqtt_bridge.mqtt_manager import MQTTManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db_path():
    """Create a temporary database file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp_file:
        db_path = tmp_file.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def database_manager(temp_db_path):
    """Create a DatabaseManager instance with temporary database."""
    db_manager = DatabaseManager(db_path=temp_db_path)

    yield db_manager
    db_manager.close()


@pytest.fixture
def mock_mqtt_manager():
    """Create a mock MQTT manager for testing."""
    mock_mqtt = AsyncMock(spec=MQTTManager)
    mock_mqtt.is_connected = True
    mock_mqtt.publish = AsyncMock(return_value=True)
    mock_mqtt.subscribe = AsyncMock()
    mock_mqtt.connect = AsyncMock()
    mock_mqtt.disconnect = AsyncMock()
    return mock_mqtt


@pytest.fixture
def device_manager(database_manager):
    """Create a DeviceManager instance for testing."""
    return DeviceManager(database_manager)


@pytest.fixture
def sample_device_data():
    """Sample device data for testing."""
    return {
        "device_id": "test_esp32_001",
        "device_type": "ESP32",
        "sensors": ["temperature", "humidity", "pressure"],
        "actuators": ["led", "relay"],
        "firmware_version": "1.0.0",
        "location": "test_lab",
        "status": "online"
    }


@pytest.fixture
def sample_sensor_data():
    """Sample sensor reading data for testing."""
    return {
        "device_id": "test_esp32_001",
        "sensor_type": "temperature",
        "value": 23.5,
        "unit": "°C",
        "timestamp": "2024-01-01T12:00:00Z"
    }


@pytest.fixture
async def bridge_instance(temp_db_path, mock_mqtt_manager):
    """Create a bridge instance for integration testing."""
    bridge = MCPMQTTBridge(
        mqtt_broker="test_broker",
        mqtt_port=1883,
        db_path=temp_db_path,
        device_timeout_minutes=1
    )
    # Replace MQTT manager with mock
    bridge.mqtt = mock_mqtt_manager
    
    await bridge._initialize_components()
    yield bridge
    await bridge.stop()


@pytest.fixture
def mqtt_test_config():
    """Configuration for MQTT integration tests."""
    return {
        "broker": os.getenv("MQTT_TEST_BROKER", "localhost"),
        "port": int(os.getenv("MQTT_TEST_PORT", "1883")),
        "username": os.getenv("MQTT_TEST_USERNAME"),
        "password": os.getenv("MQTT_TEST_PASSWORD"),
        "client_id": "test_mcp_bridge"
    }


# Test markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on file location."""
    for item in items:
        # Mark tests in unit/ directory as unit tests
        if "unit/" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        # Mark tests in integration/ directory as integration tests
        elif "integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration) 