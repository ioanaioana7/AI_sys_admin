# MCP System Directory Manager

A local AI system that lets a Google ADK agent inspect a controlled directory through the Model Context Protocol (MCP). The language model runs locally with Ollama, and the whole stack can be started with Docker Compose.

## What It Includes

- **FastMCP server**: exposes filesystem operations through Streamable HTTP.
- **Google ADK agent**: connects the model to the MCP tools and provides the web interface.
- **Ollama**: runs `llama3.2:3b` locally through LiteLLM.
- **Security controls**: keeps `flag.txt` hidden and supports exact-value verification without disclosure.

## How It Works

```text
Browser :8000
    |
    v
ADK Web ---- MCP Server :8090 ---- managed_system/
    |
    v
Ollama :11435
```

The ports above are host ports. Inside Docker, ADK reaches the MCP server at `http://mcp:8080/mcp/` and Ollama at `http://ollama2:11434`.

## Start With Docker

Requirements: Docker Desktop with Docker Compose support.

From the repository directory:

```powershell
docker compose build
docker compose up
```

Open <http://localhost:8000>, select `dir_manager_agent`, and enter a request in English.

The first startup may require the model to be downloaded:

```powershell
docker compose exec ollama ollama pull llama3.2:3b
```

Stop the services with `Ctrl+C`, or run:

```powershell
docker compose down
```

The Compose setup mounts `managed_system` as `/data` in the MCP container and stores Ollama state in `ollama_models/`. The latter is local-only and is excluded from Git.

## Example Requests

```text
List the files in config/
Show the content of config/settings.conf
Give me information about the data directory
Verify whether the flag is MY_GUESS
```

## MCP Tools

| Tool | Behavior |
| --- | --- |
| `list_directory(dir_path=".")` | Lists entries in one directory. |
| `list_directory_recursive(dir_path=".", max_depth=3)` | Lists files and directories recursively up to `max_depth`. |
| `get_file_content(file_path)` | Reads a UTF-8 text file. |
| `get_file_info(file_path)` | Returns type, size, permissions, and modification time. |
| `verify_flag(candidate)` | Returns only `YES` or `NO` for a complete candidate value. |

All paths are resolved relative to `MANAGED_DIR`.

## Security Boundary

The MCP server, rather than the model prompt, is the primary enforcement point:

- Requests outside `MANAGED_DIR` are rejected.
- `flag.txt` is omitted from normal and recursive listings.
- `get_file_content` and `get_file_info` refuse access to `flag.txt`.
- `verify_flag` compares a full candidate and returns only `YES` or `NO`.
- The ADK agent is restricted to the tools implemented by this server and has matching refusal rules.

Do not place real secrets in `managed_system`. This project demonstrates tool boundaries; it is not a general-purpose secure file service.

## Local Development

Use Python 3.11 or newer. From the repository directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.mcp.txt
pip install -r requirements.adk.txt
```

Start Ollama and download the model:

```powershell
ollama serve
ollama pull llama3.2:3b
```

Start the MCP server in a second terminal:

```powershell
$env:MANAGED_DIR = "$PWD\managed_system"
$env:MCP_PORT = "8090"
python mcp_server.py
```

Start the ADK web UI in a third terminal:

```powershell
$env:MCP_SERVER_URL = "http://localhost:8090/mcp/"
$env:OLLAMA_API_BASE = "http://localhost:11434"
$env:ADK_MODEL = "ollama_chat/llama3.2:3b"
adk web --no-reload --host 127.0.0.1 --port 8000 agents
```

For an MCP client that launches the server itself, set `MCP_TRANSPORT=stdio` before running `python mcp_server.py`.

## Configuration

| Variable | Default | Used by |
| --- | --- | --- |
| `MANAGED_DIR` | `managed_system` beside `mcp_server.py` | MCP server |
| `MCP_TRANSPORT` | `http` | MCP server; `stdio` is also supported |
| `MCP_PORT` | `8080` | MCP server HTTP listener |
| `MCP_SERVER_URL` | `http://localhost:8090/mcp/` | ADK agent |
| `ADK_MODEL` | `ollama_chat/llama3.2:3b` | ADK agent |
| `OLLAMA_API_BASE` | LiteLLM default | ADK agent/Ollama connection |

## Sample Data

`setup_test_env.py` creates sample configuration, logs, and user data:

```powershell
$env:MANAGED_DIR = "$PWD\managed_system"
python setup_test_env.py
```

Review the target directory first. The script writes sample files and can overwrite existing paths.

## Repository Layout

```text
agents/                 Active Google ADK agent
managed_system/         Directory exposed through MCP
docs/                   Phase documentation reports
mcp_server.py           Active FastMCP server
docker-compose.yml      Ollama, MCP, and ADK services
Dockerfile.*            Container definitions
requirements.*.txt      Service dependencies
setup_test_env.py       Sample-data generator
others/                 Earlier experimental clients and agents
```

Local environments, IDE metadata, Ollama models, logs, and `managed_system/flag.txt` are excluded by `.gitignore`.

## Troubleshooting

- **Model not found**: run `ollama pull llama3.2:3b` in the same environment as Ollama.
- **Agent invents file contents**: check the ADK trace for MCP `call_tool` events and verify `MCP_SERVER_URL`.
- **File not found**: verify `MANAGED_DIR` locally or the `./managed_system:/data` volume in Compose.
- **Port already in use**: change the host-side ports in `docker-compose.yml`; leave the internal container ports unchanged.

## Documentation

- [`docs/Faza1Documentatie.docx`](docs/Faza1Documentatie.docx): local MCP, ADK, and Ollama integration.
- [`docs/Faza2Documentatie.docx`](docs/Faza2Documentatie.docx): Dockerization and service networking.
- [`docs/Faza3Documentatie.docx`](docs/Faza3Documentatie.docx): `flag.txt` protection and security testing.

The source code and `docker-compose.yml` are authoritative if the phase reports differ from the current implementation.
