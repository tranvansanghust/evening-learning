"""
Utility modules for the evening learning backend.

Provides helper classes and functions for common tasks across the application.
"""

from app.utils.http_client import HTTPClient, HTTPClientError

__all__ = [
    "HTTPClient",
    "HTTPClientError",
]
