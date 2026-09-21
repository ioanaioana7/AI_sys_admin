"""
Tool-uri simple pentru agent fără dependență de FastMCP.
"""

import os
from pathlib import Path
from typing import List

# Directorul de bază pe care îl administrăm
BASE_DIR = os.getenv("MANAGED_DIR", "D:\\ASO\\Proiect\\managed_system")


def validate_path(file_path: str) -> Path:
    """
    Validează și returnează un path absolut în cadrul directorului gestionat.
    """
    base = Path(BASE_DIR).resolve()
    target = (base / file_path).resolve()
    
    # Verificăm că path-ul este în interiorul directorului gestionat
    if not str(target).startswith(str(base)):
        raise ValueError(f"Access denied: path outside managed directory")
    
    return target


def list_directory(dir_path: str = ".") -> List[str]:
    """
    Listează conținutul unui director din sistemul gestionat.
    """
    try:
        target_path = validate_path(dir_path)
        
        if not target_path.exists():
            return [f"Error: Directory '{dir_path}' does not exist"]
        
        if not target_path.is_dir():
            return [f"Error: '{dir_path}' is not a directory"]
        
        # Listăm conținutul
        items = []
        for item in sorted(target_path.iterdir()):
            name = item.name
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


def get_file_content(file_path: str) -> str:
    """
    Citește și returnează conținutul unui fișier din sistemul gestionat.
    """
    try:
        target_path = validate_path(file_path)
        
        if not target_path.exists():
            return f"Error: File '{file_path}' does not exist"
        
        if not target_path.is_file():
            return f"Error: '{file_path}' is not a file"
        
        # Citim fișierul
        with open(target_path, 'r', encoding='utf-8') as f:
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


def get_file_info(file_path: str) -> str:
    """
    Returnează informații detaliate despre un fișier sau director.
    """
    try:
        target_path = validate_path(file_path)
        
        if not target_path.exists():
            return f"Error: '{file_path}' does not exist"
        
        stat_info = target_path.stat()
        file_type = "Directory" if target_path.is_dir() else "File"
        
        info = f"""Path: {file_path}
Type: {file_type}
Size: {stat_info.st_size} bytes
Permissions: {oct(stat_info.st_mode)[-3:]}
Last modified: {stat_info.st_mtime}"""
        
        return info
    
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error getting file info: {str(e)}"


def search_files(pattern: str, dir_path: str = ".") -> List[str]:
    """
    Caută fișiere care conțin un pattern în nume.
    """
    try:
        target_path = validate_path(dir_path)
        
        if not target_path.exists():
            return [f"Error: Directory '{dir_path}' does not exist"]
        
        if not target_path.is_dir():
            return [f"Error: '{dir_path}' is not a directory"]
        
        matches = []
        base = Path(BASE_DIR).resolve()
        
        for item in target_path.rglob("*"):
            if item.is_file() and pattern.lower() in item.name.lower():
                rel_path = item.relative_to(base)
                matches.append(str(rel_path))
        
        return matches if matches else [f"No files found matching '{pattern}'"]
    
    except ValueError as e:
        return [f"Error: {str(e)}"]
    except Exception as e:
        return [f"Error searching files: {str(e)}"]


def get_disk_usage(dir_path: str = ".") -> str:
    """
    Returnează informații despre utilizarea spațiului pe disc.
    """
    try:
        target_path = validate_path(dir_path)
        
        if not target_path.exists():
            return f"Error: Directory '{dir_path}' does not exist"
        
        if not target_path.is_dir():
            return f"Error: '{dir_path}' is not a directory"
        
        total_size = 0
        file_count = 0
        dir_count = 0
        
        for item in target_path.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size
                file_count += 1
            elif item.is_dir():
                dir_count += 1
        
        size_mb = total_size / (1024 * 1024)
        
        info = f"""Directory: {dir_path}
Total size: {total_size} bytes ({size_mb:.2f} MB)
Files: {file_count}
Subdirectories: {dir_count}"""
        
        return info
    
    except ValueError as e:
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error calculating disk usage: {str(e)}"