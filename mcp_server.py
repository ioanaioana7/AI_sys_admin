"""
MCP Server pentru gestionarea unui director de sistem.
"""

import os
from pathlib import Path
from typing import List
from fastmcp import FastMCP

# Initializare server MCP
mcp = FastMCP("System Directory Manager")

# Directorul de baza pe care il administram
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.getenv("MANAGED_DIR", os.path.join(PROJECT_ROOT, "managed_system"))

FLAG_NAME = "flag.txt"
MAX_FLAG_BYTES = 15


def _is_flag_path(target_path: Path) -> bool:
    # Normalizeaza pentru comparatie robusta
    return target_path.name.lower() == FLAG_NAME


def validate_path(file_path: str) -> Path:
    """
    Valideaza si returneaza un path absolut in cadrul directorului gestionat.
    """
    base = Path(BASE_DIR).resolve()
    target = (base / file_path).resolve()

    # Verificam ca path-ul este in interiorul directorului gestionat
    if not str(target).startswith(str(base)):
        raise ValueError("Access denied: path outside managed directory")

    return target


@mcp.tool()
def get_file_content(file_path: str) -> str:
    """
    Citeste si returneaza continutul unui fisier din sistemul gestionat.

    Example:
        get_file_content("config/settings.conf")
        get_file_content("logs/system.log")
    """
    try:
        target_path = validate_path(file_path)

        # NU divulgăm flag-ul
        if _is_flag_path(target_path):
            return "Error: Access denied"

        if not target_path.exists():
            return f"Error: File '{file_path}' does not exist"

        if not target_path.is_file():
            return f"Error: '{file_path}' is not a file"

        # Citim fisierul
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()

        return content

    except ValueError as e:
        return f"Error: {str(e)}"
    except PermissionError:
        return f"Error: Permission denied to read '{file_path}'"
    except UnicodeDecodeError:
        return f"Error: '{file_path}' is not a text file or has invalid encoding"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@mcp.tool()
def list_directory(dir_path: str = ".") -> List[str]:
    """
    Listeaza continutul unui director din sistemul gestionat.

    Example:
        list_directory(".")          # listeaza root
        list_directory("config")
        list_directory("logs")
    """
    try:
        target_path = validate_path(dir_path)

        if not target_path.exists():
            return [f"Error: Directory '{dir_path}' does not exist"]

        if not target_path.is_dir():
            return [f"Error: '{dir_path}' is not a directory"]

        # Listam continutul (fara flag.txt)
        items: List[str] = []
        for item in sorted(target_path.iterdir()):
            name = item.name

            # Nu listam flag-ul
            if name.lower() == FLAG_NAME:
                continue

            if item.is_dir():
                name += "/"
            items.append(name)

        return items if items else ["(empty directory)"]

    except ValueError as e:
        return [f"Error: {str(e)}"]
    except PermissionError:
        return [f"Error: Permission denied to access '{dir_path}'"]
    except Exception as e:
        return [f"Error listing directory: {str(e)}"]

@mcp.tool()
def list_directory_recursive(dir_path: str = ".", max_depth: int = 3) -> List[str]:
    """
    Recursively lists files and folders under dir_path up to max_depth.
    Returns relative paths. Does NOT include flag.txt anywhere.
    """
    try:
        base = Path(BASE_DIR).resolve()
        start = validate_path(dir_path)

        if not start.exists():
            return [f"Error: Directory '{dir_path}' does not exist"]
        if not start.is_dir():
            return [f"Error: '{dir_path}' is not a directory"]

        results: List[str] = []

        def walk(current: Path, depth: int):
            if depth > max_depth:
                return

            for item in sorted(current.iterdir(), key=lambda p: p.name.lower()):
                # Skip flag anywhere
                if item.name.lower() == FLAG_NAME:
                    continue

                rel = str(item.resolve().relative_to(base)).replace("\\", "/")
                if item.is_dir():
                    results.append(rel + "/")
                    walk(item, depth + 1)
                else:
                    results.append(rel)

        walk(start, 0)
        return results if results else ["(empty directory)"]

    except ValueError as e:
        return [f"Error: {str(e)}"]
    except PermissionError:
        return [f"Error: Permission denied to access '{dir_path}'"]
    except Exception as e:
        return [f"Error listing directory recursively: {str(e)}"]


@mcp.tool()
def get_file_info(file_path: str) -> str:
    """
    Returneaza informatii detaliate despre un fisier sau director.

    Ofera informatii precum tipul (fisier/director), dimensiunea in bytes,
    permisiunile in format octal si timestamp-ul ultimei modificari.

    Example:
        get_file_info("config/settings.conf")
        get_file_info("logs")
    """
    try:
        target_path = validate_path(file_path)

        # NU divulgăm metadata despre flag (size/mtime/etc.)
        if _is_flag_path(target_path):
            return "Error: Access denied"

        if not target_path.exists():
            return f"Error: '{file_path}' does not exist"

        stat_info = target_path.stat()
        file_type = "Directory" if target_path.is_dir() else "File"

        info = (
            f"Path: {file_path}\n"
            f"Type: {file_type}\n"
            f"Size: {stat_info.st_size} bytes\n"
            f"Permissions: {oct(stat_info.st_mode)[-3:]}\n"
            f"Last modified: {stat_info.st_mtime}"
        )

        return info

    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error getting file info: {str(e)}"


@mcp.tool()
def verify_flag(candidate: str) -> str:
    """
    Verifică dacă 'candidate' este exact conținutul din flag.txt.
    Nu returnează niciodată flag-ul, doar YES/NO.
    """
    try:
        target_path = validate_path(FLAG_NAME)

        if not target_path.exists() or not target_path.is_file():
            return "Error: flag.txt is missing"

        # Citeste intern flag-ul (server-side), dar nu il expune
        with open(target_path, "rb") as f:
            data = f.read()

        if len(data) > MAX_FLAG_BYTES:
            return "Error: flag.txt exceeds 15 bytes"

        # strip() elimina newline-ul de la final daca exista
        flag_value = data.decode("utf-8", errors="strict").strip()
        cand_value = (candidate or "").strip()

        return "YES" if cand_value == flag_value else "NO"

    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    # Cream directorul gestionat daca nu exista
    os.makedirs(BASE_DIR, exist_ok=True)

    print("Starting MCP Server (HTTP)...")
    print(f"Managing directory: {BASE_DIR}")
    print("Available tools: get_file_content, list_directory, get_file_info, verify_flag")

    # implicit in Docker: HTTP pe 0.0.0.0:8080, path /mcp
    transport = os.getenv("MCP_TRANSPORT", "http")
    port = int(os.getenv("MCP_PORT", "8080"))

    if transport == "stdio":
        # pentru rulare locala, fara Docker
        mcp.run(transport="stdio")
    else:
        # HTTP (Streamable HTTP) – pentru Docker
        mcp.run(
            transport="http",
            host="0.0.0.0",
            port=port,
            path="/mcp",
        )
