"""
SQL Query Validator for Safe Query Execution

Provides security validation for user-submitted SQL queries to prevent
destructive operations and SQL injection attacks.
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class SQLValidationError(Exception):
    """Raised when SQL query validation fails"""
    pass


class SQLValidator:
    """Validates SQL queries for safe execution"""

    # Dangerous SQL keywords that should be blocked
    BLOCKED_KEYWORDS = {
        'DELETE', 'DROP', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT',
        'UPDATE', 'REPLACE', 'RENAME', 'GRANT', 'REVOKE', 'EXECUTE',
        'EXEC', 'PRAGMA', 'ATTACH', 'DETACH'
    }

    # Only allow SELECT statements
    ALLOWED_STATEMENTS = {'SELECT', 'WITH', 'EXPLAIN'}

    # Maximum rows to return (safety limit)
    DEFAULT_MAX_ROWS = 10000

    # Maximum query execution time (seconds)
    DEFAULT_TIMEOUT = 30

    def __init__(self,
                 max_rows: int = DEFAULT_MAX_ROWS,
                 timeout_seconds: int = DEFAULT_TIMEOUT,
                 enforce_limit: bool = True):
        """
        Initialize SQL validator

        Args:
            max_rows: Maximum number of rows to return
            timeout_seconds: Maximum query execution time
            enforce_limit: Whether to enforce LIMIT clause on queries
        """
        self.max_rows = max_rows
        self.timeout_seconds = timeout_seconds
        self.enforce_limit = enforce_limit

    def validate_query(self, query: str) -> Tuple[str, Dict[str, Any]]:
        """
        Validate and potentially modify a SQL query for safe execution

        Args:
            query: The SQL query to validate

        Returns:
            Tuple of (validated_query, metadata)

        Raises:
            SQLValidationError: If query is invalid or dangerous
        """
        if not query or not query.strip():
            raise SQLValidationError("Query cannot be empty")

        # Normalize query
        query = query.strip()
        query_upper = query.upper()

        # Check for blocked keywords
        self._check_blocked_keywords(query_upper)

        # Check statement type
        self._check_statement_type(query_upper)

        # Check for SQL injection patterns
        self._check_injection_patterns(query)

        # Check for multiple statements
        self._check_multiple_statements(query)

        # Add or validate LIMIT clause if enforced
        if self.enforce_limit:
            query = self._enforce_limit(query, query_upper)

        metadata = {
            "max_rows": self.max_rows,
            "timeout_seconds": self.timeout_seconds,
            "validated": True
        }

        logger.debug(f"Query validated successfully: {query[:100]}...")
        return query, metadata

    def _check_blocked_keywords(self, query_upper: str):
        """Check for dangerous SQL keywords"""
        # Split into words and check each
        words = re.findall(r'\b[A-Z]+\b', query_upper)

        for keyword in self.BLOCKED_KEYWORDS:
            if keyword in words:
                raise SQLValidationError(
                    f"Blocked keyword detected: {keyword}. Only SELECT queries are allowed."
                )

    def _check_statement_type(self, query_upper: str):
        """Verify query starts with an allowed statement"""
        # Get the first keyword
        match = re.match(r'\s*(\w+)', query_upper)
        if not match:
            raise SQLValidationError("Invalid query format")

        first_keyword = match.group(1)

        if first_keyword not in self.ALLOWED_STATEMENTS:
            raise SQLValidationError(
                f"Query must start with {', '.join(self.ALLOWED_STATEMENTS)}. "
                f"Got: {first_keyword}"
            )

    def _check_injection_patterns(self, query: str):
        """Check for common SQL injection patterns"""
        # Look for suspicious patterns
        injection_patterns = [
            r';\s*DROP',
            r';\s*DELETE',
            r';\s*UPDATE',
            r'--.*DROP',
            r'/\*.*DROP.*\*/',
            r'UNION.*SELECT.*FROM.*INFORMATION_SCHEMA',
            r'1\s*=\s*1',  # Common injection pattern
            r"'\s*OR\s*'.*'='",  # ' OR '1'='1
        ]

        query_upper = query.upper()
        for pattern in injection_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                raise SQLValidationError(
                    f"Potential SQL injection detected. Pattern matched: {pattern}"
                )

    def _check_multiple_statements(self, query: str):
        """Check for multiple SQL statements (prevents stacked queries)"""
        # Remove string literals to avoid false positives
        query_no_strings = re.sub(r"'[^']*'", '', query)
        query_no_strings = re.sub(r'"[^"]*"', '', query_no_strings)

        # Count semicolons (excluding those in comments or strings)
        semicolons = query_no_strings.count(';')

        # Allow one trailing semicolon
        if semicolons > 1 or (semicolons == 1 and not query_no_strings.rstrip().endswith(';')):
            raise SQLValidationError(
                "Multiple SQL statements not allowed. Only single SELECT queries permitted."
            )

    def _enforce_limit(self, query: str, query_upper: str) -> str:
        """Enforce or validate LIMIT clause"""
        # Check if query already has a LIMIT
        limit_match = re.search(r'\bLIMIT\s+(\d+)', query_upper)

        if limit_match:
            # Validate existing limit
            limit_value = int(limit_match.group(1))
            if limit_value > self.max_rows:
                # Replace with max allowed
                query = re.sub(
                    r'\bLIMIT\s+\d+',
                    f'LIMIT {self.max_rows}',
                    query,
                    flags=re.IGNORECASE
                )
                logger.warning(
                    f"Query LIMIT reduced from {limit_value} to {self.max_rows}"
                )
        else:
            # Add LIMIT clause
            # Handle queries that might end with semicolon
            if query.rstrip().endswith(';'):
                query = query.rstrip()[:-1] + f' LIMIT {self.max_rows};'
            else:
                query = query + f' LIMIT {self.max_rows}'

            logger.info(f"Added LIMIT {self.max_rows} to query")

        return query

    def get_safe_tables(self) -> list:
        """
        Return list of tables that are safe to query

        Returns:
            List of table names
        """
        return [
            'sensor_readings',
            'sensor_data',
            'actuator_states',
            'device_events',
            'device_errors',
            'device_capabilities',
            'device_metrics',
            'devices'
        ]

    def validate_table_access(self, query: str, allowed_tables: Optional[list] = None) -> bool:
        """
        Check if query only accesses allowed tables

        Args:
            query: SQL query
            allowed_tables: List of allowed table names (uses default if None)

        Returns:
            True if all tables are allowed

        Raises:
            SQLValidationError: If unauthorized table is accessed
        """
        if allowed_tables is None:
            allowed_tables = self.get_safe_tables()

        # Extract table names from FROM and JOIN clauses
        table_pattern = r'\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        tables = re.findall(table_pattern, query, re.IGNORECASE)

        for table in tables:
            if table.lower() not in [t.lower() for t in allowed_tables]:
                raise SQLValidationError(
                    f"Access to table '{table}' is not allowed. "
                    f"Allowed tables: {', '.join(allowed_tables)}"
                )

        return True


def validate_sql_query(query: str,
                       max_rows: int = 10000,
                       timeout_seconds: int = 30,
                       enforce_limit: bool = True) -> Tuple[str, Dict[str, Any]]:
    """
    Convenience function to validate a SQL query

    Args:
        query: SQL query to validate
        max_rows: Maximum rows to return
        timeout_seconds: Query timeout
        enforce_limit: Whether to enforce LIMIT

    Returns:
        Tuple of (validated_query, metadata)

    Raises:
        SQLValidationError: If validation fails
    """
    validator = SQLValidator(max_rows, timeout_seconds, enforce_limit)
    return validator.validate_query(query)
