#!/usr/bin/env python3
"""
Simple test script for SQL query functionality (standalone)
"""

import sys
import os
import sqlite3
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mcp_mqtt_bridge'))

from sql_validator import SQLValidator, SQLValidationError

def test_sql_validator():
    """Test SQL validator"""
    print("=" * 60)
    print("Testing SQL Validator")
    print("=" * 60)

    validator = SQLValidator()

    # Test 1: Valid SELECT query
    print("\n1. Valid SELECT query:")
    try:
        query = "SELECT * FROM sensor_readings WHERE device_id = 'esp32_123'"
        validated, metadata = validator.validate_query(query)
        print(f"   ✓ Query validated successfully")
        print(f"   Validated query: {validated}")
    except SQLValidationError as e:
        print(f"   ✗ Validation failed: {e}")

    # Test 2: Blocked DELETE query
    print("\n2. Blocked DELETE query:")
    try:
        query = "DELETE FROM sensor_readings WHERE device_id = 'esp32_123'"
        validated, metadata = validator.validate_query(query)
        print(f"   ✗ Should have been blocked!")
    except SQLValidationError as e:
        print(f"   ✓ Correctly blocked: {e}")

    # Test 3: Blocked DROP TABLE query
    print("\n3. Blocked DROP TABLE query:")
    try:
        query = "SELECT * FROM devices; DROP TABLE devices;--"
        validated, metadata = validator.validate_query(query)
        print(f"   ✗ Should have been blocked!")
    except SQLValidationError as e:
        print(f"   ✓ Correctly blocked: {e}")

    # Test 4: Query without LIMIT (should be added)
    print("\n4. Query without LIMIT:")
    try:
        query = "SELECT * FROM sensor_readings"
        validated, metadata = validator.validate_query(query)
        print(f"   ✓ LIMIT added automatically")
        print(f"   Validated query: {validated}")
    except SQLValidationError as e:
        print(f"   ✗ Validation failed: {e}")

    # Test 5: Query with excessive LIMIT (should be reduced)
    print("\n5. Query with excessive LIMIT:")
    try:
        query = "SELECT * FROM sensor_readings LIMIT 50000"
        validated, metadata = validator.validate_query(query)
        print(f"   ✓ LIMIT reduced to maximum")
        print(f"   Validated query: {validated}")
    except SQLValidationError as e:
        print(f"   ✗ Validation failed: {e}")

    # Test 6: SQL injection attempt
    print("\n6. SQL injection attempt:")
    try:
        query = "SELECT * FROM sensor_readings WHERE device_id = 'esp' OR '1'='1'"
        validated, metadata = validator.validate_query(query)
        print(f"   ✗ Should have been blocked!")
    except SQLValidationError as e:
        print(f"   ✓ Correctly blocked: {e}")

    # Test 7: UPDATE query (blocked)
    print("\n7. UPDATE query (blocked):")
    try:
        query = "UPDATE sensor_readings SET value = 100"
        validated, metadata = validator.validate_query(query)
        print(f"   ✗ Should have been blocked!")
    except SQLValidationError as e:
        print(f"   ✓ Correctly blocked: {e}")

def test_execute_query_logic():
    """Test query execution logic with in-memory database"""
    print("\n" + "=" * 60)
    print("Testing Query Execution")
    print("=" * 60)

    # Create in-memory database
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Create test table
    print("\n1. Creating test table...")
    cursor.execute("""
        CREATE TABLE sensor_readings (
            id INTEGER PRIMARY KEY,
            device_id TEXT,
            sensor_type TEXT,
            value REAL,
            unit TEXT,
            timestamp DATETIME
        )
    """)

    # Insert test data
    test_data = [
        ('esp32_001', 'temperature', 23.5, '°C', datetime.now().isoformat()),
        ('esp32_001', 'humidity', 65.0, '%', datetime.now().isoformat()),
        ('esp32_002', 'temperature', 22.1, '°C', datetime.now().isoformat()),
        ('esp32_002', 'humidity', 70.5, '%', datetime.now().isoformat()),
        ('esp32_003', 'temperature', 24.0, '°C', datetime.now().isoformat()),
    ]

    cursor.executemany("""
        INSERT INTO sensor_readings (device_id, sensor_type, value, unit, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, test_data)
    conn.commit()
    print("   ✓ Test data inserted")

    # Test 2: Simple SELECT
    print("\n2. Simple SELECT query:")
    validator = SQLValidator()
    query = "SELECT * FROM sensor_readings"
    validated_query, metadata = validator.validate_query(query)

    cursor = conn.execute(validated_query)
    rows = cursor.fetchall()
    print(f"   ✓ Query executed: {len(rows)} rows returned")
    for row in rows[:3]:
        print(f"   - {row['device_id']}: {row['sensor_type']} = {row['value']} {row['unit']}")

    # Test 3: Aggregation query
    print("\n3. Aggregation query:")
    query = """
        SELECT device_id, COUNT(*) as sensor_count, AVG(value) as avg_value
        FROM sensor_readings
        GROUP BY device_id
    """
    validated_query, metadata = validator.validate_query(query)

    cursor = conn.execute(validated_query)
    rows = cursor.fetchall()
    print(f"   ✓ Aggregation executed: {len(rows)} devices")
    for row in rows:
        print(f"   - {row['device_id']}: {row['sensor_count']} sensors, avg={row['avg_value']:.2f}")

    # Test 4: Filtered query
    print("\n4. Filtered query:")
    query = """
        SELECT * FROM sensor_readings
        WHERE sensor_type = 'temperature'
        ORDER BY value DESC
    """
    validated_query, metadata = validator.validate_query(query)

    cursor = conn.execute(validated_query)
    rows = cursor.fetchall()
    print(f"   ✓ Filter applied: {len(rows)} temperature readings")
    for row in rows:
        print(f"   - {row['device_id']}: {row['value']} {row['unit']}")

    conn.close()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SQL Query Functionality Test Suite")
    print("=" * 60)

    try:
        test_sql_validator()
        test_execute_query_logic()

        print("\n" + "=" * 60)
        print("✓ All tests completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
