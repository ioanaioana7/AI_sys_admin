# agent.py

import json
import subprocess
import threading
import queue
import uuid
from typing import Any, Dict, List

from others.agent_config import MCP_SERVER_CMD, SYSTEM_PROMPT
from others.ollama_client import ollama_chat, OllamaError


class MCPStdioClient:
    def __init__(self, cmd: List[str]):
        print("[agent] starting MCP server:", " ".join(cmd))
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        self.responses = queue.Queue()
        self._start_reader_thread()
        self._start_stderr_thread()

    def _start_reader_thread(self):
        def reader():
            for line in self.proc.stdout:
                line = line.strip()
                if not line:
                    continue
                # fastmcp sometimes prints text -> we ignore non-JSON
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    # you can print it to debug
                    print(f"[agent][stdout-nonjson] {line}")
                    continue
                # put JSON messages in queue
                self.responses.put(msg)
        t = threading.Thread(target=reader, daemon=True)
        t.start()

    def _start_stderr_thread(self):
        def reader_err():
            for line in self.proc.stderr:
                line = line.strip()
                if line:
                    print(f"[mcp][stderr] {line}")
        t = threading.Thread(target=reader_err, daemon=True)
        t.start()

    def _next_id(self) -> str:
        return str(uuid.uuid4())

    def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        req_id = self._next_id()
        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        line = json.dumps(req) + "\n"
        # in case stdin is None -> server didn't start
        if not self.proc.stdin:
            raise RuntimeError("MCP server stdin is not available.")
        self.proc.stdin.write(line)
        self.proc.stdin.flush()

        while True:
            resp = self.responses.get()
            if resp.get("id") == req_id:
                return resp

    def list_tools(self):
        return self.send_request("tools/list")

    def call_tool(self, name: str, arguments: Dict[str, Any]):
        return self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })


def main():
    # 1. start MCP
    mcp = MCPStdioClient(MCP_SERVER_CMD)

    # 2. get tools
    print("[agent] requesting tools from MCP...")
    tools_info = mcp.list_tools()
    print("[agent] MCP tools response:", tools_info)

    conversation = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    print("\nMCP System Admin Agent started (English).")
    print("Try things like:")
    print("- 'List the managed directory'")
    print("- 'Show me the content of config.txt'")
    print("Ctrl+C to exit.\n")

    while True:
        try:
            user_input = input("YOU> ")
        except (EOFError, KeyboardInterrupt):
            print("\n[agent] exiting")
            break

        # simple commands that directly call MCP (bypass LLM)
        if user_input.lower().startswith("mcp:"):
            # e.g. mcp:list .
            parts = user_input.split()
            if len(parts) >= 2 and parts[0] == "mcp:list":
                dir_path = parts[1] if len(parts) > 1 else "."
                resp = mcp.call_tool("list_directory", {"dir_path": dir_path})
                print("AGENT>", resp.get("result"))
                continue

        conversation.append({"role": "user", "content": user_input})

        # 3. ask LLM
        try:
            model_msg = ollama_chat(conversation)
        except OllamaError as e:
            print(f"AGENT> LLM error: {e}")
            continue

        assistant_text = model_msg.get("content", "")
        print(f"AGENT> {assistant_text}")
        conversation.append({"role": "assistant", "content": assistant_text})

        # OPTIONAL: very naive detection
        if "list_directory" in assistant_text and "{" in assistant_text:
            print("[agent] (note) model looks like it wants to call a tool; you can implement parsing here.")


if __name__ == "__main__":
    main()
