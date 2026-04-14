"""Tests for CAPABILITY.toml specification format compliance."""

import pytest
from capability_spec import parse_capability_toml, validate_capability


# Test all agent types from the spec
VALID_TYPES = ["lighthouse", "vessel", "scout", "quartermaster", "barnacle", "greenhorn"]
VALID_STATUSES = ["active", "idle", "hibernating", "decommissioned"]


def make_toml(agent_type="vessel", status="active", caps=None, comm=None):
    """Helper to generate CAPABILITY.toml strings for testing."""
    lines = [
        '[agent]',
        'name = "TestBot"',
        f'type = "{agent_type}"',
        f'status = "{status}"',
        'home_repo = "SuperInstance/test-vessel"',
    ]
    if caps:
        lines.append('[capabilities]')
        for name, conf in caps.items():
            lines.append(f'[capabilities.{name}]')
            lines.append(f'confidence = {conf}')
            lines.append(f'description = "{name} skill"')
    if comm:
        lines.append('[communication]')
        for k, v in comm.items():
            if isinstance(v, bool):
                lines.append(f'{k} = {"true" if v else "false"}')
            elif isinstance(v, str):
                lines.append(f'{k} = "{v}"')
    return '\n'.join(lines)


class TestSpecAgentTypes:
    """Test all valid agent types from CAPABILITY-SPEC.md."""

    @pytest.mark.parametrize("agent_type", VALID_TYPES)
    def test_all_agent_types_parse(self, agent_type):
        toml = make_toml(agent_type=agent_type)
        data = parse_capability_toml(toml)
        assert data["agent"]["type"] == agent_type

    @pytest.mark.parametrize("agent_type", VALID_TYPES)
    def test_all_agent_types_validate(self, agent_type):
        toml = make_toml(agent_type=agent_type)
        data = parse_capability_toml(toml)
        result = validate_capability(data)
        assert not any("type" in e for e in result.errors)


class TestSpecStatuses:
    """Test all valid status values."""

    @pytest.mark.parametrize("status", VALID_STATUSES)
    def test_all_statuses_parse(self, status):
        toml = make_toml(status=status)
        data = parse_capability_toml(toml)
        assert data["agent"]["status"] == status

    @pytest.mark.parametrize("status", VALID_STATUSES)
    def test_all_statuses_validate(self, status):
        toml = make_toml(status=status)
        data = parse_capability_toml(toml)
        result = validate_capability(data)
        assert not any("status" in e for e in result.errors)


class TestSpecCapabilitiesFormat:
    """Test capability format: skill, confidence (0-1), last_used, description."""

    def test_capability_with_all_fields(self):
        toml = make_toml(caps={"testing": 0.9})
        data = parse_capability_toml(toml)
        cap = data["capabilities"]["testing"]
        assert cap["confidence"] == 0.9
        assert "description" in cap

    def test_capability_confidence_at_zero(self):
        toml = make_toml(caps={"testing": 0.0})
        data = parse_capability_toml(toml)
        assert data["capabilities"]["testing"]["confidence"] == 0.0

    def test_capability_confidence_at_one(self):
        toml = make_toml(caps={"testing": 1.0})
        data = parse_capability_toml(toml)
        assert data["capabilities"]["testing"]["confidence"] == 1.0

    def test_multiple_capabilities(self):
        toml = make_toml(caps={"testing": 0.9, "research": 0.8, "coordination": 0.95})
        data = parse_capability_toml(toml)
        assert len(data["capabilities"]) == 3


class TestSpecCommunication:
    """Test communication section format."""

    def test_bottles_enabled(self):
        toml = make_toml(comm={"bottles": True, "bottle_path": "for-bot/"})
        data = parse_capability_toml(toml)
        assert data["communication"]["bottles"] is True

    def test_mud_enabled(self):
        toml = make_toml(comm={"mud": True, "mud_home": "tavern"})
        data = parse_capability_toml(toml)
        assert data["communication"]["mud"] is True

    def test_issues_enabled(self):
        toml = make_toml(comm={"issues": True})
        data = parse_capability_toml(toml)
        assert data["communication"]["issues"] is True


