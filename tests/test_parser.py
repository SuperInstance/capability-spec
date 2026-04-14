"""Tests for CAPABILITY.toml parsing."""

import pytest
from pathlib import Path
from capability_spec import (
    parse_capability_toml, parse_capability_file,
    CapabilityParseError,
)

SAMPLE_TOML = """
[agent]
name = "Oracle1"
type = "lighthouse"
role = "Managing Director"
avatar = "🔮"
status = "active"
home_repo = "SuperInstance/oracle1-vessel"
last_active = "2026-04-12T15:20:00Z"
model = "z.ai/glm-5.1"

[agent.runtime]
flavor = "python"
flux_enabled = true
flux_isa_version = "v3"
flux_modes = ["cloud"]

[capabilities]

[capabilities.architecture]
confidence = 0.95
last_used = "2026-04-12"
description = "System architecture, ISA design, fleet coordination"

[capabilities.testing]
confidence = 0.90
last_used = "2026-04-12"
description = "Test writing, conformance verification"

[communication]
bottles = true
bottle_path = "for-oracle1/"
mud = true
mud_home = "tavern"
issues = true
pr_reviews = true

[resources]
compute = "oracle-cloud-arm64"
cpu_cores = 4
ram_gb = 24
storage_gb = 200
cuda = false
languages = ["python", "typescript", "c", "go", "rust", "zig"]

[constraints]
max_task_duration = "4h"
requires_approval = ["email", "public_post", "external_api"]
refuses = ["destructive_operations", "data_exfiltration"]

[associates]
reports_to = "casey"
collaborates = ["jetsonclaw1", "superz", "babel"]
manages = ["superz", "babel", "claude-code"]
trusts = { jetsonclaw1 = 0.90, superz = 0.75, babel = 0.70, claude_code = 0.65 }
"""

MINIMAL_TOML = """
[agent]
name = "MinBot"
type = "vessel"
status = "active"
"""


class TestParseCapabilityToml:
    """Test parse_capability_toml function."""

    def test_parse_sample(self):
        data = parse_capability_toml(SAMPLE_TOML)
        assert data["agent"]["name"] == "Oracle1"
        assert data["agent"]["type"] == "lighthouse"
        assert data["agent"]["status"] == "active"

    def test_parse_minimal(self):
        data = parse_capability_toml(MINIMAL_TOML)
        assert data["agent"]["name"] == "MinBot"
        assert data["capabilities"] == {}
        assert data["communication"] == {}

    def test_parse_capabilities(self):
        data = parse_capability_toml(SAMPLE_TOML)
        caps = data["capabilities"]
        assert "architecture" in caps
        assert caps["architecture"]["confidence"] == 0.95
        assert caps["testing"]["confidence"] == 0.90

    def test_parse_communication(self):
        data = parse_capability_toml(SAMPLE_TOML)
        comm = data["communication"]
        assert comm["bottles"] is True
        assert comm["bottle_path"] == "for-oracle1/"
        assert comm["mud"] is True

    def test_parse_resources(self):
        data = parse_capability_toml(SAMPLE_TOML)
        res = data["resources"]
        assert res["cpu_cores"] == 4
        assert res["ram_gb"] == 24
        assert res["languages"] == ["python", "typescript", "c", "go", "rust", "zig"]

    def test_parse_constraints(self):
        data = parse_capability_toml(SAMPLE_TOML)
        cons = data["constraints"]
        assert "email" in cons["requires_approval"]
        assert "destructive_operations" in cons["refuses"]

    def test_parse_associates(self):
        data = parse_capability_toml(SAMPLE_TOML)
        assoc = data["associates"]
        assert assoc["reports_to"] == "casey"
        assert "jetsonclaw1" in assoc["collaborates"]
        assert assoc["trusts"]["superz"] == 0.75

    def test_parse_runtime(self):
        data = parse_capability_toml(SAMPLE_TOML)
        assert data["agent"]["runtime"]["flavor"] == "python"
        assert data["agent"]["runtime"]["flux_enabled"] is True

    def test_returns_dict(self):
        data = parse_capability_toml(SAMPLE_TOML)
        assert isinstance(data, dict)

    def test_all_sections_present(self):
        data = parse_capability_toml(SAMPLE_TOML)
        expected_keys = {"agent", "capabilities", "communication", "resources", "constraints", "associates"}
        assert expected_keys == set(data.keys())

    def test_invalid_toml_raises(self):
        with pytest.raises(CapabilityParseError):
            parse_capability_toml("this is not [valid toml")

    def test_empty_string_parses_as_empty(self):
        data = parse_capability_toml("")
        assert data == {"agent": {}, "capabilities": {}, "communication": {},
                        "resources": {}, "constraints": {}, "associates": {}}

    def test_garbage_raises(self):
        with pytest.raises(CapabilityParseError):
            parse_capability_toml("{{{{{")

    def test_partial_toml(self):
        data = parse_capability_toml("[agent]\nname = 'Bot'")
        assert data["agent"]["name"] == "Bot"


class TestParseCapabilityFile:
    """Test parse_capability_file function."""

    def test_parse_actual_file(self):
        toml_path = Path(__file__).parent.parent / "CAPABILITY.toml"
        if toml_path.exists():
            data = parse_capability_file(str(toml_path))
            assert "agent" in data
            assert data["agent"]["name"] == "Oracle1"

    def test_missing_file_raises(self):
        with pytest.raises(CapabilityParseError, match="File not found"):
            parse_capability_file("/nonexistent/CAPABILITY.toml")

    def test_parse_file_via_str(self, tmp_path):
        f = tmp_path / "CAP.toml"
        f.write_text(MINIMAL_TOML)
        data = parse_capability_file(str(f))
        assert data["agent"]["name"] == "MinBot"

    def test_parse_invalid_file(self, tmp_path):
        f = tmp_path / "BAD.toml"
        f.write_text("{{{invalid")
        with pytest.raises(CapabilityParseError):
            parse_capability_file(str(f))

    def test_parse_file_pathlib(self, tmp_path):
        f = tmp_path / "CAP.toml"
        f.write_text(MINIMAL_TOML)
        data = parse_capability_file(str(f))
        assert data["agent"]["type"] == "vessel"
