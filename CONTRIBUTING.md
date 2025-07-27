# Contributing to ESP32 MCP-MQTT Bridge

Thank you for considering contributing to the ESP32 MCP-MQTT Bridge project! This document provides guidelines and information for contributors.

## 📋 **Table of Contents**

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Style Guidelines](#style-guidelines)

## 🤝 **Code of Conduct**

This project follows a code of conduct to ensure a welcoming environment for all contributors. Please be respectful, inclusive, and constructive in all interactions.

## 🚀 **Getting Started**

### **Prerequisites**
- **ESP32 Development**: ESP-IDF v5.1+, Python 3.8+
- **Server Development**: Python 3.11+, Poetry (recommended)
- **Tools**: Git, Docker (optional)

### **Fork and Clone**
```bash
# Fork the repository on GitHub
git clone https://github.com/YOUR_USERNAME/esp32-mcp-bridge.git
cd esp32-mcp-bridge
```

## 💻 **Development Setup**

### **ESP32 Firmware**
```bash
# Setup ESP-IDF environment
cd firmware
source $IDF_PATH/export.sh

# Build and test
cd examples/basic_example
idf.py build
```

### **Python Server**
```bash
# Setup Python environment
cd server
poetry install --with dev
poetry shell

# Run tests
pytest
```

## 🔧 **Making Changes**

### **Branch Naming**
- `feature/your-feature-name` - New features
- `bugfix/issue-description` - Bug fixes  
- `docs/documentation-update` - Documentation changes
- `refactor/component-name` - Code refactoring

### **Commit Messages**
Follow conventional commit format:
```
type(scope): description

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples**:
```
feat(esp32): add TLS support for MQTT connections
fix(server): resolve device timeout detection issue
docs(readme): update installation instructions
```

## 🧪 **Testing**

### **ESP32 Tests**
```bash
cd firmware/tests/unit_tests
idf.py build flash monitor
```

### **Python Tests**
```bash
cd server
pytest tests/
pytest --cov=mcp_mqtt_bridge --cov-report=html
```

### **Integration Tests**
```bash
# Start test MQTT broker
docker run -d -p 1883:1883 eclipse-mosquitto

# Run integration tests
pytest tests/integration/
```

## 📝 **Submitting Changes**

### **Pull Request Process**

1. **Update Documentation**: Ensure README, API docs, and comments are updated
2. **Add Tests**: Include tests for new functionality
3. **Check Style**: Run linters and formatters
4. **Test Thoroughly**: All tests must pass
5. **Small PRs**: Keep changes focused and reviewable

### **PR Template**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature  
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## 🎨 **Style Guidelines**

### **C/C++ (ESP32)**
- Follow ESP-IDF coding style
- Use `snake_case` for functions and variables
- Use `UPPER_CASE` for constants and macros
- Maximum line length: 120 characters
- Always include error handling

```c
// Good
esp_err_t mcp_bridge_init(const mcp_bridge_config_t *config) {
    if (!config) {
        return ESP_ERR_INVALID_ARG;
    }
    // Implementation...
    return ESP_OK;
}
```

### **Python**
- Follow PEP 8
- Use type hints for all functions
- Maximum line length: 100 characters
- Use docstrings for all public functions

```python
def get_device_status(device_id: str) -> Optional[DeviceStatus]:
    """Get the current status of a device.
    
    Args:
        device_id: Unique identifier for the device
        
    Returns:
        Device status if found, None otherwise
    """
    return self.devices.get(device_id)
```

### **Documentation**
- Use clear, concise language
- Include code examples for complex features
- Update API documentation for any changes
- Use Markdown formatting consistently

## 🐛 **Reporting Issues**

### **Bug Reports**
Include:
- ESP-IDF version (for firmware issues)
- Python version (for server issues)
- Hardware details (ESP32 variant, sensors)
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs/error messages

### **Feature Requests**
Include:
- Use case description
- Proposed solution
- Alternative solutions considered
- Impact on existing functionality

## 🏷️ **Release Process**

### **Versioning**
We use [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH`
- Breaking changes increment MAJOR
- New features increment MINOR  
- Bug fixes increment PATCH

### **Release Checklist**
- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version numbers bumped
- [ ] Release notes prepared

## 📞 **Getting Help**

- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Use GitHub Issues for bugs and features
- **Email**: [maintainer@example.com](mailto:maintainer@example.com)
- **Discord**: [Community Discord](https://discord.gg/example)

## 🎯 **Areas for Contribution**

### **High Priority**
- Performance optimizations
- Additional sensor/actuator examples
- Enhanced security features
- Mobile app development

### **Good First Issues**
- Documentation improvements
- Example projects
- Unit test coverage
- Bug fixes in issues labeled `good-first-issue`

### **Advanced Features**
- Multi-protocol support (CoAP, LoRaWAN)
- Cloud integration (AWS IoT, Azure IoT)
- Machine learning integration
- Kubernetes operator

---

Thank you for contributing! 🎉 