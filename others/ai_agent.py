"""
Agent AI care acționează ca administrator de sistem.
Folosește LiteLLM pentru a comunica cu Ollama și tool calling pentru MCP.
"""

import os
import json
import asyncio
from typing import List, Dict, Any
from litellm import completion

# ================== CONFIG ==================

# Directorul gestionat (ai grijă să fie director, nu fișier)
MANAGED_DIR = os.getenv("MANAGED_DIR", r"D:\ASO\Proiect\managed_system")

# Istoricul conversației
conversation_history: List[Dict[str, Any]] = []

SYSTEM_PROMPT = """You are an expert system administrator with deep knowledge of systems management.

Your role is to help users understand and manage their system by:
- Inspecting files and directories in the managed system
- Providing clear explanations about system state and configurations
- Answering questions about system logs, configurations, and performance

IMPORTANT INSTRUCTIONS:
1. Use the available tools to get accurate, real-time information
2. After receiving tool results, analyze them and provide a clear answer to the user
3. Do NOT call the same tool multiple times with the same arguments
4. After getting the information you need, ALWAYS provide a final response to the user
5. Be concise and direct in your responses

You have access to these tools:
- list_directory: List contents of a directory
- get_file_content: Read file contents
- get_file_info: Get detailed file information

Always provide a final answer after using tools.
"""

# ================== TOOLS SCHEMA (pt. LLM) ==================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "Lists the contents of a directory. Returns a list of files and subdirectories. Directories are marked with '/' suffix.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dir_path": {
                        "type": "string",
                        "description": "The relative path to the directory (use '.' for root)"
                    }
                },
                "required": ["dir_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_content",
            "description": "Reads and returns the content of a text file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The relative path to the file"
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_file_info",
            "description": "Gets detailed information about a file or directory (size, permissions, last modified).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The relative path to the file or directory"
                    }
                },
                "required": ["file_path"]
            }
        }
    }
]


# ================== EXECUTOR MCP LOCAL ==================

def _is_coroutine(obj) -> bool:
    return asyncio.iscoroutine(obj) or asyncio.iscoroutinefunction(obj)


def _normalize_tool_output(res: Any) -> str:
    """
    fastmcp tinde să întoarcă dicturi gen {"files": [...]} sau {"content": "..."}.
    Aici le facem text pentru LLM.
    """
    # dict de forma {"files": [...]}
    if isinstance(res, dict):
        if "files" in res and isinstance(res["files"], list):
            return "\n".join(str(x) for x in res["files"])
        if "content" in res:
            return str(res["content"])
        # alt dict -> îl returnăm json
        return json.dumps(res, indent=2)

    # listă simplă
    if isinstance(res, list):
        return "\n".join(str(x) for x in res)

    return str(res)


def _call_mcp_like_object(obj, **kwargs):
    """
    Încearcă mai multe variante de apel pentru un obiect MCP (fastmcp).
    IMPORTANT: tratează și cazul în care .run(...) e async și trebuie await.
    Întoarce (success: bool, result: Any)
    """
    # 1. direct callable
    if callable(obj):
        maybe = obj(**kwargs)
        if asyncio.iscoroutine(maybe):
            return True, asyncio.run(maybe)
        return True, maybe

    # 2. .func
    if hasattr(obj, "func") and callable(getattr(obj, "func")):
        maybe = obj.func(**kwargs)
        if asyncio.iscoroutine(maybe):
            return True, asyncio.run(maybe)
        return True, maybe

    # 3. .run
    if hasattr(obj, "run") and callable(getattr(obj, "run")):
        # mai întâi încercăm cu kwargs
        try:
            maybe = obj.run(**kwargs)
        except TypeError:
            # varianta ta: trebuie dict
            maybe = obj.run(kwargs)

        if asyncio.iscoroutine(maybe):
            return True, asyncio.run(maybe)
        return True, maybe

    # 4. .call
    if hasattr(obj, "call") and callable(getattr(obj, "call")):
        try:
            maybe = obj.call(**kwargs)
        except TypeError:
            maybe = obj.call(kwargs)

        if asyncio.iscoroutine(maybe):
            return True, asyncio.run(maybe)
        return True, maybe

    # 5. .handler
    if hasattr(obj, "handler") and callable(getattr(obj, "handler")):
        try:
            maybe = obj.handler(**kwargs)
        except TypeError:
            maybe = obj.handler(kwargs)

        if asyncio.iscoroutine(maybe):
            return True, asyncio.run(maybe)
        return True, maybe

    return False, f"Tool object of type {type(obj).__name__} is not directly callable. Available attrs: {dir(obj)}"


def execute_tool_call(tool_name: str, arguments: Dict[str, Any]) -> str:
    """
    Execută un tool din mcp_server și returnează rezultatul ca text.
    """
    import sys
    sys.path.insert(0, os.path.dirname(__file__))

    try:
        from mcp_server import (
            list_directory,
            get_file_content,
            get_file_info
        )
    except Exception as e:
        return f"Error importing mcp_server tools: {e}"

    tools_map = {
        "list_directory": list_directory,
        "get_file_content": get_file_content,
        "get_file_info": get_file_info
    }

    if tool_name not in tools_map:
        return f"Error: Unknown tool {tool_name}"

    tool_obj = tools_map[tool_name]

    try:
        ok, res = _call_mcp_like_object(tool_obj, **arguments)
        if not ok:
            return f"Error: {res}"

        return _normalize_tool_output(res)

    except Exception as e:
        return f"Error executing tool: {str(e)}"


# ================== CHAT ==================

