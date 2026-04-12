#!/usr/bin/env python3
"""
Fleet Discovery Crawler — scans CAPABILITY.toml files across the fleet.
"""
import json
import sys
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # Python < 3.11

GITHUB_TOKEN = open(Path.home() / ".bashrc").read()
for line in GITHUB_TOKEN.split("\n"):
    if "export GITHUB_TOKEN=" in line:
        GITHUB_TOKEN = line.split("=", 1)[1].strip().strip("'\"")
        break

ORG = "SuperInstance"
CAPABILITY_FILE = "CAPABILITY.toml"


def fetch_json(url):
    req = urllib.request.Request(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/json"
    })
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def fetch_toml(repo_full_name):
    """Fetch CAPABILITY.toml from a repo."""
    url = f"https://raw.githubusercontent.com/{repo_full_name}/main/{CAPABILITY_FILE}"
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return tomllib.loads(resp.read().decode())
    except:
        return None


def recency_weight(last_used: str) -> float:
    """Calculate recency weight from ISO date."""
    try:
        dt = datetime.fromisoformat(last_used.replace("Z", "+00:00")).replace(tzinfo=None)
        days = (datetime.utcnow() - dt).days
        if days < 1: return 1.0
        if days < 3: return 0.9
        if days < 7: return 0.7
        if days < 30: return 0.5
        return 0.3
    except:
        return 0.3


def scan_fleet():
    """Scan all repos for CAPABILITY.toml files."""
    print("🔍 Scanning fleet for CAPABILITY.toml files...")
    
    agents = []
    page = 1
    while True:
        repos = fetch_json(f"https://api.github.com/orgs/{ORG}/repos?per_page=100&page={page}")
        if not repos:
            break
        for repo in repos:
            cap = fetch_toml(repo["full_name"])
            if cap and "agent" in cap:
                agents.append(cap)
                name = cap["agent"].get("name", repo["name"])
                avatar = cap["agent"].get("avatar", "?")
                atype = cap["agent"].get("type", "unknown")
                status = cap["agent"].get("status", "unknown")
                print(f"  {avatar} {name:20} ({atype:12}) [{status}]")
        page += 1
        if page > 10: break  # safety limit

    return agents


def find_specialists(agents, capability: str, min_confidence: float = 0.5):
    """Find agents with a specific capability."""
    results = []
    for agent in agents:
        caps = agent.get("capabilities", {})
        cap = caps.get(capability)
        if cap and cap.get("confidence", 0) >= min_confidence:
            conf = cap["confidence"]
            rec = recency_weight(cap.get("last_used", "2000-01-01"))
            score = conf * rec
            results.append({
                "name": agent["agent"].get("name", "unknown"),
                "avatar": agent["agent"].get("avatar", "?"),
                "confidence": conf,
                "recency": rec,
                "score": score,
                "description": cap.get("description", ""),
                "home_repo": agent["agent"].get("home_repo", ""),
            })
    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def main():
    agents = scan_fleet()
    print(f"\n📊 Found {len(agents)} agents with capabilities")

    if len(agents) == 0:
        print("No agents found yet. Deploy CAPABILITY.toml to vessel repos.")
        return

    # Show all capabilities across fleet
    all_caps = {}
    for agent in agents:
        for cap_name, cap_data in agent.get("capabilities", {}).items():
            if cap_name not in all_caps:
                all_caps[cap_name] = []
            all_caps[cap_name].append({
                "agent": agent["agent"].get("name", "?"),
                "confidence": cap_data.get("confidence", 0),
            })

    print("\n🏆 Fleet Capability Map:")
    for cap_name, agents_list in sorted(all_caps.items()):
        agents_list.sort(key=lambda x: x["confidence"], reverse=True)
        top = agents_list[0]
        count = len(agents_list)
        print(f"  {cap_name:20} {count} agent(s) — best: {top['agent']} ({top['confidence']:.0%})")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Search mode: find specialists
        cap = sys.argv[1]
        min_conf = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
        agents = scan_fleet()
        results = find_specialists(agents, cap, min_conf)
        print(f"\n🎯 Specialists for '{cap}' (min confidence: {min_conf:.0%}):")
        for r in results:
            print(f"  {r['avatar']} {r['name']:15} conf={r['confidence']:.0%} score={r['score']:.2f}")
            print(f"     {r['description']}")
    else:
        main()
