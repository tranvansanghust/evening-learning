"""
HTTP client for making internal API calls to FastAPI endpoints.

This module provides a helper class to make HTTP requests from handlers
to local FastAPI endpoints, useful for calling internal services from
the Telegram handler layer.

Utilities:
    - HTTPClient: Client for making internal API calls
"""

import logging
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)


class HTTPClient:
    """
    Client for making HTTP calls to internal FastAPI endpoints.

    Used by Telegram handlers to call business logic endpoints
    without direct coupling. Provides error handling and logging.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize HTTP client with base URL.

        Args:
            base_url: Base URL for API endpoints (default: localhost:8000)

        Example:
            >>> client = HTTPClient()
            >>> result = await client.call_endpoint(
            ...     "POST",
            ...     "/api/quiz/start",
            ...     {"user_id": 1, "lesson_id": 5}
            ... )
        """
        self.base_url = base_url
        logger.info(f"HTTPClient initialized with base URL: {base_url}")

    async def call_endpoint(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Make an HTTP call to a local FastAPI endpoint.

        Handles connection errors gracefully and logs all requests/responses.

        Args:
            method: HTTP method ('GET', 'POST', 'PUT', 'DELETE', etc.)
            path: API path (e.g., '/api/quiz/start')
            data: Optional request body data (for POST/PUT requests)
            timeout: Request timeout in seconds (default: 30)

        Returns:
            dict: Parsed JSON response from endpoint, or None on error

        Raises:
            HTTPClientError: On HTTP errors (4xx, 5xx)

        Example:
            >>> client = HTTPClient()
            >>> result = await client.call_endpoint(
            ...     "POST",
            ...     "/api/quiz/submit",
            ...     {"session_id": 1, "answer": "useState"}
            ... )
            >>> if result:
            ...     print(result.get("next_question"))
        """
        url = f"{self.base_url}{path}"
        method = method.upper()

        try:
            logger.info(f"Calling {method} {url}")

            async with httpx.AsyncClient(timeout=timeout) as client:
                if method == "GET":
                    response = await client.get(url)
                elif method == "POST":
                    response = await client.post(url, json=data)
                elif method == "PUT":
                    response = await client.put(url, json=data)
                elif method == "DELETE":
                    response = await client.delete(url)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Check for HTTP errors
                response.raise_for_status()

                # Parse and return response
                logger.info(f"Response status: {response.status_code}")
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error {e.response.status_code} from {method} {url}: "
                f"{e.response.text}"
            )
            return None

        except httpx.ConnectError as e:
            logger.error(f"Connection error calling {method} {url}: {str(e)}")
            return None

        except httpx.TimeoutException as e:
            logger.error(f"Timeout calling {method} {url}: {str(e)}")
            return None

        except Exception as e:
            logger.error(f"Error calling {method} {url}: {str(e)}")
            return None

    async def get(
        self,
        path: str,
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Make a GET request to an endpoint.

        Convenience method for GET requests.

        Args:
            path: API path
            timeout: Request timeout in seconds

        Returns:
            dict: Parsed JSON response, or None on error

        Example:
            >>> client = HTTPClient()
            >>> result = await client.get("/api/progress/user/1")
        """
        return await self.call_endpoint("GET", path, timeout=timeout)

    async def post(
        self,
        path: str,
        data: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Make a POST request to an endpoint.

        Convenience method for POST requests.

        Args:
            path: API path
            data: Request body data
            timeout: Request timeout in seconds

        Returns:
            dict: Parsed JSON response, or None on error

        Example:
            >>> client = HTTPClient()
            >>> result = await client.post(
            ...     "/api/quiz/submit",
            ...     {"session_id": 1, "answer": "useState"}
            ... )
        """
        return await self.call_endpoint("POST", path, data, timeout=timeout)

    async def put(
        self,
        path: str,
        data: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Make a PUT request to an endpoint.

        Convenience method for PUT requests.

        Args:
            path: API path
            data: Request body data
            timeout: Request timeout in seconds

        Returns:
            dict: Parsed JSON response, or None on error

        Example:
            >>> client = HTTPClient()
            >>> result = await client.put(
            ...     "/api/user/1",
            ...     {"username": "new_name"}
            ... )
        """
        return await self.call_endpoint("PUT", path, data, timeout=timeout)

    async def delete(
        self,
        path: str,
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Make a DELETE request to an endpoint.

        Convenience method for DELETE requests.

        Args:
            path: API path
            timeout: Request timeout in seconds

        Returns:
            dict: Parsed JSON response, or None on error

        Example:
            >>> client = HTTPClient()
            >>> result = await client.delete("/api/session/1")
        """
        return await self.call_endpoint("DELETE", path, timeout=timeout)


class HTTPClientError(Exception):
    """Exception raised for HTTP client errors."""

    pass
