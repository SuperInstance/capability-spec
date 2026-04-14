"""Capability Specification Language — parse, validate, match CAPABILITY.toml files."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib


# ---------------------------------------------------------------------------
# Recency weight — as defined in CAPABILITY-SPEC.md
# ---------------------------------------------------------------------------

def recency_weight(last_used: str) -> float:
    """Calculate recency weight from ISO date string.

    Weight schedule:
      < 1 day  → 1.0
      < 3 days → 0.9
      < 7 days → 0.7
      < 30 days→ 0.5
      else     → 0.3
    """
    try:
        dt = datetime.fromisoformat(last_used.replace("Z", "+00:00")).replace(tzinfo=None)
        days = (datetime.utcnow() - dt).days
        if days < 1:
            return 1.0
        if days < 3:
            return 0.9
        if days < 7:
            return 0.7
        if days < 30:
            return 0.5
        return 0.3
    except Exception:
        return 0.3


# ---------------------------------------------------------------------------
# Capability Parser — reads and normalizes CAPABILITY.toml
# ---------------------------------------------------------------------------

class CapabilityParseError(Exception):
    """Raised when CAPABILITY.toml cannot be parsed or is invalid."""


def parse_capability_toml(text: str) -> dict:
    """Parse a CAPABILITY.toml string into a normalized dictionary.

    Returns a dict with keys: agent, capabilities, communication, resources,
    constraints, associates (each may be empty dict if section missing).
    """
    try:
        data = tomllib.loads(text)
    except Exception as e:
        raise CapabilityParseError(f"TOML parse error: {e}")

    return {
        "agent": data.get("agent", {}),
        "capabilities": data.get("capabilities", {}),
        "communication": data.get("communication", {}),
        "resources": data.get("resources", {}),
        "constraints": data.get("constraints", {}),
        "associates": data.get("associates", {}),
    }


def parse_capability_file(path: str) -> dict:
    """Parse a CAPABILITY.toml file from disk."""
    p = Path(path)
    if not p.exists():
        raise CapabilityParseError(f"File not found: {path}")
    return parse_capability_toml(p.read_text())


# ---------------------------------------------------------------------------
# Capability Validator — checks required fields and constraints
# ---------------------------------------------------------------------------

class ValidationResult:
    """Aggregates validation errors and warnings."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def __repr__(self):
        return f"ValidationResult(errors={len(self.errors)}, warnings={len(self.warnings)})"


VALID_AGENT_TYPES = {"lighthouse", "vessel", "scout", "quartermaster", "barnacle", "greenhorn"}
VALID_STATUSES = {"active", "idle", "hibernating", "decommissioned"}


def validate_capability(data: dict) -> ValidationResult:
    """Validate a parsed CAPABILITY.toml dict. Returns ValidationResult."""
    result = ValidationResult()
    agent = data.get("agent", {})

    # Required agent fields
    if not agent.get("name"):
        result.add_error("agent.name is required")
    if not agent.get("type"):
        result.add_error("agent.type is required")
    elif agent["type"] not in VALID_AGENT_TYPES:
        result.add_error(f"agent.type must be one of {VALID_AGENT_TYPES}, got '{agent['type']}'")
    if not agent.get("status"):
        result.add_error("agent.status is required")
    elif agent["status"] not in VALID_STATUSES:
        result.add_error(f"agent.status must be one of {VALID_STATUSES}, got '{agent['status']}'")

    # Validate capabilities
    caps = data.get("capabilities", {})
    for cap_name, cap_data in caps.items():
        if not isinstance(cap_data, dict):
            result.add_error(f"capabilities.{cap_name} must be a table")
            continue
        conf = cap_data.get("confidence")
        if conf is not None:
            if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
                result.add_error(f"capabilities.{cap_name}.confidence must be between 0 and 1, got {conf}")
        if not cap_data.get("description"):
            result.add_warning(f"capabilities.{cap_name} missing description")

    # Validate communication
    comm = data.get("communication", {})
    if not comm:
        result.add_warning("communication section is empty")
    if comm.get("bottles") and not comm.get("bottle_path"):
        result.add_warning("communication.bottles is true but bottle_path not set")

    # Validate resources
    res = data.get("resources", {})
    if res:
        for key in ("cpu_cores", "ram_gb", "storage_gb"):
            val = res.get(key)
            if val is not None and not isinstance(val, (int, float)) or (isinstance(val, (int, float)) and val < 0):
                result.add_error(f"resources.{key} must be a non-negative number, got {val}")

    # Validate constraints
    constraints = data.get("constraints", {})
    if constraints:
        if "requires_approval" in constraints:
            if not isinstance(constraints["requires_approval"], list):
                result.add_error("constraints.requires_approval must be a list")
        if "refuses" in constraints:
            if not isinstance(constraints["refuses"], list):
                result.add_error("constraints.refuses must be a list")
        if "budget_tokens_per_day" in constraints:
            b = constraints["budget_tokens_per_day"]
            if not isinstance(b, (int, float)) or b < 0:
                result.add_error(f"constraints.budget_tokens_per_day must be non-negative, got {b}")

    # Validate associates
    associates = data.get("associates", {})
    if associates:
        if "trusts" in associates:
            trusts = associates["trusts"]
            if not isinstance(trusts, dict):
                result.add_error("associates.trusts must be a table of name→float")
            else:
                for name, val in trusts.items():
                    if not isinstance(val, (int, float)) or not (0 <= val <= 1):
                        result.add_error(f"associates.trusts.{name} must be between 0 and 1, got {val}")

    return result


