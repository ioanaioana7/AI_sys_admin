"""
Script pentru crearea unui mediu de test cu fisiere si directoare.
"""

import os
from pathlib import Path

# Directorul de baza
BASE_DIR = os.getenv("MANAGED_DIR", "D:\\ASO\\Proiect\\managed_system")

def setup_test_environment():
    """Creeaza o structură de directoare si fișiere pentru testare."""
    
    base = Path(BASE_DIR)
    base.mkdir(exist_ok=True)
    
    # Cream subdirectoare
    (base / "config").mkdir(exist_ok=True)
    (base / "logs").mkdir(exist_ok=True)
    (base / "data").mkdir(exist_ok=True)
    
    # Cream fisiere de configurare
    (base / "config" / "settings.conf").write_text("""# System Settings
server_port=8080
max_connections=100
log_level=INFO
""")
    
    (base / "config" / "database.conf").write_text("""# Database Configuration
db_host=localhost
db_port=5432
db_name=systemdb
""")
    
    # Cream fisiere de log
    (base / "logs" / "system.log").write_text("""[2025-01-15 10:00:00] System started
[2025-01-15 10:01:23] User admin logged in
[2025-01-15 10:05:45] Database connection established
[2025-01-15 10:10:12] Processing task #1234
""")
    
    (base / "logs" / "error.log").write_text("""[2025-01-15 10:03:15] WARNING: High memory usage detected
[2025-01-15 10:07:32] ERROR: Failed to connect to external service
""")
    
    # Cream fisiere de date
    (base / "data" / "users.txt").write_text("""admin:1001
john:1002
mary:1003
""")
    
    (base / "data" / "README.md").write_text("""# Data Directory

This directory contains system data files.

## Files:
- users.txt: List of system users
""")
    
    # Cream un fișier in root
    (base / "system_info.txt").write_text("""System: Linux
Version: 5.15.0
Architecture: x86_64
""")
    
    print(f"Test environment created successfully in: {BASE_DIR}")
    print("\nDirectory structure:")
    for root, dirs, files in os.walk(BASE_DIR):
        level = root.replace(BASE_DIR, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f'{indent}{os.path.basename(root)}/')
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f'{subindent}{file}')


if __name__ == "__main__":
    setup_test_environment()