def chat(user_message: str) -> str:
    """
    1. trimite mesajul userului la model (cu tools)
    2. dacă modelul cere tool → îl executăm
    3. facem a doua chemare fără tools pentru răspuns final
    """
    conversation_history.append({"role": "user", "content": user_message})

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *conversation_history
    ]

    # ===== 1. PRIMA CHEMARE — modelul poate cere tool-uri =====
    try:
        first_response = completion(
            model="ollama/llama3.2:3b",
            messages=messages,
            tools=TOOLS,
            api_base="http://localhost:11434",
            temperature=0.7
        )
    except Exception as e:
        return f"Error talking to model: {e}"

    assistant_msg = first_response.choices[0].message

    # normalizare la dict
    if hasattr(assistant_msg, "to_dict"):
        assistant_dict = assistant_msg.to_dict()
    elif isinstance(assistant_msg, dict):
        assistant_dict = assistant_msg
    else:
        assistant_dict = {}
        if hasattr(assistant_msg, "content"):
            assistant_dict["content"] = assistant_msg.content
        if hasattr(assistant_msg, "function_call"):
            assistant_dict["function_call"] = assistant_msg.function_call
        if hasattr(assistant_msg, "tool_calls"):
            assistant_dict["tool_calls"] = assistant_msg.tool_calls

    content = (assistant_dict.get("content") or "").strip()
    func_call = assistant_dict.get("function_call") or assistant_dict.get("tool_call")
    tool_calls = assistant_dict.get("tool_calls")

    # dacă nu a cerut tool-uri, returnăm direct
    if not func_call and not tool_calls:
        final_response = content or "I don't have a response."
        conversation_history.append({"role": "assistant", "content": final_response})
        return final_response

    # ===== 2. EXECUTĂM TOOL-URILE =====
    calls = []
    if func_call:
        calls.append(func_call)
    elif tool_calls:
        if isinstance(tool_calls, list):
            calls.extend(tool_calls)
        else:
            calls.append(tool_calls)

    # prevenire loop
    seen_tool_calls: Dict[str, int] = {}
    aggregated_tool_outputs = []

    for call in calls:
        tool_name = None
        arguments = {}

        if isinstance(call, dict):
            tool_name = call.get("name") or call.get("function", {}).get("name")
            args_raw = call.get("arguments") or call.get("function", {}).get("arguments") or "{}"
        else:
            tool_name = getattr(call, "name", None) or getattr(call, "function", {}).get("name")
            args_raw = getattr(call, "arguments", "{}")

        # parse args
        if isinstance(args_raw, str):
            try:
                arguments = json.loads(args_raw)
            except Exception:
                arguments = {}
        elif isinstance(args_raw, dict):
            arguments = args_raw
        else:
            arguments = {}

        if not tool_name:
            continue

        sig = f"{tool_name}:{json.dumps(arguments, sort_keys=True)}"
        seen_tool_calls[sig] = seen_tool_calls.get(sig, 0) + 1
        if seen_tool_calls[sig] > 3:
            err_msg = f"Error: repeated call to tool '{tool_name}' with same args detected. Aborting."
            messages.append({"role": "tool", "name": tool_name, "content": err_msg})
            aggregated_tool_outputs.append(err_msg)
            continue

        # LOG
        print(f"  [Calling tool: {tool_name} with {arguments}]")

        result = execute_tool_call(tool_name, arguments)

        messages.append({
            "role": "tool",
            "name": tool_name,
            "content": result
        })

        aggregated_tool_outputs.append(f"{tool_name} output:\n{result}")

    # ===== 3. A DOUA CHEMARE — forțăm răspuns final =====
    tool_summary = "\n\n---\n".join(aggregated_tool_outputs) if aggregated_tool_outputs else "No tool outputs."

    messages.append({
        "role": "assistant",
        "content": (
            "TOOL_RESULTS_SUMMARY:\n"
            + tool_summary
            + "\n\nUse ONLY the information above to answer the user. "
              "Do NOT call any tools again. Provide a concise final answer."
        )
    })

    try:
        second_response = completion(
            model="ollama/llama3.2:3b",
            messages=messages,
            tools=[],  # fără tools aici
            api_base="http://localhost:11434",
            temperature=0.0
        )
    except Exception as e:
        fallback = (
            "I received tool outputs but couldn't produce a final answer:\n\n"
            + tool_summary
            + f"\n\n(secondary model error: {e})"
        )
        conversation_history.append({"role": "assistant", "content": fallback})
        return fallback

    final_msg = second_response.choices[0].message
    if hasattr(final_msg, "to_dict"):
        final_dict = final_msg.to_dict()
    elif isinstance(final_msg, dict):
        final_dict = final_msg
    else:
        final_dict = {"content": getattr(final_msg, "content", "")}

    final_content = (final_dict.get("content") or "").strip()
    if not final_content:
        final_content = "I used the tool results but could not produce a final answer."

    conversation_history.append({"role": "assistant", "content": final_content})
    return final_content


# ================== MAIN ==================

def main():
    print("=" * 60)
    print("System Administrator AI Agent")
    print("=" * 60)
    print(f"Managing directory: {MANAGED_DIR}")
    print(f"Model: ollama/llama3.2:3b")
    print("Type 'exit' or 'quit' to stop")
    print("=" * 60)
    print()

    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("exit", "quit", "q"):
                print("Goodbye!")
                break

            if not user_input:
                continue

            print("\nSystemAdministrator: ", end="", flush=True)
            response = chat(user_input)
            print(response)
            print()

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


if __name__ == "__main__":
    main()
