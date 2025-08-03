"""
Timezone-aware utilities for consistent datetime handling across the MCP-MQTT bridge.

This module provides UTC-based datetime functions to ensure consistency
across different timezones and server locations.
"""

from datetime import datetime, timezone, timedelta
from typing import Union, Optional


def utc_now() -> datetime:
    """Get current UTC time with timezone information."""
    return datetime.now(timezone.utc)


def utc_timestamp() -> float:
    """Get current UTC timestamp as float."""
    return utc_now().timestamp()


def from_timestamp(timestamp: Union[float, int], tz: Optional[timezone] = None) -> datetime:
    """Convert timestamp to timezone-aware datetime.
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        tz: Target timezone (defaults to UTC)
        
    Returns:
        Timezone-aware datetime object
    """
    if tz is None:
        tz = timezone.utc
    return datetime.fromtimestamp(timestamp, tz=tz)


def from_timestamp_utc(timestamp: Union[float, int]) -> datetime:
    """Convert timestamp to UTC datetime."""
    return from_timestamp(timestamp, timezone.utc)


def to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC.
    
    Args:
        dt: Datetime object (naive datetimes are assumed to be local time)
        
    Returns:
        UTC datetime with timezone info
    """
    if dt.tzinfo is None:
        # Naive datetime - assume it's local time and convert to UTC
        return dt.replace(tzinfo=timezone.utc)
    elif dt.tzinfo != timezone.utc:
        # Convert to UTC
        return dt.astimezone(timezone.utc)
    else:
        # Already UTC
        return dt


def age_seconds(dt: datetime) -> float:
    """Calculate age in seconds from UTC now.
    
    Args:
        dt: Datetime to calculate age for
        
    Returns:
        Age in seconds (float)
    """
    dt_utc = to_utc(dt)
    return (utc_now() - dt_utc).total_seconds()


def age_minutes(dt: datetime) -> float:
    """Calculate age in minutes from UTC now."""
    return age_seconds(dt) / 60.0


def utc_plus_timedelta(delta: timedelta) -> datetime:
    """Get UTC time plus a timedelta."""
    return utc_now() + delta


def utc_minus_timedelta(delta: timedelta) -> datetime:
    """Get UTC time minus a timedelta."""
    return utc_now() - delta


def ensure_utc(dt: Union[datetime, str, float, int, None], device_boot_time: Optional[datetime] = None) -> datetime:
    """Ensure a value is a UTC datetime.
    
    Args:
        dt: Input value - can be datetime, ISO string, timestamp, or None
        device_boot_time: Device boot time for converting milliseconds-since-boot timestamps
        
    Returns:
        UTC datetime object
    """
    if dt is None:
        return utc_now()
    elif isinstance(dt, datetime):
        return to_utc(dt)
    elif isinstance(dt, str):
        # Parse ISO format string
        try:
            parsed = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            return to_utc(parsed)
        except ValueError:
            # Fallback to current time if parsing fails
            return utc_now()
    elif isinstance(dt, (int, float)):
        # Handle different timestamp formats
        # ESP32 milliseconds since boot: 0 to ~49 days (4,294,967,295 ms = 49.7 days)
        # Unix timestamps are typically > 1,000,000,000 (year 2001+)
        
        if dt >= 0 and dt < 1000000000:  # Less than year 2001 = likely milliseconds since boot
            if device_boot_time is not None:
                # Convert milliseconds to timedelta and add to device boot time
                return device_boot_time + timedelta(milliseconds=dt)
            else:
                # No device boot time available, use current time
                return utc_now()
        else:
            # Assume it's a Unix timestamp (seconds since epoch)
            return from_timestamp_utc(dt)
    else:
        return utc_now()


def utc_isoformat(dt: Optional[datetime] = None) -> str:
    """Get UTC ISO format string.
    
    Args:
        dt: Datetime to format (defaults to current UTC time)
        
    Returns:
        ISO format string with UTC timezone suffix
    """
    if dt is None:
        dt = utc_now()
    else:
        dt = to_utc(dt)
    
    # Format with 'Z' suffix for UTC
    return dt.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')


def is_expired(dt: datetime, timeout_minutes: int) -> bool:
    """Check if a datetime is expired based on timeout.
    
    Args:
        dt: Datetime to check
        timeout_minutes: Timeout in minutes
        
    Returns:
        True if expired, False otherwise
    """
    dt_utc = to_utc(dt)
    timeout_delta = timedelta(minutes=timeout_minutes)
    return (utc_now() - dt_utc) > timeout_delta


def format_age(dt: datetime) -> str:
    """Format age as human-readable string.
    
    Args:
        dt: Datetime to calculate age for
        
    Returns:
        Human-readable age string (e.g., "2m 30s ago", "1h 15m ago")
    """
    total_seconds = age_seconds(dt)
    
    if total_seconds < 60:
        return f"{int(total_seconds)}s ago"
    elif total_seconds < 3600:  # Less than 1 hour
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        return f"{minutes}m {seconds}s ago"
    elif total_seconds < 86400:  # Less than 1 day
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        return f"{hours}h {minutes}m ago"
    else:  # 1 day or more
        days = int(total_seconds // 86400)
        hours = int((total_seconds % 86400) // 3600)
        return f"{days}d {hours}h ago"