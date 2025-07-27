# Multi-stage build for Python MCP-MQTT Bridge Server

FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser

# Set work directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/mcpuser/.local

# Copy application code
COPY mcp_mqtt_bridge/ ./mcp_mqtt_bridge/
COPY examples/ ./examples/

# Create data directory and set permissions
RUN mkdir -p /data && chown -R mcpuser:mcpuser /data /app

# Switch to non-root user
USER mcpuser

# Update PATH
ENV PATH=/home/mcpuser/.local/bin:$PATH

# Environment variables
ENV PYTHONPATH=/app
ENV MQTT_BROKER=localhost
ENV MQTT_PORT=1883
ENV DB_PATH=/data/bridge.db
ENV LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sqlite3; sqlite3.connect('${DB_PATH}').close()" || exit 1

# Expose port (if needed for web interface in future)
EXPOSE 8000

# Run the application
CMD ["python", "-m", "mcp_mqtt_bridge"] 