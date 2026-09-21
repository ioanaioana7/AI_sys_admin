"""
Agent AI simplificat care funcționează cu modele mici fără tool calling.
Folosește prompt engineering pentru a decide ce tool-uri să apeleze.
"""

import os
import re
from litellm import completion

# Configurare directorul gestionat
MANAGED_DIR = os.getenv("MANAGED_DIR", "D:\\ASO\\Proiect\\managed_system")

# Import tool-uri
import sys
sys.path.insert(0, os.path.dirname(__file__))
from mcp_server import (
    list_directory, get_file_content, get_file_info
)

SYSTEM_PROMPT = """You are a system administrator assistant. You help users manage their system.

Available commands:
- LIST <path> - list directory contents (use "." for root)
- READ <path> - read file content
- INFO <path> - get file/directory info
- SEARCH <pattern> <path> - search for files
- USAGE <path> - get disk usage
- SYSINFO - get system information

When answering:
1. First decide which command(s) to use
2. Write the command(s) in format: COMMAND <args>
3. After getting results, provide a clear answer to the user

Example:
User: "What files are in the root?"
You: "LIST .
Based on the directory listing, the root contains..."
"""


def parse_and_execute_commands(text: str) -> str:
    """
    Parsează textul pentru comenzi și le execută.
    
    Returns:
        Rezultatele comenzilor executate
    """
    results = []
    
    # Caută comenzi în text
    commands = {
        r'LIST\s+(.+?)(?:\n|$)': lambda m: list_directory(m.group(1).strip()),
        r'READ\s+(.+?)(?:\n|$)': lambda m: get_file_content(m.group(1).strip()),
        r'INFO\s+(.+?)(?:\n|$)': lambda m: get_file_info(m.group(1).strip()),
        r'SEARCH\s+(\S+)\s+(.+?)(?:\n|$)': lambda m: search_files(m.group(1).strip(), m.group(2).strip()),
        r'USAGE\s+(.+?)(?:\n|$)': lambda m: get_disk_usage(m.group(1).strip()),
        r'SYSINFO': lambda m: get_system_info(),
    }
    
    for pattern, func in commands.items():
        matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            try:
                result = func(match)
                cmd = match.group(0).strip()
                results.append(f"Command: {cmd}\nResult: {result}\n")
            except Exception as e:
                results.append(f"Error executing command: {str(e)}\n")
    
    return "\n".join(results) if results else ""


def chat(user_message: str) -> str:
    """
    Procesează un mesaj și returnează răspunsul.
    """
    try:
        # Prima cerere - LLM decide ce comenzi să folosească
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        
        print("  [Thinking...]", flush=True)
        
        response = completion(
            model="ollama/gemma3:1b",
            messages=messages,
            api_base="http://localhost:11434",
            temperature=0.3,
            max_tokens=512
        )
        
        llm_response = response.choices[0].message.content
        
        # Execută comenzile din răspunsul LLM
        command_results = parse_and_execute_commands(llm_response)
        
        if not command_results:
            # Nu sunt comenzi - returnează direct răspunsul
            return llm_response
        
        print("  [Executing commands...]", flush=True)
        print(f"  {command_results[:200]}..." if len(command_results) > 200 else f"  {command_results}", flush=True)
        
        # A doua cerere - LLM interpretează rezultatele
        messages.append({"role": "assistant", "content": llm_response})
        messages.append({"role": "user", "content": f"Command results:\n{command_results}\n\nPlease provide a clear answer based on these results."})
        
        print("  [Formulating answer...]", flush=True)
        
        final_response = completion(
            model="ollama/gemma3:1b",
            messages=messages,
            api_base="http://localhost:11434",
            temperature=0.3,
            max_tokens=512
        )
        
        return final_response.choices[0].message.content
        
    except Exception as e:
        return f"Error: {str(e)}\n\nPlease make sure Ollama is running: ollama serve"


def main():
    """Funcție principală pentru rularea agentului."""
    print("=" * 60)
    print("System Administrator AI Agent (Simple Mode)")
    print("=" * 60)
    print(f"Managing directory: {MANAGED_DIR}")
    print(f"Model: ollama/gemma3:1b")
    print("Type 'exit' or 'quit' to stop")
    print("=" * 60)
    print()
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            print(f"\nSystemAdministrator:")
            response = chat(user_input)
            print(response)
            print()
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {str(e)}\n")


if __name__ == "__main__":
    main()