import os
from pathlib import Path
from typing import Set, Tuple, List

EXCLUDE_DIRS = {
    ".git", ".venv", "venv", "build", "dist", "__pycache__", 
    "node_modules", ".idea", ".vscode", "html", "latex", "xml"
}

def scan_repo(repo_path: Path) -> Tuple[List[Path], List[Path]]:
    """
    Scans repository for Python and C++ source files, respecting .coopadocs config if present.
    Returns:
        (python_files, cpp_files)
    """
    config = {}
    config_files = [".coopadocs", ".coopadocs.yaml", ".coopadocs.yml"]
    for cf in config_files:
        cf_path = repo_path / cf
        if cf_path.exists():
            try:
                import yaml
                with open(cf_path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                break
            except Exception as e:
                print(f"Warning: Failed to parse config {cf}: {e}")
                
    includes = config.get("include", [])
    if isinstance(includes, str):
        includes = [includes]
        
    python_files = []
    cpp_files = []
    
    # Determine the target paths to scan
    scan_paths = []
    if includes:
        for inc in includes:
            inc_path = repo_path / inc
            if inc_path.exists():
                scan_paths.append(inc_path)
            else:
                print(f"Warning: Included path '{inc}' does not exist.")
    else:
        scan_paths.append(repo_path)
        
    for scan_path in scan_paths:
        for root, dirs, files in os.walk(scan_path):
            # In-place modify dirs to skip excluded ones
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()
                if ext == ".py":
                    python_files.append(file_path)
                elif ext in {".h", ".hpp", ".cpp", ".cc", ".cxx", ".c"}:
                    cpp_files.append(file_path)
                    
    return python_files, cpp_files
