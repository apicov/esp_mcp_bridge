#!/usr/bin/env python3
"""
Health check script for MCP-MQTT Bridge.
Monitors system status, connectivity, and performance metrics.
"""
import asyncio
import sys
import time
import json
import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add the parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import paho.mqtt.client as mqtt
    from mcp_mqtt_bridge.database import DatabaseManager
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure all dependencies are installed")
    sys.exit(1)


class HealthChecker:
    """Health checker for MCP-MQTT Bridge components."""
    
    def __init__(self, mqtt_broker: str = "localhost", mqtt_port: int = 1883,
                 mqtt_username: Optional[str] = None, mqtt_password: Optional[str] = None,
                 db_path: str = "./data/bridge.db"):
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.db_path = db_path
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and health."""
        result = {
            "component": "database",
            "status": "unknown",
            "details": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if not Path(self.db_path).exists():
                result["status"] = "error"
                result["details"]["error"] = f"Database file not found: {self.db_path}"
                return result
            
            # Test database connection
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.cursor()
                
                # Check if tables exist
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name IN ('devices', 'sensor_data', 'device_errors')
                """)
                tables = [row[0] for row in cursor.fetchall()]
                
                if len(tables) < 3:
                    result["status"] = "warning"
                    result["details"]["warning"] = f"Missing tables: {set(['devices', 'sensor_data', 'device_errors']) - set(tables)}"
                else:
                    result["status"] = "healthy"
                
                # Get basic statistics
                cursor.execute("SELECT COUNT(*) FROM devices")
                result["details"]["total_devices"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM devices WHERE status = 'online'")
                result["details"]["online_devices"] = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM sensor_data 
                    WHERE timestamp > datetime('now', '-1 hour')
                """)
                result["details"]["recent_sensor_readings"] = cursor.fetchone()[0]
                
                # Check database size
                cursor.execute("SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()")
                db_size = cursor.fetchone()[0]
                result["details"]["database_size_mb"] = round(db_size / 1024 / 1024, 2)
                
        except sqlite3.Error as e:
            result["status"] = "error"
            result["details"]["error"] = str(e)
        except Exception as e:
            result["status"] = "error"
            result["details"]["error"] = f"Unexpected error: {e}"
        
        return result
    
    def check_mqtt_health(self) -> Dict[str, Any]:
        """Check MQTT broker connectivity."""
        result = {
            "component": "mqtt",
            "status": "unknown",
            "details": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # Create MQTT client
            client = mqtt.Client(client_id="health_check_client")
            
            if self.mqtt_username and self.mqtt_password:
                client.username_pw_set(self.mqtt_username, self.mqtt_password)
            
            # Connection tracking
            connection_result = {"connected": False, "error": None}
            
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    connection_result["connected"] = True
                else:
                    connection_result["error"] = f"Connection failed with code {rc}"
            
            def on_disconnect(client, userdata, rc):
                connection_result["connected"] = False
            
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            
            # Attempt connection with timeout
            client.connect(self.mqtt_broker, self.mqtt_port, 60)
            client.loop_start()
            
            # Wait for connection
            timeout = 10
            start_time = time.time()
            while time.time() - start_time < timeout:
                if connection_result["connected"] or connection_result["error"]:
                    break
                time.sleep(0.1)
            
            client.loop_stop()
            client.disconnect()
            
            if connection_result["connected"]:
                result["status"] = "healthy"
                result["details"]["broker"] = f"{self.mqtt_broker}:{self.mqtt_port}"
                result["details"]["connection_time_ms"] = round((time.time() - start_time) * 1000, 2)
            else:
                result["status"] = "error"
                result["details"]["error"] = connection_result["error"] or "Connection timeout"
                
        except Exception as e:
            result["status"] = "error"
            result["details"]["error"] = str(e)
        
        return result
    
    def check_device_activity(self) -> Dict[str, Any]:
        """Check recent device activity and identify stale devices."""
        result = {
            "component": "device_activity",
            "status": "unknown",
            "details": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if not Path(self.db_path).exists():
                result["status"] = "error"
                result["details"]["error"] = "Database not found"
                return result
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check for devices that haven't sent data recently
                cursor.execute("""
                    SELECT d.device_id, d.last_seen, d.status,
                           CASE 
                               WHEN d.last_seen IS NULL THEN 999999
                               ELSE (julianday('now') - julianday(d.last_seen)) * 24 * 60
                           END as minutes_since_last_seen
                    FROM devices d
                    ORDER BY minutes_since_last_seen DESC
                """)
                
                devices = cursor.fetchall()
                stale_devices = []
                active_devices = []
                
                for device_id, last_seen, status, minutes_ago in devices:
                    device_info = {
                        "device_id": device_id,
                        "last_seen": last_seen,
                        "status": status,
                        "minutes_since_last_seen": round(minutes_ago, 1) if minutes_ago < 999999 else None
                    }
                    
                    if minutes_ago > 60:  # More than 1 hour
                        stale_devices.append(device_info)
                    else:
                        active_devices.append(device_info)
                
                result["details"]["total_devices"] = len(devices)
                result["details"]["active_devices"] = len(active_devices)
                result["details"]["stale_devices"] = len(stale_devices)
                result["details"]["stale_device_list"] = stale_devices[:10]  # Limit to 10
                
                # Determine overall status
                if len(devices) == 0:
                    result["status"] = "warning"
                    result["details"]["message"] = "No devices registered"
                elif len(stale_devices) > len(active_devices):
                    result["status"] = "warning"
                    result["details"]["message"] = "More stale devices than active"
                else:
                    result["status"] = "healthy"
                
        except Exception as e:
            result["status"] = "error"
            result["details"]["error"] = str(e)
        
        return result
    
    def check_error_rates(self) -> Dict[str, Any]:
        """Check device error rates."""
        result = {
            "component": "error_rates",
            "status": "unknown",
            "details": {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            if not Path(self.db_path).exists():
                result["status"] = "error"
                result["details"]["error"] = "Database not found"
                return result
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check recent errors (last 24 hours)
                cursor.execute("""
                    SELECT COUNT(*) FROM device_errors 
                    WHERE timestamp > datetime('now', '-24 hours')
                """)
                recent_errors = cursor.fetchone()[0]
                
                # Check error rates by device
                cursor.execute("""
                    SELECT device_id, COUNT(*) as error_count
                    FROM device_errors 
                    WHERE timestamp > datetime('now', '-24 hours')
                    GROUP BY device_id
                    ORDER BY error_count DESC
                    LIMIT 5
                """)
                top_error_devices = cursor.fetchall()
                
                # Check total error count
                cursor.execute("SELECT COUNT(*) FROM device_errors")
                total_errors = cursor.fetchone()[0]
                
                result["details"]["recent_errors_24h"] = recent_errors
                result["details"]["total_errors"] = total_errors
                result["details"]["top_error_devices"] = [
                    {"device_id": device_id, "error_count": count}
                    for device_id, count in top_error_devices
                ]
                
                # Determine status
                if recent_errors == 0:
                    result["status"] = "healthy"
                elif recent_errors < 10:
                    result["status"] = "warning"
                    result["details"]["message"] = f"{recent_errors} errors in last 24 hours"
                else:
                    result["status"] = "error"
                    result["details"]["message"] = f"High error rate: {recent_errors} errors in last 24 hours"
                
        except Exception as e:
            result["status"] = "error"
            result["details"]["error"] = str(e)
        
        return result
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks and return comprehensive status."""
        self.logger.info("Starting comprehensive health check")
        
        checks = {
            "database": self.check_database_health(),
            "mqtt": self.check_mqtt_health(),
            "device_activity": self.check_device_activity(),
            "error_rates": self.check_error_rates()
        }
        
        # Determine overall system status
        statuses = [check["status"] for check in checks.values()]
        
        if "error" in statuses:
            overall_status = "error"
        elif "warning" in statuses:
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "overall_status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
            "summary": {
                "healthy": statuses.count("healthy"),
                "warning": statuses.count("warning"),
                "error": statuses.count("error"),
                "unknown": statuses.count("unknown")
            }
        }
    
    def format_output(self, results: Dict[str, Any], format_type: str = "text") -> str:
        """Format health check results for output."""
        if format_type == "json":
            return json.dumps(results, indent=2)
        
        # Text format
        output = []
        output.append("🏥 MCP-MQTT Bridge Health Check")
        output.append("=" * 50)
        output.append(f"Timestamp: {results['timestamp']}")
        output.append(f"Overall Status: {results['overall_status'].upper()}")
        output.append("")
        
        status_icons = {
            "healthy": "✅",
            "warning": "⚠️",
            "error": "❌",
            "unknown": "❓"
        }
        
        for component, check in results["checks"].items():
            icon = status_icons.get(check["status"], "❓")
            output.append(f"{icon} {component.replace('_', ' ').title()}: {check['status'].upper()}")
            
            if "error" in check["details"]:
                output.append(f"   Error: {check['details']['error']}")
            elif "warning" in check["details"]:
                output.append(f"   Warning: {check['details']['warning']}")
            elif "message" in check["details"]:
                output.append(f"   Info: {check['details']['message']}")
            
            # Add relevant details
            for key, value in check["details"].items():
                if key not in ["error", "warning", "message"] and not key.endswith("_list"):
                    output.append(f"   {key.replace('_', ' ').title()}: {value}")
            
            output.append("")
        
        return "\n".join(output)