class TestSpecResources:
    """Test resources section format."""

    def test_resources_parse_from_toml(self):
        toml = """
[agent]
name = "Bot"
type = "vessel"
status = "active"

[resources]
compute = "cloud-arm64"
cpu_cores = 4
ram_gb = 24
storage_gb = 200
cuda = false
languages = ["python", "go"]
"""
        data = parse_capability_toml(toml)
        res = data["resources"]
        assert res["compute"] == "cloud-arm64"
        assert res["cpu_cores"] == 4
        assert res["ram_gb"] == 24
        assert res["cuda"] is False
        assert "python" in res["languages"]


class TestSpecConstraints:
    """Test constraints section format."""

    def test_constraints_parse_from_toml(self):
        toml = """
[agent]
name = "Bot"
type = "vessel"
status = "active"

[constraints]
max_task_duration = "4h"
requires_approval = ["email", "public_post"]
refuses = ["destructive_operations"]
budget_tokens_per_day = 500000
"""
        data = parse_capability_toml(toml)
        cons = data["constraints"]
        assert cons["max_task_duration"] == "4h"
        assert "email" in cons["requires_approval"]
        assert "destructive_operations" in cons["refuses"]
        assert cons["budget_tokens_per_day"] == 500000


class TestSpecAssociates:
    """Test associates section format."""

    def test_associates_parse_from_toml(self):
        toml = """
[agent]
name = "Bot"
type = "vessel"
status = "active"

[associates]
reports_to = "casey"
collaborates = ["agent1", "agent2"]
manages = ["agent3"]
trusts = { agent1 = 0.90, agent2 = 0.75 }
"""
        data = parse_capability_toml(toml)
        assoc = data["associates"]
        assert assoc["reports_to"] == "casey"
        assert "agent1" in assoc["collaborates"]
        assert assoc["trusts"]["agent1"] == 0.90


class TestOracle1CapabilityToml:
    """Integration test: parse and validate the actual CAPABILITY.toml in this repo."""

    def test_parse_actual_toml(self):
        from pathlib import Path
        toml_path = Path(__file__).parent.parent / "CAPABILITY.toml"
        if not toml_path.exists():
            pytest.skip("CAPABILITY.toml not found")
        from capability_spec import parse_capability_file
        data = parse_capability_file(str(toml_path))
        assert data["agent"]["name"] == "Oracle1"
        assert data["agent"]["type"] == "lighthouse"
        assert data["agent"]["status"] == "active"

    def test_validate_actual_toml(self):
        from pathlib import Path
        toml_path = Path(__file__).parent.parent / "CAPABILITY.toml"
        if not toml_path.exists():
            pytest.skip("CAPABILITY.toml not found")
        from capability_spec import parse_capability_file
        data = parse_capability_file(str(toml_path))
        result = validate_capability(data)
        assert result.ok, f"Validation failed: {result.errors}"

    def test_actual_toml_has_capabilities(self):
        from pathlib import Path
        toml_path = Path(__file__).parent.parent / "CAPABILITY.toml"
        if not toml_path.exists():
            pytest.skip("CAPABILITY.toml not found")
        from capability_spec import parse_capability_file
        data = parse_capability_file(str(toml_path))
        caps = data["capabilities"]
        assert len(caps) >= 5
        assert "architecture" in caps
        assert "testing" in caps

    def test_actual_toml_all_confidences_valid(self):
        from pathlib import Path
        toml_path = Path(__file__).parent.parent / "CAPABILITY.toml"
        if not toml_path.exists():
            pytest.skip("CAPABILITY.toml not found")
        from capability_spec import parse_capability_file
        data = parse_capability_file(str(toml_path))
        for name, cap in data["capabilities"].items():
            assert 0 <= cap["confidence"] <= 1, f"{name} has invalid confidence"
