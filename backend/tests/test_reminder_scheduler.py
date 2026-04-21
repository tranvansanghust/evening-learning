"""Tests for reminder_time storage and scheduler logic."""
from unittest.mock import MagicMock
from datetime import datetime


# --- Helper ---
def make_user(reminder_time=None, telegram_id="123"):
    u = MagicMock()
    u.user_id = 1
    u.telegram_id = telegram_id
    u.reminder_time = reminder_time
    return u


def make_enrollment(status="IN_PROGRESS"):
    e = MagicMock()
    e.status = status
    return e


# --- Test should_send_reminder logic ---
def should_send_reminder(user, current_time: str, has_active_course: bool) -> bool:
    """Helper to decide whether to send reminder — pure logic, no DB needed."""
    if not user.reminder_time:
        return False
    if not has_active_course:
        return False
    return user.reminder_time == current_time


class TestShouldSendReminder:
    def test_matching_time_active_course(self):
        user = make_user(reminder_time="20:00")
        assert should_send_reminder(user, "20:00", True) is True

    def test_non_matching_time(self):
        user = make_user(reminder_time="20:00")
        assert should_send_reminder(user, "21:00", True) is False

    def test_no_reminder_time(self):
        user = make_user(reminder_time=None)
        assert should_send_reminder(user, "20:00", True) is False

    def test_no_active_course(self):
        user = make_user(reminder_time="20:00")
        assert should_send_reminder(user, "20:00", False) is False
