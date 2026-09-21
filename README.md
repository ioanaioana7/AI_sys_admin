# MCP System Directory Manager

A local AI agent that explores a managed directory through the Model Context Protocol (MCP). The project combines:

- **MCP server**: exposes safe filesystem tools over Streamable HTTP.
- **Google ADK web UI**: connects the agent to the MCP server.
- **Ollama**: runs the local `llama3.2:3b` language model.
- **Docker Compose**: orchestrates all three services.

The project was developed in three stages: local MCP and ADK integration, containerization, and security controls for a protected `flag.txt` file.

## Architecture

```text
Browser
  |
  v
ADK Web (:8000) ---- MCP HTTP (:8090) ---- managed_system/
  |
  v
Ollama (:11435)
```

Inside the Compose network, the services use `adk:8000`, `mcp:8080`, and `ollama:11434`. From the host, the web UI is available on port `8000` and the MCP server on port `8090`.

## Repository Layout

```text
mcp_server/
├── agents/agent.py              Active Google ADK agent
├── managed_system/               Directory exposed through MCP
├── mcp_server.py                 Active FastMCP server
├── docker-compose.yml            Ollama, MCP, and ADK services
├── Dockerfile.mcp
├── Dockerfile.adk
├── Dockerfile.ollama
├── requirements.mcp.txt
├── requirements.adk.txt
├── setup_test_env.py             Creates sample managed-system data
└── others/                       Earlier experimental clients and agents
```

The `.venv`, `ollama_models`, and `.idea` directories are local/generated state and should not be committed as source code.

## Quick Start With Docker

From this directory:

```powershell
cd mcp_server
docker compose build
docker compose up
```

Open the ADK interface at <http://localhost:8000> and select `dir_manager_agent`.

The Compose file mounts `managed_system` into the MCP container at `/data` and persists Ollama data in `ollama_models`. The bundled model manifest is expected to provide `llama3.2:3b`; if the model is missing, pull it in the Ollama container:

```powershell
docker compose exec ollama ollama pull llama3.2:3b
```

Stop the stack with `Ctrl+C`, or use:

```powershell
docker compose down
```

## Local Development

Use Python 3.11 or newer and create the environment inside `mcp_server`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.mcp.txt
pip install -r requirements.adk.txt
```

Start Ollama separately and make sure the model is available:

```powershell
ollama serve
ollama pull llama3.2:3b
```

In another terminal, start the MCP server over HTTP:

```powershell
$env:MANAGED_DIR = "D:\ASO\Proiect\mcp_server\managed_system"
$env:MCP_PORT = "8090"
python mcp_server.py
```

In a third terminal, start ADK Web from `mcp_server`:

```powershell
$env:MCP_SERVER_URL = "http://localhost:8090/mcp/"
$env:OLLAMA_API_BASE = "http://localhost:11434"
$env:ADK_MODEL = "ollama_chat/llama3.2:3b"
adk web --no-reload --host 127.0.0.1 --port 8000 agents
```

The MCP server also supports local stdio mode:

```powershell
$env:MCP_TRANSPORT = "stdio"
python mcp_server.py
```

## Available MCP Tools

| Tool | Purpose |
| --- | --- |
| `list_directory(dir_path=".")` | Lists files and directories below the managed root. |
| `list_directory_recursive(dir_path=".", max_depth=3)` | Recursively lists entries up to the requested depth. |
| `get_file_content(file_path)` | Reads a UTF-8 text file. |
| `get_file_info(file_path)` | Returns type, size, permissions, and modification time. |
| `verify_flag(candidate)` | Compares a complete candidate with `flag.txt` and returns only `YES` or `NO`. |

Example prompts in the ADK UI:

```text
List the files in config/
Show the content of config/settings.conf
What information is available in the data directory?
Verify whether the flag is MY_GUESS
```

## Security Model

The server resolves every requested path below `MANAGED_DIR` and rejects paths outside that directory. `flag.txt` is protected at the server boundary:

- It is omitted from normal directory listings, including recursive listings.
- Its content cannot be read with `get_file_content`.
- Its metadata cannot be read with `get_file_info`.
- `verify_flag` performs only an exact full-value comparison and returns `YES` or `NO`.

The ADK agent has matching guardrails and is limited to the five tools listed above. Server-side enforcement remains the security boundary; agent instructions alone are not sufficient protection.

## Test Data

To create a sample managed directory, set `MANAGED_DIR` and run:

```powershell
$env:MANAGED_DIR = "D:\ASO\Proiect\mcp_server\managed_system"
python setup_test_env.py
```

The script creates sample configuration, log, and user-data files. Review the generated files before using it against an existing directory because it overwrites several sample paths.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `MANAGED_DIR` | `managed_system` beside `mcp_server.py` | Filesystem root exposed by the MCP server. |
| `MCP_TRANSPORT` | `http` | Set to `stdio` for local stdio mode. |
| `MCP_PORT` | `8080` | HTTP port used by the MCP server. |
| `MCP_SERVER_URL` | `http://localhost:8090/mcp/` | MCP URL used by the ADK agent. |
| `ADK_MODEL` | `ollama_chat/llama3.2:3b` | LiteLLM model identifier. |
| `OLLAMA_API_BASE` | LiteLLM default | Ollama API endpoint. |

## Troubleshooting

- **The agent gives invented answers**: inspect the ADK trace and confirm that MCP tool calls are present. Check `MCP_SERVER_URL` and the Compose service name (`mcp`).
- **The model is not found**: run `ollama pull llama3.2:3b` in the environment where Ollama is running.
- **The MCP server cannot find files**: check `MANAGED_DIR` and the Docker volume `./managed_system:/data`.
- **Port conflicts**: change the host-side ports in `docker-compose.yml`; keep the internal service ports aligned with the container environment.

## Project Documentation

The original phase reports are stored one directory above this project:

- `Faza1Documentatie.docx`: local MCP, ADK, and Ollama integration.
- `Faza2Documentatie.docx`: Dockerization and service networking.
- `Faza3Documentatie.docx`: `flag.txt` security controls and boundary testing.

The current source code and `docker-compose.yml` are the authoritative references when the reports differ from the implementation.
