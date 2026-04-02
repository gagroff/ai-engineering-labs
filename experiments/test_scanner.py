# experiments/test_scanner.py
"""Quick smoke test for the repo scanner. Run directly with: python experiments/test_scanner.py"""

import json
import sys
from pathlib import Path

# Ensure the project root is on sys.path so `agents` is importable when
# running this script directly (e.g. python experiments/test_scanner.py)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.tools.repo_analyzer import scan_repo_structure

result = scan_repo_structure("sample-devops-repo", include_hidden=True)

print(json.dumps(result.model_dump(), indent=2))

print(f"\n--- Summary ---")
print(f"Total files:       {result.total_files}")
print(f"Total directories: {result.total_directories}")
print(f"Total size:        {result.total_size_bytes} bytes")
print(f"Notable files:     {result.notable_files}")
print(f"File types found:  {[ft.extension for ft in result.file_types]}")