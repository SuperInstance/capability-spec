"""Tests for A2A Agent Card adapter."""

import pytest
from capability_spec import to_a2a_agent_card


SAMPLE_DATA = {
    "agent": {
        "name": "Oracle1",
        "type": "lighthouse",
        "status": "active",
        "avatar": "🔮",
        "model": "z.ai/glm-5.1",
    },
    "capabilities": {
        "architecture": {"confidence": 0.95, "description": "System architecture"},
        "testing": {"confidence": 0.90, "description": "Test writing"},
    },
    "communication": {
        "bottles": True,
        "bottle_path": "for-oracle1/",
        "mud": True,
        "mud_home": "tavern",
        "issues": True,
        "pr_reviews": True,
    },
    "resources": {
        "compute": "oracle-cloud-arm64",
        "cpu_cores": 4,
        "ram_gb": 24,
        "languages": ["python", "typescript", "c", "go", "rust", "zig"],
    },
}


class TestA2AAgentCard:
    """Test to_a2a_agent_card conversion."""

    def test_returns_dict(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        assert isinstance(card, dict)

    def test_name_mapped(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        assert card["name"] == "Oracle1"

    def test_type_mapped(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        assert card["type"] == "lighthouse"

    def test_status_mapped(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        assert card["status"] == "active"

    def test_model_mapped(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        assert card["model"] == "z.ai/glm-5.1"

    def test_avatar_mapped(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        assert card["avatar"] == "🔮"

    def test_skills_count(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        assert len(card["skills"]) == 2

    def test_skill_structure(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        skill = card["skills"][0]
        assert "id" in skill
        assert "name" in skill
        assert "confidence" in skill
        assert "description" in skill

    def test_skill_confidence(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        arch = next(s for s in card["skills"] if s["id"] == "architecture")
        assert arch["confidence"] == 0.95

    def test_skill_name_titleized(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        arch = next(s for s in card["skills"] if s["id"] == "architecture")
        assert arch["name"] == "Architecture"

    def test_endpoints_count(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        # bottles, mud, issues, pr_reviews = 4
        assert len(card["endpoints"]) == 4

    def test_bottle_endpoint(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        bottle = next(e for e in card["endpoints"] if e["type"] == "bottle")
        assert bottle["path"] == "for-oracle1/"

    def test_mud_endpoint(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        mud = next(e for e in card["endpoints"] if e["type"] == "mud")
        assert mud["room"] == "tavern"

    def test_metadata_compute(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        assert card["metadata"]["compute"] == "oracle-cloud-arm64"

    def test_metadata_cpu_cores(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        assert card["metadata"]["cpu_cores"] == 4

    def test_metadata_ram_gb(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        assert card["metadata"]["ram_gb"] == 24

    def test_metadata_languages(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        assert len(card["metadata"]["languages"]) == 6

    def test_empty_data(self):
        card = to_a2a_agent_card({})
        assert card["name"] == ""
        assert card["skills"] == []
        assert card["endpoints"] == []

    def test_no_communication_endpoints_empty(self):
        data = {"agent": {"name": "Bot"}, "capabilities": {}, "resources": {}}
        card = to_a2a_agent_card(data)
        assert card["endpoints"] == []

    def test_bottles_false_no_endpoint(self):
        data = {"agent": {}, "communication": {"bottles": False}, "resources": {}}
        card = to_a2a_agent_card(data)
        bottle_eps = [e for e in card["endpoints"] if e["type"] == "bottle"]
        assert len(bottle_eps) == 0

    def test_card_keys(self):
        card = to_a2a_agent_card(SAMPLE_DATA)
        expected = {"name", "type", "status", "model", "avatar", "skills", "endpoints", "metadata"}
        assert set(card.keys()) == expected
