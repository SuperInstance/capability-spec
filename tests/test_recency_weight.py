"""Tests for recency_weight function."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from capability_spec import recency_weight


class TestRecencyWeightBasic:
    """Basic recency weight tests."""

    def test_today(self):
        today = datetime.utcnow().strftime('%Y-%m-%d')
        assert recency_weight(today) == 1.0

    def test_yesterday(self):
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
        # Exactly 1 day ago → still < 1 day boundary depends on exact timing
        result = recency_weight(yesterday)
        assert result in (0.9, 1.0)

    def test_two_days_ago(self):
        two_days = (datetime.utcnow() - timedelta(days=2)).strftime('%Y-%m-%d')
        assert recency_weight(two_days) == 0.9

    def test_five_days_ago(self):
        five_days = (datetime.utcnow() - timedelta(days=5)).strftime('%Y-%m-%d')
        assert recency_weight(five_days) == 0.7

    def test_twenty_days_ago(self):
        twenty = (datetime.utcnow() - timedelta(days=20)).strftime('%Y-%m-%d')
        assert recency_weight(twenty) == 0.5

    def test_sixty_days_ago(self):
        sixty = (datetime.utcnow() - timedelta(days=60)).strftime('%Y-%m-%d')
        assert recency_weight(sixty) == 0.3

    def test_old_date(self):
        assert recency_weight('2000-01-01') == 0.3

    def test_invalid_string(self):
        assert recency_weight('not-a-date') == 0.3

    def test_empty_string(self):
        assert recency_weight('') == 0.3

    def test_iso_with_z(self):
        today = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        assert recency_weight(today) == 1.0

    def test_iso_with_timezone(self):
        today = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S+00:00')
        assert recency_weight(today) == 1.0

    def test_bare_date_string(self):
        result = recency_weight('2026-04-12')
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_returns_float(self):
        result = recency_weight('2026-04-12')
        assert isinstance(result, float)

    def test_weight_in_range(self):
        result = recency_weight('2026-04-12')
        assert 0.0 <= result <= 1.0


class TestRecencyWeightBoundaries:
    """Test exact boundary conditions."""

    @patch('capability_spec.datetime')
    def test_zero_days(self, mock_dt):
        now = datetime(2026, 4, 14, 12, 0, 0)
        mock_dt.utcnow.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        assert recency_weight('2026-04-14T12:00:00') == 1.0

    @patch('capability_spec.datetime')
    def test_exactly_one_day(self, mock_dt):
        now = datetime(2026, 4, 14, 12, 0, 0)
        mock_dt.utcnow.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        assert recency_weight('2026-04-13T12:00:00') == 0.9

    @patch('capability_spec.datetime')
    def test_exactly_three_days(self, mock_dt):
        now = datetime(2026, 4, 14, 12, 0, 0)
        mock_dt.utcnow.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        assert recency_weight('2026-04-11T12:00:00') == 0.7

    @patch('capability_spec.datetime')
    def test_exactly_seven_days(self, mock_dt):
        now = datetime(2026, 4, 14, 12, 0, 0)
        mock_dt.utcnow.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        assert recency_weight('2026-04-07T12:00:00') == 0.5

    @patch('capability_spec.datetime')
    def test_exactly_thirty_days(self, mock_dt):
        now = datetime(2026, 4, 14, 12, 0, 0)
        mock_dt.utcnow.return_value = now
        mock_dt.fromisoformat = datetime.fromisoformat
        assert recency_weight('2026-03-15T12:00:00') == 0.3
