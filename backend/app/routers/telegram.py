"""
Telegram webhook router for receiving and processing updates.

This module defines the webhook endpoint that Telegram sends updates to.
Updates are parsed and routed to appropriate handlers for processing.

The webhook expects POST requests from Telegram containing update objects
in JSON format. Responses are immediately returned to Telegram to confirm
successful receipt (webhook mode has a 30-second timeout).
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse

from app.config import settings
from app.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)

# Create router for Telegram webhook
router = APIRouter(tags=["Telegram Webhook"])

# Global TelegramService instance (initialized on first request)
telegram_service: TelegramService = None


def get_telegram_service() -> TelegramService:
    """
    Get or initialize the TelegramService instance.

    Uses lazy initialization to ensure bot token is available.

    Returns:
        TelegramService: Singleton instance of the Telegram service

    Raises:
        ValueError: If Telegram bot token is not configured
    """
    global telegram_service

    if telegram_service is None:
        if not settings.telegram_bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not configured in environment")
            raise ValueError("Telegram bot token not configured")

        telegram_service = TelegramService(settings.telegram_bot_token)

    return telegram_service


@router.post("/webhook/telegram")
async def telegram_webhook(request: Request) -> JSONResponse:
    """
    Receive and process Telegram webhook updates.

    This endpoint receives POST requests from Telegram containing updates
    in JSON format. The update is parsed and routed to appropriate handlers.

    Updates are processed asynchronously while immediately returning a 200
    response to Telegram to avoid webhook delivery timeouts.

    Args:
        request: FastAPI request object containing the Telegram update

    Returns:
        JSONResponse: Success response to confirm receipt to Telegram

    Raises:
        HTTPException: If request parsing or validation fails

    Example:
        Telegram sends:
        {
            "update_id": 123456,
            "message": {
                "message_id": 1,
                "from": {"id": 987654, "first_name": "John"},
                "text": "/start"
            }
        }

    Note:
        - Telegram expects a response within 30 seconds
        - Response body is ignored by Telegram, only HTTP status matters
        - Failed updates are logged but don't affect webhook delivery
    """
    try:
        # Parse incoming JSON from Telegram
        update_dict = await request.json()
        logger.info(f"Received webhook update: {update_dict.get('update_id')}")

        # Get or initialize TelegramService
        service = get_telegram_service()

        # Parse the update into standard format
        parsed_update = service.parse_update(update_dict)

        if parsed_update is None:
            logger.warning(f"Failed to parse update: {update_dict}")
            # Return 200 to Telegram anyway - don't retry unparseable updates
            return JSONResponse(
                status_code=200,
                content={"ok": True, "message": "Update received but not parsed"}
            )

        logger.info(
            f"Parsed update from user {parsed_update.user_id}: "
            f"type={parsed_update.update_type}, text={parsed_update.message_text}"
        )

        # TODO: Route to appropriate handler based on message_text/command
        # This will be implemented by telegram_handlers.py
        # For now, just log the update
        logger.debug(f"Update ready for routing: {parsed_update.__dict__}")

        # Immediately return success to Telegram
        return JSONResponse(
            status_code=200,
            content={"ok": True, "message": "Update received"}
        )

    except ValueError as e:
        logger.error(f"JSON parsing error: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON in request")
    except Exception as e:
        logger.error(f"Unexpected error in webhook: {str(e)}")
        # Return 200 anyway to prevent Telegram from retrying
        return JSONResponse(
            status_code=200,
            content={"ok": True, "message": "Webhook processed with errors"}
        )


@router.get("/health/telegram")
async def telegram_health() -> Dict[str, Any]:
    """
    Health check endpoint for Telegram webhook.

    Verifies that the Telegram service is properly initialized and
    can communicate with the Telegram API.

    Returns:
        dict: Status information including bot username and webhook config

    Example:
        {
            "status": "healthy",
            "service": "telegram-webhook",
            "bot_token_configured": true,
            "webhook_url": "https://example.com/webhook/telegram"
        }
    """
    try:
        service = get_telegram_service()
        return {
            "status": "healthy",
            "service": "telegram-webhook",
            "bot_token_configured": bool(settings.telegram_bot_token),
            "webhook_url": settings.telegram_webhook_url or "not configured",
        }
    except ValueError as e:
        logger.warning(f"Telegram health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "service": "telegram-webhook",
            "error": str(e),
        }
