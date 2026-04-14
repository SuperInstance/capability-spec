"""Tests for CAPABILITY.toml validation."""

import pytest
from capability_spec import validate_capability, ValidationResult


SAMPLE_VALID = {
    "agent": {"name": "Oracle1", "type": "lighthouse", "status": "active",
              "role": "MD", "avatar": "🔮", "home_repo": "SuperInstance/oracle1-vessel"},
    "capabilities": {
        "architecture": {"confidence": 0.95, "last_used": "2026-04-12",
                         "description": "System architecture"},
        "testing": {"confidence": 0.90, "last_used": "2026-04-12",
                    "description": "Test writing"},
    },
    "communication": {"bottles": True, "bottle_path": "for-oracle1/"},
    "resources": {"cpu_cores": 4, "ram_gb": 24, "storage_gb": 200},
    "constraints": {"requires_approval": ["email"], "refuses": ["evil"],
                    "budget_tokens_per_day": 500000},
    "associates": {"trusts": {"friend": 0.8}},
}


class TestValidationResult:
    """Test ValidationResult class."""

    def test_initial_state(self):
        r = ValidationResult()
        assert r.ok is True
        assert r.errors == []
        assert r.warnings == []

    def test_add_error(self):
        r = ValidationResult()
        r.add_error("bad thing")
        assert r.ok is False
        assert len(r.errors) == 1

    def test_add_warning(self):
        r = ValidationResult()
        r.add_warning("heads up")
        assert r.ok is True  # warnings don't affect ok
        assert len(r.warnings) == 1

    def test_repr(self):
        r = ValidationResult()
        r.add_error("e")
        r.add_warning("w")
        assert "errors=1" in repr(r)
        assert "warnings=1" in repr(r)


class TestValidateAgent:
    """Test agent section validation."""

    def test_valid_agent(self):
        result = validate_capability(SAMPLE_VALID)
        agent_errors = [e for e in result.errors if "agent" in e]
        assert len(agent_errors) == 0

    def test_missing_name(self):
        data = {"agent": {"type": "lighthouse", "status": "active"}}
        result = validate_capability(data)
        assert any("agent.name" in e for e in result.errors)

    def test_missing_type(self):
        data = {"agent": {"name": "Bot", "status": "active"}}
        result = validate_capability(data)
        assert any("agent.type" in e for e in result.errors)

    def test_invalid_type(self):
        data = {"agent": {"name": "Bot", "type": "spaceship", "status": "active"}}
        result = validate_capability(data)
        assert any("spaceship" in e for e in result.errors)

    def test_valid_types(self):
        for t in ["lighthouse", "vessel", "scout", "quartermaster", "barnacle", "greenhorn"]:
            data = {"agent": {"name": "Bot", "type": t, "status": "active"}}
            result = validate_capability(data)
            assert not any("agent.type" in e for e in result.errors), f"Type {t} should be valid"

    def test_missing_status(self):
        data = {"agent": {"name": "Bot", "type": "vessel"}}
        result = validate_capability(data)
        assert any("agent.status" in e for e in result.errors)

    def test_invalid_status(self):
        data = {"agent": {"name": "Bot", "type": "vessel", "status": "dead"}}
        result = validate_capability(data)
        assert any("dead" in e for e in result.errors)

    def test_valid_statuses(self):
        for s in ["active", "idle", "hibernating", "decommissioned"]:
            data = {"agent": {"name": "Bot", "type": "vessel", "status": s}}
            result = validate_capability(data)
            assert not any("agent.status" in e for e in result.errors)


