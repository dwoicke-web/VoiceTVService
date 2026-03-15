"""
Input validation utilities for API endpoints
Prevents injection attacks, malformed data, and invalid requests
"""

import re
import logging
from typing import Any, Optional, Dict, List

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


def validate_query_string(query: str, min_length: int = 1, max_length: int = 256) -> str:
    """
    Validate search query string

    Args:
        query: Query string to validate
        min_length: Minimum query length
        max_length: Maximum query length

    Returns:
        Validated and sanitized query string

    Raises:
        ValidationError: If query is invalid
    """
    if not isinstance(query, str):
        raise ValidationError("Query must be a string")

    query = query.strip()

    if len(query) < min_length:
        raise ValidationError(f"Query must be at least {min_length} character(s)")

    if len(query) > max_length:
        raise ValidationError(f"Query must be no more than {max_length} characters")

    # Remove control characters
    query = ''.join(char for char in query if ord(char) >= 32)

    # Check for SQL injection patterns (basic check)
    dangerous_patterns = [
        r"('.*)|(--)|(;.*)|(/\*.*\*/)|(\*.*)",  # SQL injection
        r"(<.*>)|(&quot;)|(&#x)|(&#)",  # HTML/XML injection
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            logger.warning(f"Suspicious pattern detected in query: {query[:50]}...")
            raise ValidationError("Query contains invalid characters or patterns")

    return query


def validate_content_type(content_type: str) -> str:
    """
    Validate content type parameter

    Args:
        content_type: Content type to validate

    Returns:
        Validated content type

    Raises:
        ValidationError: If content type is invalid
    """
    valid_types = ['all', 'show', 'movie', 'sports']
    content_type = content_type.lower().strip()

    if content_type not in valid_types:
        raise ValidationError(f"Invalid content_type. Must be one of: {', '.join(valid_types)}")

    return content_type


def validate_tv_id(tv_id: str) -> str:
    """
    Validate TV device ID

    Args:
        tv_id: TV ID to validate

    Returns:
        Validated TV ID

    Raises:
        ValidationError: If TV ID is invalid
    """
    valid_ids = ['big_screen', 'upper_left', 'upper_right', 'lower_left', 'lower_right']

    tv_id = tv_id.lower().strip()

    if tv_id not in valid_ids:
        raise ValidationError(f"Invalid tv_id. Must be one of: {', '.join(valid_ids)}")

    return tv_id


def validate_volume_level(level: Any) -> int:
    """
    Validate volume level

    Args:
        level: Volume level to validate

    Returns:
        Validated volume level (0-100)

    Raises:
        ValidationError: If level is invalid
    """
    try:
        level = int(level)
    except (ValueError, TypeError):
        raise ValidationError("Volume level must be an integer")

    if level < 0 or level > 100:
        raise ValidationError("Volume level must be between 0 and 100")

    return level


def validate_power_action(action: str) -> str:
    """
    Validate power control action

    Args:
        action: Power action to validate

    Returns:
        Validated power action

    Raises:
        ValidationError: If action is invalid
    """
    valid_actions = ['on', 'off']
    action = action.lower().strip()

    if action not in valid_actions:
        raise ValidationError(f"Invalid action. Must be one of: {', '.join(valid_actions)}")

    return action


def validate_json_data(data: Optional[Dict], required_fields: List[str]) -> Dict:
    """
    Validate JSON request data

    Args:
        data: JSON data to validate
        required_fields: List of required field names

    Returns:
        Validated data dictionary

    Raises:
        ValidationError: If data is missing required fields
    """
    if data is None:
        raise ValidationError("Request body must be JSON")

    if not isinstance(data, dict):
        raise ValidationError("Request body must be a JSON object")

    for field in required_fields:
        if field not in data or data[field] is None:
            raise ValidationError(f"Missing required field: {field}")

    return data


def validate_service_name(service: str) -> str:
    """
    Validate streaming service name

    Args:
        service: Service name to validate

    Returns:
        Validated service name

    Raises:
        ValidationError: If service is invalid
    """
    valid_services = [
        'YouTubeTV', 'Peacock', 'ESPN+', 'Amazon Prime', 'HBO Max',
        'YouTube', 'Fandango', 'Vudu', 'JustWatch'
    ]

    if service not in valid_services:
        raise ValidationError(f"Invalid service. Must be one of: {', '.join(valid_services)}")

    return service
