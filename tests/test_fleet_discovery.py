"""Tests for fleet_discovery.py module (mocked network calls)."""

import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

VALID_CAP_TOML = """
[agent]
name = "TestAgent"
type = "vessel"
status = "active"
avatar = "🚢"
home_repo = "SuperInstance/test-vessel"

[capabilities]

[capabilities.testing]
confidence = 0.85
last_used = "2026-04-12"
description = "Test writing"
"""

BASHRC_PATH = Path.home() / ".bashrc"
_BASHRC_BACKUP = None


def _ensure_bashrc_with_token():
    global _BASHRC_BACKUP
    token_line = 'export GITHUB_TOKEN=fake_test_token_xyz\n'
    if BASHRC_PATH.exists():
        _BASHRC_BACKUP = BASHRC_PATH.read_text()
        if 'export GITHUB_TOKEN=' in _BASHRC_BACKUP:
            return
        BASHRC_PATH.write_text(_BASHRC_BACKUP + '\n' + token_line)
    else:
        _BASHRC_BACKUP = None
        BASHRC_PATH.write_text(token_line)


def _restore_bashrc():
    if _BASHRC_BACKUP is not None:
        BASHRC_PATH.write_text(_BASHRC_BACKUP)
    else:
        try:
            BASHRC_PATH.unlink()
        except OSError:
            pass


@pytest.fixture(autouse=True, scope="module")
def setup_bashrc():
    _ensure_bashrc_with_token()
    if 'fleet_discovery' in sys.modules:
        del sys.modules['fleet_discovery']
    yield
    _restore_bashrc()


def _get_module():
    if 'fleet_discovery' in sys.modules:
        return sys.modules['fleet_discovery']
    import fleet_discovery
    return fleet_discovery


class TestFleetDiscoveryImports:
    def test_import_succeeds(self):
        mod = _get_module()
        assert hasattr(mod, 'recency_weight')
        assert hasattr(mod, 'scan_fleet')
        assert hasattr(mod, 'find_specialists')

    def test_recency_weight_function_exists(self):
        assert callable(_get_module().recency_weight)

    def test_recency_weight_returns_float(self):
        assert isinstance(_get_module().recency_weight('2026-04-12'), float)

    def test_github_token_set(self):
        mod = _get_module()
        assert hasattr(mod, 'GITHUB_TOKEN')
        assert mod.GITHUB_TOKEN == 'fake_test_token_xyz'

    def test_recency_weight_matches_spec(self):
        mod = _get_module()
        from capability_spec import recency_weight
        assert mod.recency_weight('2026-04-12') == recency_weight('2026-04-12')


class TestFetchJson:
    @patch('fleet_discovery.urllib.request.urlopen')
    def test_fetch_json_returns_data(self, mock_urlopen):
        mod = _get_module()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps([{"name": "test"}]).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        assert mod.fetch_json("https://api.github.com/test") == [{"name": "test"}]

    @patch('fleet_discovery.urllib.request.urlopen')
    def test_fetch_json_passes_auth_header(self, mock_urlopen):
        mod = _get_module()
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'[]'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        mod.fetch_json("https://api.github.com/test")
        call_args = mock_urlopen.call_args[0][0]
        assert "token fake_test_token_xyz" in call_args.headers.get("Authorization", "")


class TestFetchToml:
    @patch('fleet_discovery.urllib.request.urlopen')
    def test_fetch_toml_returns_parsed(self, mock_urlopen):
        mod = _get_module()
        mock_resp = MagicMock()
        mock_resp.read.return_value = VALID_CAP_TOML.encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = mod.fetch_toml("SuperInstance/test-vessel")
        assert result is not None
        assert result["agent"]["name"] == "TestAgent"

    @patch('fleet_discovery.urllib.request.urlopen')
    def test_fetch_toml_404_returns_none(self, mock_urlopen):
        mod = _get_module()
        mock_urlopen.side_effect = Exception("404")
        assert mod.fetch_toml("SuperInstance/nonexistent") is None