# ---------------------------------------------------------------------------
# Capability Matcher — find specialists for tasks
# ---------------------------------------------------------------------------

def match_specialists(agents: list[dict], capability: str, min_confidence: float = 0.5) -> list[dict]:
    """Find agents matching a capability requirement.

    Args:
        agents: List of parsed CAPABILITY.toml dicts.
        capability: Capability name to match.
        min_confidence: Minimum confidence threshold (0-1).

    Returns:
        List of results sorted by score (confidence * recency_weight).
    """
    results = []
    for agent in agents:
        caps = agent.get("capabilities", {})
        cap = caps.get(capability)
        if cap and cap.get("confidence", 0) >= min_confidence:
            conf = cap.get("confidence", 0)
            rec = recency_weight(cap.get("last_used", "2000-01-01"))
            score = conf * rec
            results.append({
                "name": agent["agent"].get("name", "unknown"),
                "type": agent["agent"].get("type", "unknown"),
                "avatar": agent["agent"].get("avatar", "?"),
                "confidence": conf,
                "recency": rec,
                "score": score,
                "description": cap.get("description", ""),
                "home_repo": agent["agent"].get("home_repo", ""),
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def build_capability_map(agents: list[dict]) -> dict[str, list[dict]]:
    """Build a fleet-wide capability map.

    Returns dict mapping capability names to list of {agent, confidence}.
    """
    cap_map: dict[str, list[dict]] = {}
    for agent in agents:
        for cap_name, cap_data in agent.get("capabilities", {}).items():
            if cap_name not in cap_map:
                cap_map[cap_name] = []
            cap_map[cap_name].append({
                "agent": agent["agent"].get("name", "?"),
                "confidence": cap_data.get("confidence", 0),
            })
    # Sort each capability's agents by confidence descending
    for cap_name in cap_map:
        cap_map[cap_name].sort(key=lambda x: x["confidence"], reverse=True)
    return cap_map


# ---------------------------------------------------------------------------
# A2A Adapter — translate CAPABILITY.toml to Google A2A Agent Card
# ---------------------------------------------------------------------------

def to_a2a_agent_card(data: dict) -> dict:
    """Convert a parsed CAPABILITY.toml dict to an A2A Agent Card.

    Mapping:
      [agent] → name, type
      [capabilities] → skills
      [communication] → endpoints
      [resources] → metadata
    """
    agent = data.get("agent", {})
    caps = data.get("capabilities", {})
    comm = data.get("communication", {})
    resources = data.get("resources", {})

    skills = []
    for cap_name, cap_data in caps.items():
        skills.append({
            "id": cap_name,
            "name": cap_name.replace("_", " ").title(),
            "confidence": cap_data.get("confidence", 0),
            "description": cap_data.get("description", ""),
        })

    endpoints = []
    if comm.get("bottles"):
        endpoints.append({"type": "bottle", "path": comm.get("bottle_path", "")})
    if comm.get("mud"):
        endpoints.append({"type": "mud", "room": comm.get("mud_home", "")})
    if comm.get("issues"):
        endpoints.append({"type": "github-issues"})
    if comm.get("pr_reviews"):
        endpoints.append({"type": "github-pr-reviews"})

    return {
        "name": agent.get("name", ""),
        "type": agent.get("type", ""),
        "status": agent.get("status", ""),
        "model": agent.get("model", ""),
        "avatar": agent.get("avatar", ""),
        "skills": skills,
        "endpoints": endpoints,
        "metadata": {
            "compute": resources.get("compute", ""),
            "cpu_cores": resources.get("cpu_cores"),
            "ram_gb": resources.get("ram_gb"),
            "languages": resources.get("languages", []),
        },
    }
