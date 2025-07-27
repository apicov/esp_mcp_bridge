#!/usr/bin/env python3
"""
Quick test to verify the chat demo setup is ready
"""

import os
import sys
from pathlib import Path

def check_chat_setup():
    """Check if the chat demo setup is ready."""
    print("🔍 Checking Chat Demo Setup...")
    print("="*40)
    
    issues = []
    
    # Check required files
    required_files = [
        "chat_with_devices.py",
        "start_chat_demo.py", 
        "requirements-chat.txt",
        "CHAT_DEMO_README.md"
    ]
    
    for file in required_files:
        if Path(file).exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            issues.append(f"Missing file: {file}")
    
    # Check if we're in virtual environment
    if sys.prefix != sys.base_prefix:
        print("✅ Virtual environment detected")
    else:
        print("⚠️  Virtual environment not detected")
        issues.append("Recommend activating virtual environment")
    
    # Check if OpenAI API key is set
    if os.getenv("OPENAI_API_KEY"):
        print("✅ OpenAI API key found")
    else:
        print("⚠️  OpenAI API key not set")
        issues.append("Need to set OPENAI_API_KEY environment variable")
    
    # Check for core components
    core_files = [
        "mcp_mqtt_bridge/__init__.py",
        "examples/mock_esp32_device.py"
    ]
    
    for file in core_files:
        if Path(file).exists():
            print(f"✅ {file}")
        else:
            print(f"❌ {file}")
            issues.append(f"Missing core file: {file}")
    
    print("\n" + "="*40)
    
    if not issues:
        print("🎉 CHAT DEMO READY!")
        print("\nTo start:")
        print("1. Set OpenAI API key: export OPENAI_API_KEY='your-key'")
        print("2. Install requirements: pip install -r requirements-chat.txt")  
        print("3. Run demo: python start_chat_demo.py")
        return True
    else:
        print("⚠️  Issues found:")
        for issue in issues:
            print(f"   • {issue}")
        return False

if __name__ == "__main__":
    success = check_chat_setup()
    sys.exit(0 if success else 1) 