class TestScanFleet:
    @patch('fleet_discovery.fetch_toml')
    @patch('fleet_discovery.fetch_json')
    def test_scan_returns_agents(self, mock_fetch_json, mock_fetch_toml):
        mod = _get_module()
        mock_fetch_json.side_effect = [
            [{"full_name": "SuperInstance/agent1", "name": "agent1"},
             {"full_name": "SuperInstance/lib1", "name": "lib1"}],
            [],
        ]
        mock_fetch_toml.side_effect = lambda name: {
            "agent": {"name": "A1", "type": "vessel", "status": "active"}
        } if "agent" in name else None

        with patch('builtins.print'):
            agents = mod.scan_fleet()
        assert len(agents) == 1
        assert agents[0]["agent"]["name"] == "A1"

    @patch('fleet_discovery.fetch_json')
    def test_scan_empty_org(self, mock_fetch_json):
        mod = _get_module()
        mock_fetch_json.return_value = []
        with patch('builtins.print'):
            agents = mod.scan_fleet()
        assert agents == []

    @patch('fleet_discovery.fetch_toml')
    @patch('fleet_discovery.fetch_json')
    def test_scan_multiple_pages(self, mock_fetch_json, mock_fetch_toml):
        mod = _get_module()
        mock_fetch_json.side_effect = [
            [{"full_name": "SuperInstance/a1", "name": "a1"},
             {"full_name": "SuperInstance/a2", "name": "a2"}],
            [],
        ]
        mock_fetch_toml.return_value = {"agent": {"name": "X", "type": "vessel", "status": "active"}}

        with patch('builtins.print'):
            agents = mod.scan_fleet()
        assert len(agents) == 2


class TestFindSpecialists:
    def test_find_in_mock_agents(self):
        mod = _get_module()
        agents = [{
            "agent": {"name": "TestBot", "type": "vessel", "avatar": "🤖", "home_repo": "test/repo"},
            "capabilities": {"testing": {"confidence": 0.9, "last_used": "2026-04-12"}}
        }]
        results = mod.find_specialists(agents, "testing")
        assert len(results) == 1
        assert results[0]["name"] == "TestBot"

    def test_find_no_match(self):
        mod = _get_module()
        agents = [{
            "agent": {"name": "TestBot", "type": "vessel", "avatar": "🤖", "home_repo": "test/repo"},
            "capabilities": {"testing": {"confidence": 0.9, "last_used": "2026-04-12"}}
        }]
        assert mod.find_specialists(agents, "nonexistent") == []

    def test_find_specialists_sorted(self):
        mod = _get_module()
        agents = [
            {"agent": {"name": "Low", "type": "vessel", "avatar": "?", "home_repo": "t/r"},
             "capabilities": {"testing": {"confidence": 0.5, "last_used": "2026-04-12"}}},
            {"agent": {"name": "High", "type": "vessel", "avatar": "?", "home_repo": "t/r"},
             "capabilities": {"testing": {"confidence": 0.95, "last_used": "2026-04-12"}}},
        ]
        results = mod.find_specialists(agents, "testing")
        assert results[0]["name"] == "High"

    def test_find_specialists_result_keys(self):
        mod = _get_module()
        agents = [{
            "agent": {"name": "B", "type": "vessel", "avatar": "🤖", "home_repo": "t/r"},
            "capabilities": {"testing": {"confidence": 0.8, "last_used": "2026-04-12"}}
        }]
        r = mod.find_specialists(agents, "testing")[0]
        assert "name" in r and "confidence" in r and "score" in r

    def test_find_specialists_matches_capability_spec(self):
        mod = _get_module()
        from capability_spec import match_specialists
        agents = [
            {"agent": {"name": "B1", "type": "vessel", "avatar": "?", "home_repo": "t/r"},
             "capabilities": {"testing": {"confidence": 0.9, "last_used": "2026-04-12"}}},
            {"agent": {"name": "B2", "type": "scout", "avatar": "?", "home_repo": "t/r"},
             "capabilities": {"testing": {"confidence": 0.7, "last_used": "2026-04-10"}}},
        ]
        fd = mod.find_specialists(agents, "testing")
        cs = match_specialists(agents, "testing")
        assert len(fd) == len(cs)
        for f, c in zip(fd, cs):
            assert f["name"] == c["name"] and f["score"] == c["score"]