class TestValidateCapabilities:
    """Test capabilities section validation."""

    def test_valid_capabilities(self):
        result = validate_capability(SAMPLE_VALID)
        cap_errors = [e for e in result.errors if "capabilities" in e]
        assert len(cap_errors) == 0

    def test_confidence_out_of_range_high(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "capabilities": {"test": {"confidence": 1.5}}}
        result = validate_capability(data)
        assert any("confidence" in e for e in result.errors)

    def test_confidence_out_of_range_negative(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "capabilities": {"test": {"confidence": -0.5}}}
        result = validate_capability(data)
        assert any("confidence" in e for e in result.errors)

    def test_confidence_boundary_zero(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "capabilities": {"test": {"confidence": 0}}}
        result = validate_capability(data)
        assert not any("confidence" in e for e in result.errors)

    def test_confidence_boundary_one(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "capabilities": {"test": {"confidence": 1.0}}}
        result = validate_capability(data)
        assert not any("confidence" in e for e in result.errors)

    def test_missing_description_warns(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "capabilities": {"test": {"confidence": 0.5}}}
        result = validate_capability(data)
        assert any("description" in w for w in result.warnings)

    def test_non_table_capability_errors(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "capabilities": {"test": "not a table"}}
        result = validate_capability(data)
        assert any("must be a table" in e for e in result.errors)

    def test_empty_capabilities_ok(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "capabilities": {}}
        result = validate_capability(data)
        assert result.ok


class TestValidateCommunication:
    """Test communication section validation."""

    def test_valid_communication(self):
        result = validate_capability(SAMPLE_VALID)
        comm_errors = [e for e in result.errors if "communication" in e]
        assert len(comm_errors) == 0

    def test_empty_communication_warns(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "communication": {}}
        result = validate_capability(data)
        assert any("communication" in w for w in result.warnings)

    def test_bottles_without_path_warns(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "communication": {"bottles": True}}
        result = validate_capability(data)
        assert any("bottle_path" in w for w in result.warnings)


class TestValidateResources:
    """Test resources section validation."""

    def test_valid_resources(self):
        result = validate_capability(SAMPLE_VALID)
        res_errors = [e for e in result.errors if "resources" in e]
        assert len(res_errors) == 0

    def test_negative_cpu_cores(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "resources": {"cpu_cores": -1}}
        result = validate_capability(data)
        assert any("cpu_cores" in e for e in result.errors)

    def test_zero_resources_ok(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "resources": {"cpu_cores": 0, "ram_gb": 0, "storage_gb": 0}}
        result = validate_capability(data)
        assert not any("resources" in e for e in result.errors)


class TestValidateConstraints:
    """Test constraints section validation."""

    def test_valid_constraints(self):
        result = validate_capability(SAMPLE_VALID)
        cons_errors = [e for e in result.errors if "constraints" in e]
        assert len(cons_errors) == 0

    def test_requires_approval_not_list(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "constraints": {"requires_approval": "email"}}
        result = validate_capability(data)
        assert any("requires_approval" in e for e in result.errors)

    def test_refuses_not_list(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "constraints": {"refuses": "evil"}}
        result = validate_capability(data)
        assert any("refuses" in e for e in result.errors)

    def test_negative_budget(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "constraints": {"budget_tokens_per_day": -100}}
        result = validate_capability(data)
        assert any("budget" in e for e in result.errors)

    def test_zero_budget_ok(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "constraints": {"budget_tokens_per_day": 0}}
        result = validate_capability(data)
        assert not any("budget" in e for e in result.errors)


class TestValidateAssociates:
    """Test associates section validation."""

    def test_valid_associates(self):
        result = validate_capability(SAMPLE_VALID)
        assoc_errors = [e for e in result.errors if "associates" in e]
        assert len(assoc_errors) == 0

    def test_trusts_not_table(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "associates": {"trusts": "not a table"}}
        result = validate_capability(data)
        assert any("trusts" in e for e in result.errors)

    def test_trusts_out_of_range(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "associates": {"trusts": {"friend": 1.5}}}
        result = validate_capability(data)
        assert any("friend" in e for e in result.errors)

    def test_trusts_zero_ok(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "associates": {"trusts": {"friend": 0}}}
        result = validate_capability(data)
        assert not any("trusts" in e for e in result.errors)

    def test_trusts_one_ok(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "associates": {"trusts": {"friend": 1.0}}}
        result = validate_capability(data)
        assert not any("trusts" in e for e in result.errors)

    def test_trusts_negative(self):
        data = {"agent": {"name": "B", "type": "vessel", "status": "active"},
                "associates": {"trusts": {"friend": -0.5}}}
        result = validate_capability(data)
        assert any("friend" in e for e in result.errors)
