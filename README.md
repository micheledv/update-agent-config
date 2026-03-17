# Update Agent Config

Update local AI model configurations for various agents.

## Usage

```bash
./update-agent-config.py
# or
python update-agent-config.py
```

The script reads `config.json` from one of these locations:
1. `./config.json` (current directory)
2. `$XDG_CONFIG_HOME/update-agent-config/config.json`
3. `~/.update-agent-config.json`

## Configuration

Create a `config.json` file:

```json
{
    "agents": ["opencode", "pi"],
    "services": ["lmstudio", "ollama@localhost:11434"]
}
```

### Fields

- `agents`: List of agents to update (default: `["opencode"]`)
- `services`: List of services to fetch models from

### Service Format

- `service` - uses default port for that service
- `service:port` - custom port
- `service@hostname` - custom hostname
- `service@hostname:port` - custom hostname and port

### Supported Services

| Service  | Default Port |
|----------|--------------|
| lmstudio | 1234         |
| ollama   | 11434        |
| llama    | 8080         |
| llama.cpp | 8080        |
| vllm     | 8000         |
| litellm  | 4000         |

### Supported Agents

- **opencode** - Updates `~/.config/opencode/opencode.json`
- **pi** - Updates `~/.pi/agent/models.json`

## Example

```json
{
    "agents": ["opencode", "pi"],
    "services": ["lmstudio@localhost:1234", "ollama"]
}
```

This will fetch models from LM Studio on localhost:1234 and Ollama on localhost:11434, then update both OpenCode and Pi agent configurations.