def main():
    """Main function for command line usage."""
    parser = argparse.ArgumentParser(description="MCP-MQTT Bridge Health Check")
    parser.add_argument("--mqtt-broker", default="localhost", 
                       help="MQTT broker hostname")
    parser.add_argument("--mqtt-port", type=int, default=1883, 
                       help="MQTT broker port")
    parser.add_argument("--mqtt-username", 
                       help="MQTT username")
    parser.add_argument("--mqtt-password", 
                       help="MQTT password")
    parser.add_argument("--db-path", default="./data/bridge.db", 
                       help="Path to database file")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                       help="Output format")
    parser.add_argument("--component", 
                       choices=["database", "mqtt", "device_activity", "error_rates"],
                       help="Check specific component only")
    
    args = parser.parse_args()
    
    checker = HealthChecker(
        mqtt_broker=args.mqtt_broker,
        mqtt_port=args.mqtt_port,
        mqtt_username=args.mqtt_username,
        mqtt_password=args.mqtt_password,
        db_path=args.db_path
    )
    
    if args.component:
        # Run specific check
        check_methods = {
            "database": checker.check_database_health,
            "mqtt": checker.check_mqtt_health,
            "device_activity": checker.check_device_activity,
            "error_rates": checker.check_error_rates
        }
        result = check_methods[args.component]()
        print(json.dumps(result, indent=2) if args.format == "json" else 
              f"{result['component']}: {result['status']}")
    else:
        # Run all checks
        results = checker.run_all_checks()
        print(checker.format_output(results, args.format))
        
        # Exit with appropriate code
        if results["overall_status"] == "error":
            sys.exit(1)
        elif results["overall_status"] == "warning":
            sys.exit(2)


if __name__ == "__main__":
    main() 