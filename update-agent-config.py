#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

SERVICES_PORTS = {
    "lmstudio": 1234,
    "ollama": 11434,
    "llama.cpp": 8080,
    "llama": 8080,
    "vllm": 8000,
    "litellm": 4000,
}

AGENTS = {
    "opencode": {
        "path": "~/.config/opencode/opencode.json",
        "generate": lambda url, models, service, hostname: {
            f"{service}@{hostname}": {
                "npm": "@ai-sdk/openai-compatible",
                "name": f"{service}@{hostname}",
                "options": {"baseURL": url, "apiKey": "sk-local"},
                "models": {m: {} for m in models},
            }
        },
        "merge": lambda existing, new: {
            "provider": {**existing.get("provider", {}), **new}
        },
    },
    "pi": {
        "path": "~/.pi/agent/models.json",
        "generate": lambda url, models, service, hostname: {
            "providers": {
                f"{service}@{hostname}": {
                    "baseUrl": url,
                    "api": "openai-completions",
                    "apiKey": "none",
                    "models": [{"id": m} for m in models],
                }
            }
        },
        "merge": lambda existing, new: {
            "providers": {**existing.get("providers", {}), **new.get("providers", {})}
        },
    },
}

CONFIG_SEARCH_PATHS = [
    Path(__file__).parent / "config.json",
    Path(os.path.expanduser("~")) / ".config" / "update-agent-config" / "config.json",
    Path(os.path.expanduser("~")) / ".update-agent-config.json",
]


def expand_path(path: str) -> Path:
    return Path(os.path.expanduser(path))


def parse_service_spec(service_spec: str) -> tuple[str, str, int]:
    if ":" in service_spec:
        location, port_str = service_spec.rsplit(":", 1)
        port = int(port_str)
    else:
        location = service_spec
        port = None

    if "@" in location:
        service, hostname = location.split("@", 1)
    else:
        service = location
        hostname = "localhost"

    service = service or "custom"
    service = service.lower()
    port = port or SERVICES_PORTS.get(service, 8080)
    return service, hostname, port


def fetch_models(hostname: str, port: int) -> list[str] | None:
    url = f"http://{hostname}:{port}/v1/models"
    try:
        with urllib.request.urlopen(url) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return None

    models = data.get("data") or data.get("models") or []
    return sorted({m["id"] for m in models})


def generate_config(
    agent: str, url: str, models: list[str], service: str, hostname: str
) -> dict:
    return AGENTS[agent]["generate"](url, models, service, hostname)


def merge_config(agent: str, existing: dict, new: dict) -> dict:
    return AGENTS[agent]["merge"](existing, new)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config")
    args = parser.parse_args()

    config_file = args.config
    if not config_file:
        config_file = next((p for p in CONFIG_SEARCH_PATHS if p.exists()), None)

    if not config_file or not Path(config_file).exists():
        print("Error: Config file not found", file=sys.stderr)
        return 1

    with open(config_file) as f:
        config = json.load(f)

    unknown_agents = [a for a in config.get("agents", []) if a not in AGENTS]
    if unknown_agents:
        print(f"Error: Unknown agents: {', '.join(unknown_agents)}", file=sys.stderr)
        print(f"Valid agents: {', '.join(AGENTS)}", file=sys.stderr)
        return 1

    if "agents" not in config:
        print("Error: 'agents' key is required in config", file=sys.stderr)
        return 1

    if "services" not in config:
        print("Error: 'services' key is required in config", file=sys.stderr)
        return 1

    agent_list = config["agents"]
    service_list = config["services"]

    print("Fetching models...\n")
    updates = {}

    for service_spec in service_list:
        service, hostname, port = parse_service_spec(service_spec)
        url = f"http://{hostname}:{port}/v1"

        models = fetch_models(hostname, port)
        if models is None:
            continue

        service_key = f"{service}@{hostname}" if hostname != "localhost" else service
        print(f"Models found in {service_key} ({len(models)}):")
        for m in models[:10]:
            print(f"  - {m}")
        if len(models) > 10:
            print(f"  ... and {len(models) - 10} more")
        print()

        for agent in agent_list:
            agent_config = AGENTS[agent]
            path = expand_path(agent_config["path"])
            out = generate_config(agent, url, models, service, hostname)

            updates.setdefault(agent, path)
            path.parent.mkdir(parents=True, exist_ok=True)

            existing = {}
            if path.exists():
                content = path.read_text()
                if content.strip():
                    existing = json.loads(content)
            merged = merge_config(agent, existing, out)

            with open(path, "w") as f:
                json.dump(merged, f, indent=2, separators=(",", ": "))
                f.write("\n")

    home = str(expand_path("~"))
    max_len = max(len(a) for a in updates) if updates else 0
    print("Updated:")
    for agent, path in updates.items():
        print(
            f"  - {agent.ljust(max_len)}   {path}".replace(home, "~").replace("\\", "/")
        )


if __name__ == "__main__":
    exit(main() or 0)
