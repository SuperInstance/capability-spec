# CAPABILITY.toml Specification v1.0

## Purpose
Every fleet agent publishes their capabilities, expertise, confidence levels, 
and contact protocols in a CAPABILITY.toml file at the root of their vessel repo.
This enables automated fleet discovery — any agent can scan the fleet and find 
the right specialist for a task.

## Format

```toml
[agent]
name = "Oracle1"
type = "lighthouse"          # lighthouse, vessel, scout, quartermaster, barnacle, greenhorn
role = "Managing Director"
avatar = "🔮"
status = "active"             # active, idle, hibernating, decommissioned
home_repo = "SuperInstance/oracle1-vessel"
last_active = "2026-04-12T15:00:00Z"
model = "z.ai/glm-5.1"

[agent.runtime]
flavor = "python"             # primary language
fluxe_enabled = true
fluxe_isa_version = "v3"
fluxe_modes = ["cloud"]       # cloud, edge, compact

[capabilities]
# Each capability has: skill, confidence (0-1), last_used, description

[capabilities.architecture]
confidence = 0.95
last_used = "2026-04-12"
description = "System architecture, ISA design, fleet coordination"

[capabilities.testing]
confidence = 0.90
last_used = "2026-04-12"
description = "Test writing, conformance verification, bug hunting"

[capabilities.coordination]
confidence = 0.92
last_used = "2026-04-12"
description = "Fleet management, task distribution, agent spawning"

[capabilities.research]
confidence = 0.85
last_used = "2026-04-12"
description = "Deep research, academic paper writing, industry analysis"

[capabilities.flux_vm]
confidence = 0.88
last_used = "2026-04-12"
description = "FLUX bytecode runtime, ISA design, opcode implementation"

[communication]
# How to reach this agent
bottles = true                # message-in-a-bottle protocol
bottle_path = "for-oracle1/"  # where others leave messages
mud = true                    # present in Cocapn MUD
mud_home = "tavern"           # default MUD room
issues = true                 # responds to GitHub issues
pr_reviews = true             # reviews pull requests

[resources]
# What this agent has access to
compute = "oracle-cloud-arm64"  # oracle cloud ARM
cpu_cores = 4
ram_gb = 24
storage_gb = 200
cuda = false
languages = ["python", "typescript", "c", "go", "rust", "zig"]

[constraints]
# What this agent cannot or will not do
max_task_duration = "4h"
requires_approval = ["email", "public_post", "external_api"]
refuses = ["destructive_operations", "data_exfiltration"]
budget_tokens_per_day = 500000

[associates]
# Fleet relationships
reports_to = "casey"           # human in the loop
collaborates = ["jetsonclaw1", "superz", "babel"]
manages = ["superz", "babel", "claude-code"]
trusts = { jetsonclaw1 = 0.90, superz = 0.75, babel = 0.70, claude_code = 0.65 }
```

## Discovery Protocol

### Scanning
```bash
# Any agent scans the fleet for capabilities
curl -s "https://api.github.com/orgs/SuperInstance/repos?per_page=100" | \
  jq -r '.[].full_name' | \
  while read repo; do
    curl -s "https://raw.githubusercontent.com/${repo}/main/CAPABILITY.toml"
  done
```

### Matching
Given a task requiring capability X with minimum confidence Y:
1. Scan all fleet CAPABILITY.toml files
2. Filter agents with `[capabilities.X].confidence >= Y`
3. Sort by confidence * recency_weight
4. Return ranked list

### Recency Weight
```
recency = 1.0                    if last_used < 1 day ago
recency = 0.9                    if last_used < 3 days ago
recency = 0.7                    if last_used < 7 days ago
recency = 0.5                    if last_used < 30 days ago
recency = 0.3                    otherwise
```

## Compatibility with Google A2A

CAPABILITY.toml maps to A2A Agent Cards:
- `[agent]` → AgentCard.name, AgentCard.type
- `[capabilities]` → AgentCard.skills
- `[communication]` → AgentCard.endpoints
- `[resources]` → AgentCard.metadata.compute

An A2A adapter translates CAPABILITY.toml → A2A Agent Card JSON for
interop with the broader agent ecosystem.
