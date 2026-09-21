"""
Script pentru testarea automata a agentului AI.
"""

import os
import sys
from others.ai_agent import chat

# Setam directorul gestionat
os.environ["MANAGED_DIR"] = "D:\\ASO\\Proiect\\mcp_server\\agent.py"

def test_query(query: str, description: str):
    """Testeaza o intrebare si afiseaza rezultatul."""
    print("=" * 70)
    print(f"TEST: {description}")
    print("=" * 70)
    print(f"Query: {query}")
    print("-" * 70)
    
    try:
        response = chat.run(query)
        print(f"Response: {response}")
        print()
    except Exception as e:
        print(f"ERROR: {str(e)}")
        print()
    
    return True


def run_tests():
    """Ruleaza o serie de teste pentru agentul AI."""
    
    print("\n" + "=" * 70)
    print("STARTING AUTOMATED AGENT TESTS")
    print("=" * 70 + "\n")
    
    # Test 1: Listare directoare
    test_query(
        "What directories and files are in the root of the managed system?",
        "Listing root directory"
    )
    
    # Test 2: Citire fisier de configurare
    test_query(
        "Can you show me the content of the file config/settings.conf?",
        "Reading configuration file"
    )
    
    # Test 3: Explorare structura directoare
    test_query(
        "What subdirectories exist and what files are in the logs directory?",
        "Exploring logs directory structure"
    )
    
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    # Verificam daca mediul de test exista
    if not os.path.exists("/managed_system"):
        print("ERROR: Test environment not found!")
        print("Please run: python setup_test_env.py")
        sys.exit(1)
    
    run_tests()