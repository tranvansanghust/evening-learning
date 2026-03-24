"""
Telegram service for sending messages and parsing updates.

This module provides the TelegramService class which handles:
- Sending text messages to users via Telegram Bot API
- Sending messages with inline buttons
- Parsing Telegram Update objects into standard format
- Managing Telegram API communication via aiogram Client
"""

import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update

logger = logging.getLogger(__name__)


@dataclass
class InlineButton:
    """
    Represents an inline button for Telegram messages.

    Attributes:
        text: Display text on the button
        callback_data: Data sent when button is pressed
    """
    text: str
    callback_data: str


class ParsedUpdate:
    """
    Standardized representation of a Telegram update.

    Attributes:
        user_id: Telegram user ID
        message_text: Text content of the message (if available)
        update_type: Type of update (message, callback_query, etc.)
        raw_update: Original Telegram Update object
    """

    def __init__(
        self,
        user_id: str,
        message_text: Optional[str] = None,
        update_type: str = "message",
        raw_update: Optional[Update] = None,
    ):
        self.user_id = user_id
        self.message_text = message_text
        self.update_type = update_type
        self.raw_update = raw_update


class TelegramService:
    """
    Service for managing Telegram Bot communications.

    Handles sending messages to users and parsing incoming updates
    from the Telegram Bot API. Uses aiogram 3.x Client for all
    API communication.
    """

    def __init__(self, bot_token: str):
        """
        Initialize TelegramService with bot token.

        Args:
            bot_token: Telegram Bot API token from @BotFather

        Raises:
            ValueError: If bot_token is empty or invalid
        """
        if not bot_token or not bot_token.strip():
            raise ValueError("Telegram bot token cannot be empty")

        self.bot = Bot(token=bot_token)
        logger.info("TelegramService initialized with bot token")

    async def send_message(self, user_id: str, text: str) -> bool:
        """
        Send a simple text message to a user.

        Args:
            user_id: Telegram user ID to send message to
            text: Message text to send

        Returns:
            bool: True if message sent successfully, False otherwise

        Example:
            >>> service = TelegramService(token)
            >>> await service.send_message("123456789", "Hello!")
            True
        """
        try:
            await self.bot.send_message(
                chat_id=int(user_id),
                text=text,
                parse_mode="HTML"
            )
            logger.info(f"Message sent to user {user_id}")
            return True
        except ValueError as e:
            logger.error(f"Invalid user_id format: {user_id} - {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Failed to send message to user {user_id}: {str(e)}")
            return False

    async def send_message_with_buttons(
        self,
        user_id: str,
        text: str,
        buttons: List[InlineButton],
        rows: int = 2,
    ) -> bool:
        """
        Send a message with inline buttons to a user.

        Args:
            user_id: Telegram user ID to send message to
            text: Message text to send
            buttons: List of InlineButton objects to display
            rows: Number of buttons per row (default: 2)

        Returns:
            bool: True if message sent successfully, False otherwise

        Example:
            >>> buttons = [
            ...     InlineButton("Yes", "q_1_yes"),
            ...     InlineButton("No", "q_1_no"),
            ... ]
            >>> await service.send_message_with_buttons(
            ...     "123456789",
            ...     "Do you want to continue?",
            ...     buttons
            ... )
            True
        """
        try:
            keyboard = self._build_keyboard(buttons, rows)
            await self.bot.send_message(
                chat_id=int(user_id),
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            logger.info(f"Message with {len(buttons)} buttons sent to user {user_id}")
            return True
        except ValueError as e:
            logger.error(f"Invalid user_id format: {user_id} - {str(e)}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to send message with buttons to user {user_id}: {str(e)}"
            )
            return False

    def _build_keyboard(
        self,
        buttons: List[InlineButton],
        rows: int = 2
    ) -> InlineKeyboardMarkup:
        """
        Build an InlineKeyboardMarkup from a list of buttons.

        Args:
            buttons: List of InlineButton objects
            rows: Number of buttons per row

        Returns:
            InlineKeyboardMarkup: Formatted keyboard for Telegram API
        """
        keyboard_rows = []
        for i in range(0, len(buttons), rows):
            row = [
                InlineKeyboardButton(
                    text=btn.text,
                    callback_data=btn.callback_data
                )
                for btn in buttons[i : i + rows]
            ]
            keyboard_rows.append(row)

        return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    def parse_update(self, update_dict: Dict[str, Any]) -> Optional[ParsedUpdate]:
        """
        Parse a Telegram update dictionary into standardized format.

        Extracts user_id and message_text from various update types:
        - message: Regular text messages
        - callback_query: Button presses
        - edited_message: Edited messages

        Args:
            update_dict: Raw update dictionary from Telegram API webhook

        Returns:
            ParsedUpdate: Standardized update object, or None if parsing fails

        Example:
            >>> update_dict = {
            ...     "update_id": 123456,
            ...     "message": {
            ...         "message_id": 1,
            ...         "from": {"id": 987654},
            ...         "text": "Hello bot"
            ...     }
            ... }
            >>> parsed = service.parse_update(update_dict)
            >>> print(parsed.user_id, parsed.message_text)
            987654 Hello bot
        """
        try:
            # Handle message updates
            if "message" in update_dict:
                message = update_dict["message"]
                user_id = str(message.get("from", {}).get("id"))
                text = message.get("text")

                if not user_id or user_id == "None":
                    logger.warning("Could not extract user_id from message")
                    return None

                logger.info(f"Parsed message update from user {user_id}")
                return ParsedUpdate(
                    user_id=user_id,
                    message_text=text,
                    update_type="message"
                )

            # Handle callback query updates (button presses)
            if "callback_query" in update_dict:
                callback = update_dict["callback_query"]
                user_id = str(callback.get("from", {}).get("id"))
                data = callback.get("data")

                if not user_id or user_id == "None":
                    logger.warning("Could not extract user_id from callback_query")
                    return None

                logger.info(f"Parsed callback_query from user {user_id}: {data}")
                return ParsedUpdate(
                    user_id=user_id,
                    message_text=data,
                    update_type="callback_query"
                )

            # Handle edited message updates
            if "edited_message" in update_dict:
                message = update_dict["edited_message"]
                user_id = str(message.get("from", {}).get("id"))
                text = message.get("text")

                if not user_id or user_id == "None":
                    logger.warning("Could not extract user_id from edited_message")
                    return None

                logger.info(f"Parsed edited_message from user {user_id}")
                return ParsedUpdate(
                    user_id=user_id,
                    message_text=text,
                    update_type="edited_message"
                )

            logger.warning(f"Unknown update type: {list(update_dict.keys())}")
            return None

        except Exception as e:
            logger.error(f"Error parsing update: {str(e)}")
            return None

    async def close(self) -> None:
        """
        Close the bot session and clean up resources.

        Call this during application shutdown to properly close
        the HTTP session used by aiogram Bot.
        """
        try:
            await self.bot.session.close()
            logger.info("TelegramService session closed")
        except Exception as e:
            logger.error(f"Error closing TelegramService: {str(e)}")
