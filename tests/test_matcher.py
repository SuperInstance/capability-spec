"""Tests for capability matching and specialist finding."""

import pytest
from capability_spec import match_specialists, build_capability_map


AGENT_ORACLE = {
    "agent": {"name": "Oracle1", "type": "lighthouse", "status": "active",
              "avatar": "🔮", "home_repo": "SuperInstance/oracle1-vessel"},
    "capabilities": {
        "architecture": {"confidence": 0.95, "last_used": "2026-04-12",
                         "description": "System architecture"},
        "testing": {"confidence": 0.90, "last_used": "2026-04-12",
                    "description": "Test writing"},
        "coordination": {"confidence": 0.92, "last_used": "2026-04-12",
                         "description": "Fleet management"},
    },
}

AGENT_SCOUT = {
    "agent": {"name": "Scout1", "type": "scout", "status": "active",
              "avatar": "🔭", "home_repo": "SuperInstance/scout1-vessel"},
    "capabilities": {
        "testing": {"confidence": 0.85, "last_used": "2026-04-10",
                    "description": "Quick tests"},
        "research": {"confidence": 0.80, "last_used": "2026-04-08",
                     "description": "Deep research"},
    },
}

AGENT_GREENHORN = {
    "agent": {"name": "Greenhorn1", "type": "greenhorn", "status": "active",
              "avatar": "🌱", "home_repo": "SuperInstance/greenhorn1-vessel"},
    "capabilities": {
        "testing": {"confidence": 0.50, "last_used": "2026-04-01",
                    "description": "Basic tests"},
    },
}


class TestMatchSpecialists:
    """Test match_specialists function."""

    def test_find_architecture_specialist(self):
        agents = [AGENT_ORACLE, AGENT_SCOUT]
        results = match_specialists(agents, "architecture")
        assert len(results) == 1
        assert results[0]["name"] == "Oracle1"

    def test_find_testing_specialists(self):
        agents = [AGENT_ORACLE, AGENT_SCOUT, AGENT_GREENHORN]
        results = match_specialists(agents, "testing")
        assert len(results) == 3
        # Oracle should be first (highest score)
        assert results[0]["name"] == "Oracle1"

    def test_no_match_returns_empty(self):
        agents = [AGENT_ORACLE]
        results = match_specialists(agents, "nonexistent_capability")
        assert results == []

    def test_min_confidence_filters(self):
        agents = [AGENT_ORACLE, AGENT_SCOUT, AGENT_GREENHORN]
        results = match_specialists(agents, "testing", min_confidence=0.9)
        assert len(results) == 1
        assert results[0]["name"] == "Oracle1"

    def test_min_confidence_all_pass(self):
        agents = [AGENT_ORACLE, AGENT_SCOUT, AGENT_GREENHORN]
        results = match_specialists(agents, "testing", min_confidence=0.0)
        assert len(results) == 3

    def test_min_confidence_none_pass(self):
        agents = [AGENT_ORACLE]
        results = match_specialists(agents, "architecture", min_confidence=1.0)
        assert results == []

    def test_results_sorted_by_score(self):
        agents = [AGENT_SCOUT, AGENT_ORACLE]
        results = match_specialists(agents, "testing")
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_result_structure(self):
        agents = [AGENT_ORACLE]
        results = match_specialists(agents, "architecture")
        r = results[0]
        assert "name" in r
        assert "type" in r
        assert "avatar" in r
        assert "confidence" in r
        assert "recency" in r
        assert "score" in r
        assert "description" in r
        assert "home_repo" in r

    def test_empty_agents_list(self):
        results = match_specialists([], "testing")
        assert results == []

    def test_agent_without_capabilities(self):
        agents = [{"agent": {"name": "Empty", "type": "vessel", "status": "active"}}]
        results = match_specialists(agents, "testing")
        assert results == []

    def test_capability_without_confidence(self):
        agents = [{"agent": {"name": "Bot", "type": "vessel", "status": "active"},
                    "capabilities": {"test": {"description": "testing"}}}]
        results = match_specialists(agents, "test", min_confidence=0.0)
        # confidence defaults to 0, min_confidence=0.0, so 0 >= 0.0 should match
        assert len(results) == 1

    def test_score_calculation(self):
        agents = [AGENT_ORACLE]
        results = match_specialists(agents, "architecture")
        r = results[0]
        # confidence=0.95, last_used=2026-04-12 (recent), recency ~= 0.3-1.0
        assert r["confidence"] == 0.95
        assert r["score"] == pytest.approx(0.95 * r["recency"])

    def test_recency_affects_ranking(self):
        agents = [AGENT_ORACLE, AGENT_SCOUT]
        results = match_specialists(agents, "testing")
        # Oracle has higher confidence (0.90 vs 0.85)
        assert results[0]["name"] == "Oracle1"

    def test_description_in_result(self):
        agents = [AGENT_ORACLE]
        results = match_specialists(agents, "architecture")
        assert "System architecture" in results[0]["description"]

    def test_home_repo_in_result(self):
        agents = [AGENT_ORACLE]
        results = match_specialists(agents, "architecture")
        assert "oracle1-vessel" in results[0]["home_repo"]


class TestBuildCapabilityMap:
    """Test build_capability_map function."""

    def test_empty_agents(self):
        result = build_capability_map([])
        assert result == {}

    def test_single_agent(self):
        result = build_capability_map([AGENT_ORACLE])
        assert "architecture" in result
        assert "testing" in result
        assert "coordination" in result

    def test_multiple_agents(self):
        result = build_capability_map([AGENT_ORACLE, AGENT_SCOUT])
        assert "research" in result  # from Scout
        assert "architecture" in result  # from Oracle

    def test_capability_has_agents(self):
        result = build_capability_map([AGENT_ORACLE, AGENT_SCOUT, AGENT_GREENHORN])
        testing = result["testing"]
        assert len(testing) == 3
        names = [a["agent"] for a in testing]
        assert "Oracle1" in names
        assert "Scout1" in names
        assert "Greenhorn1" in names

    def test_sorted_by_confidence(self):
        result = build_capability_map([AGENT_ORACLE, AGENT_SCOUT, AGENT_GREENHORN])
        testing = result["testing"]
        confs = [a["confidence"] for a in testing]
        assert confs == sorted(confs, reverse=True)

    def test_returns_dict_of_lists(self):
        result = build_capability_map([AGENT_ORACLE])
        for key, val in result.items():
            assert isinstance(val, list)

    def test_agent_structure(self):
        result = build_capability_map([AGENT_ORACLE])
        arch = result["architecture"][0]
        assert "agent" in arch
        assert "confidence" in arch
