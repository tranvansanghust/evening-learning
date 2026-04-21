"""Tests for re-engagement message logic."""

from app.services.message_formatter import build_reengagement_message


class TestReengagementMessages:
    def test_1_day_inactive(self):
        msg = build_reengagement_message(1, "React")
        assert msg is not None
        assert "React" in msg

    def test_3_days_inactive(self):
        msg = build_reengagement_message(3, "Python")
        assert msg is not None
        assert "3" in msg
        assert "Python" in msg

    def test_5_days_inactive(self):
        msg = build_reengagement_message(5, "SQL")
        assert msg is not None
        assert "5" in msg

    def test_0_days_returns_none(self):
        assert build_reengagement_message(0, "React") is None

    def test_2_days_returns_none(self):
        assert build_reengagement_message(2, "React") is None

    def test_6_days_returns_none(self):
        assert build_reengagement_message(6, "React") is None
