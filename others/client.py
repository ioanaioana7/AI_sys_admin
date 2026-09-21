import asyncio
import os
from langchain_ollama.chat_models import ChatOllama
from mcp_use import MCPAgent, MCPClient


current_dir = os.path.dirname(os.path.abspath(__file__))
server_path = os.path.join(current_dir, "mcp_server.py")

CONFIG = {
    "mcpServers": {
        "dir-manager": {
            "command": "python",
            "args": [server_path],
        }
    }
}


async def main():
    # 1) MCP client
    client = MCPClient.from_dict(CONFIG)

    # 2) LLM (Ollama)
    llm = ChatOllama(
        model="llama3.2:3b",
        base_url="http://localhost:11434",
        temperature=0,
    )

    # 3) Agent MCP
    agent = MCPAgent(
        llm=llm,
        client=client,
        max_steps=20,
    )

    # 4) Prompt initial – ii explicam contextul
    system_prompt = (
        "You are a system administrator agent connected to an MCP server that manages a filesystem directory.\n"
        "The MCP server exposes these tools:\n"
        " - list_directory(dir_path: str) -> list of entries\n"
        " - get_file_content(file_path: str) -> file text content\n"
        " - get_file_info(file_path: str) -> details about the file (size, type, etc.)\n"
        "Always prefer calling these tools instead of guessing or inventing data.\n"
        "Be explicit about which directory you are inspecting.\n"
        "If the user asks something you cannot know, call a tool.\n"
        "Start by greeting the user and asking what they want to do.\n"
    )

    first_answer = await agent.run(system_prompt)
    print("\nAssistant:", first_answer)

    # 5) Loop
    try:
        while True:
            user_msg = input("\nYou> ").strip()
            if user_msg.lower() in {"exit", "quit", "q"}:
                print("Bye 👋")
                break

            # trimitem mesajul utilizatorului la agent
            reply = await agent.run(user_msg)
            print("\nAssistant:", reply)

    finally:
        await client.close_all_sessions()


if __name__ == "__main__":
    asyncio.run(main())
