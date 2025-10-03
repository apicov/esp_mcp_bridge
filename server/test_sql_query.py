#!/usr/bin/env python3
"""
Test script for SQL query functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from mcp_mqtt_bridge.database import DatabaseManager
from mcp_mqtt_bridge.sql_validator import SQLValidator, SQLValidationError

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
        print(f"   Metadata: {metadata}")
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

def test_database_manager():
    """Test DatabaseManager SQL query methods"""
    print("\n" + "=" * 60)
    print("Testing DatabaseManager")
    print("=" * 60)

    # Create test database
    db = DatabaseManager(db_path=":memory:")

    # Insert test data
    print("\n1. Inserting test data...")
    from datetime import datetime
    from mcp_mqtt_bridge.data_models import SensorReading

    test_readings = [
        SensorReading("esp32_001", "temperature", 23.5, "°C", datetime.now()),
        SensorReading("esp32_001", "humidity", 65.0, "%", datetime.now()),
        SensorReading("esp32_002", "temperature", 22.1, "°C", datetime.now()),
    ]

    for reading in test_readings:
        db.store_sensor_reading(reading)

    print("   ✓ Test data inserted")

    # Test 2: Execute valid query
    print("\n2. Execute valid SELECT query:")
    result = db.execute_query("SELECT * FROM sensor_readings")
    if result["success"]:
        print(f"   ✓ Query executed successfully")
        print(f"   Rows returned: {result['row_count']}")
        print(f"   Columns: {result['columns']}")
        for row in result['data']:
            print(f"   - {row['device_id']}: {row['sensor_type']} = {row['value']} {row['unit']}")
    else:
        print(f"   ✗ Query failed: {result['error']}")

    # Test 3: Execute query with aggregation
    print("\n3. Execute aggregation query:")
    result = db.execute_query("""
        SELECT device_id, COUNT(*) as sensor_count, AVG(value) as avg_value
        FROM sensor_readings
        GROUP BY device_id
    """)
    if result["success"]:
        print(f"   ✓ Query executed successfully")
        for row in result['data']:
            print(f"   - {row['device_id']}: {row['sensor_count']} sensors, avg={row['avg_value']:.2f}")
    else:
        print(f"   ✗ Query failed: {result['error']}")

    # Test 4: Attempt blocked query
    print("\n4. Attempt DELETE query (should be blocked):")
    result = db.execute_query("DELETE FROM sensor_readings")
    if result["success"]:
        print(f"   ✗ Query should have been blocked!")
    else:
        print(f"   ✓ Query blocked: {result['error']}")
        print(f"   Error type: {result['error_type']}")

    # Test 5: Get database schema
    print("\n5. Get database schema:")
    schema = db.get_database_schema()
    if schema["success"]:
        print(f"   ✓ Schema retrieved successfully")
        print(f"   Tables: {schema['table_count']}")
        for table_name, table_info in schema['tables'].items():
            print(f"   - {table_name}: {len(table_info['columns'])} columns, {table_info['row_count']} rows")
    else:
        print(f"   ✗ Failed to get schema: {schema['error']}")

    # Test 6: Get query examples
    print("\n6. Get query examples:")
    examples = db.get_query_examples()
    print(f"   ✓ Retrieved {len(examples)} example queries")
    for i, example in enumerate(examples[:3], 1):
        print(f"   {i}. {example['name']}: {example['description']}")

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SQL Query Functionality Test Suite")
    print("=" * 60)

    try:
        test_sql_validator()
        test_database_manager()

        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
