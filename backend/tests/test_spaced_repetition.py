"""Tests for spaced repetition interval logic."""
from datetime import datetime, timedelta


def get_next_interval_days(review_count: int) -> int:
    """Trả số ngày cho interval tiếp theo."""
    intervals = {0: 3, 1: 7, 2: 14}
    return intervals.get(review_count, 30)


class TestSpacedRepetitionIntervals:
    def test_first_quiz_interval_3_days(self):
        assert get_next_interval_days(0) == 3

    def test_first_review_interval_7_days(self):
        assert get_next_interval_days(1) == 7

    def test_second_review_interval_14_days(self):
        assert get_next_interval_days(2) == 14

    def test_third_and_beyond_interval_30_days(self):
        assert get_next_interval_days(3) == 30
        assert get_next_interval_days(10) == 30
