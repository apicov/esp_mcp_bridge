#!/usr/bin/env python3
"""
Development setup script for MCP-MQTT Bridge.
Initializes development environment, databases, and configurations.
"""
import os
import sys
import subprocess
import sqlite3
import yaml
from pathlib import Path


def run_command(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    return result


def check_python_version():
    """Ensure Python version is 3.11 or later."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print("Error: Python 3.11 or later is required")
        sys.exit(1)
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")


def setup_virtual_environment():
    """Create and activate virtual environment if not already active."""
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✓ Virtual environment already active")
        return
    
    if not Path("venv").exists():
        print("Creating virtual environment...")
        run_command(f"{sys.executable} -m venv venv")
    
    print("Virtual environment created. Please activate it with:")
    print("  source venv/bin/activate  # On Linux/Mac")
    print("  venv\\Scripts\\activate     # On Windows")


def install_dependencies():
    """Install project dependencies."""
    print("Installing dependencies...")
    
    # Try poetry first
    poetry_check = run_command("poetry --version", check=False)
    if poetry_check.returncode == 0:
        print("Using Poetry for dependency management")
        run_command("poetry install --with dev")
    else:
        print("Poetry not found, using pip")
        run_command("pip install -r requirements.txt")
        if Path("requirements-dev.txt").exists():
            run_command("pip install -r requirements-dev.txt")
        run_command("pip install -e .")


def setup_database():
    """Initialize development database."""
    db_path = Path("data/bridge.db")
    db_path.parent.mkdir(exist_ok=True)
    
    if db_path.exists():
        print("✓ Database already exists")
        return
    
    print("Setting up development database...")
    
    # Import here to avoid import errors during setup
    try:
        from mcp_mqtt_bridge.database import DatabaseManager
        db_manager = DatabaseManager(str(db_path))
    
        db_manager.close()
        print(f"✓ Database created at {db_path}")
    except ImportError:
        print("Warning: Could not import DatabaseManager, skipping database setup")


def create_config_files():
    """Create development configuration files."""
    config_dir = Path("config")
    
    # Development config
    dev_config_path = config_dir / "development.yaml"
    if not dev_config_path.exists():
        dev_config = {
            "mqtt": {
                "broker": "localhost",
                "port": 1883,
                "client_id": "mcp_bridge_dev"
            },
            "database": {
                "path": "./data/bridge.db",
                "retention_days": 7,
                "cleanup_interval_hours": 1
            },
            "monitoring": {
                "device_timeout_minutes": 2,
                "metrics_interval_seconds": 30,
                "log_level": "DEBUG",
                "max_errors_per_device": 50
            },
            "security": {
                "enable_tls": False
            }
        }
        
        with open(dev_config_path, 'w') as f:
            yaml.dump(dev_config, f, default_flow_style=False)
        print(f"✓ Created {dev_config_path}")
    
    # Production example
    prod_example_path = config_dir / "production.yaml.example"
    if not prod_example_path.exists():
        prod_config = {
            "mqtt": {
                "broker": "${MQTT_BROKER}",
                "port": "${MQTT_PORT:1883}",
                "username": "${MQTT_USERNAME}",
                "password": "${MQTT_PASSWORD}",
                "client_id": "mcp_bridge_prod"
            },
            "database": {
                "path": "${DB_PATH:./data/bridge.db}",
                "retention_days": 30,
                "cleanup_interval_hours": 24
            },
            "monitoring": {
                "device_timeout_minutes": 5,
                "metrics_interval_seconds": 60,
                "log_level": "${LOG_LEVEL:INFO}",
                "max_errors_per_device": 100
            },
            "security": {
                "enable_tls": True,
                "ca_cert_path": "./certs/ca.crt",
                "cert_path": "./certs/client.crt",
                "key_path": "./certs/client.key"
            }
        }
        
        with open(prod_example_path, 'w') as f:
            yaml.dump(prod_config, f, default_flow_style=False)
        print(f"✓ Created {prod_example_path}")


def setup_pre_commit_hooks():
    """Set up pre-commit hooks for code quality."""
    if Path(".pre-commit-config.yaml").exists():
        try:
            run_command("pre-commit install")
            print("✓ Pre-commit hooks installed")
        except subprocess.CalledProcessError:
            print("Warning: Could not install pre-commit hooks")


def create_directories():
    """Create necessary directories."""
    dirs = ["data", "logs", "certs"]
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"✓ Created directory: {dir_name}")


def main():
    """Main setup function."""
    print("🚀 Setting up MCP-MQTT Bridge development environment")
    print("=" * 60)
    
    check_python_version()
    setup_virtual_environment()
    create_directories()
    install_dependencies()
    setup_database()
    create_config_files()
    setup_pre_commit_hooks()
    
    print("\n✅ Development setup complete!")
    print("\nNext steps:")
    print("1. Activate your virtual environment (if not already active)")
    print("2. Start an MQTT broker: docker run -p 1883:1883 eclipse-mosquitto")
    print("3. Run the bridge: python -m mcp_mqtt_bridge --config config/development.yaml")
    print("4. Run tests: pytest")


if __name__ == "__main__":
    main() 