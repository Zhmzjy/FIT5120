"""
Utility Functions for Melbourne Parking API
"""

import re
from typing import Tuple, Optional
from datetime import datetime

class LocationUtils:
    """Utilities for location-based operations"""

    @staticmethod
    def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calculate approximate distance between two points in kilometers
        Using simplified calculation for Melbourne area

        Args:
            lat1, lng1: First coordinate pair
            lat2, lng2: Second coordinate pair

        Returns:
            Distance in kilometers
        """
        lat_diff = abs(lat1 - lat2)
        lng_diff = abs(lng1 - lng2)

        # Rough conversion for Melbourne area: 1 degree ≈ 111 km
        lat_km = lat_diff * 111.0
        lng_km = lng_diff * 111.0 * abs(lat1 / 90.0)  # Adjust for latitude

        return (lat_km ** 2 + lng_km ** 2) ** 0.5

    @staticmethod
    def is_valid_coordinate(lat: float, lng: float) -> bool:
        """
        Validate if coordinates are within Melbourne area

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            True if coordinates are valid for Melbourne
        """
        # Melbourne approximate bounds
        melbourne_bounds = {
            'lat_min': -38.5,
            'lat_max': -37.5,
            'lng_min': 144.5,
            'lng_max': 145.5
        }

        return (melbourne_bounds['lat_min'] <= lat <= melbourne_bounds['lat_max'] and
                melbourne_bounds['lng_min'] <= lng <= melbourne_bounds['lng_max'])

class ValidationUtils:
    """Utilities for data validation"""

    @staticmethod
    def validate_postcode(postcode: str) -> bool:
        """
        Validate Melbourne postcode format

        Args:
            postcode: Postcode string to validate

        Returns:
            True if valid Melbourne postcode
        """
        if not postcode or not isinstance(postcode, str):
            return False

        # Melbourne postcodes are typically 3000-3999
        try:
            code = int(postcode.strip())
            return 3000 <= code <= 3999
        except ValueError:
            return False

    @staticmethod
    def sanitize_search_query(query: str) -> str:
        """
        Sanitize search query input

        Args:
            query: Raw search query

        Returns:
            Sanitized query string
        """
        if not query:
            return ""

        # Remove special characters, keep alphanumeric and spaces
        sanitized = re.sub(r'[^\w\s-]', '', query.strip())

        # Limit length
        return sanitized[:100]

class TimeUtils:
    """Utilities for time operations"""

    @staticmethod
    def format_timestamp(timestamp: datetime) -> str:
        """
        Format timestamp for API responses

        Args:
            timestamp: DateTime object

        Returns:
            Formatted timestamp string
        """
        if not timestamp:
            return ""

        return timestamp.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def get_time_ago(timestamp: datetime) -> str:
        """
        Get human-readable time difference

        Args:
            timestamp: DateTime to compare

        Returns:
            Human-readable time difference
        """
        if not timestamp:
            return "Unknown"

        now = datetime.utcnow()
        diff = now - timestamp

        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"

class ResponseUtils:
    """Utilities for API responses"""

    @staticmethod
    def success_response(data: dict, message: str = None) -> dict:
        """
        Create standardized success response

        Args:
            data: Response data
            message: Optional success message

        Returns:
            Standardized response dictionary
        """
        response = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }

        if message:
            response['message'] = message

        return response

    @staticmethod
    def error_response(error: str, code: int = 500) -> Tuple[dict, int]:
        """
        Create standardized error response

        Args:
            error: Error message
            code: HTTP status code

        Returns:
            Tuple of (response dict, status code)
        """
        response = {
            'success': False,
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        }

