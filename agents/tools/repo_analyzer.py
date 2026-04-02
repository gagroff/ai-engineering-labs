# agents/tools/repo_analyzer.py
"""
Tool definition and implementation for the IT Ops Repo Analyzer.
Scans a repository and produces a structured summary of its layout
and detected infrastructure patterns.
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# ── Output schemas ─────────────────────────────────────────────────────────────

class FileTypeSummary(BaseModel):
    """Count of files by extension within the repo."""
    extension: str
    count: int
    example_paths: list[str] = Field(default_factory=list)


class DirectoryNode(BaseModel):
    """Lightweight representation of a directory in the repo tree."""
    name: str
    path: str
    file_count: int
    subdirectory_count: int


class RepoStructureSummary(BaseModel):
    """
    Structured summary of a repository's file layout.
    Produced by the scan_repo_structure tool.
    """
    root_path: str
    total_files: int
    total_directories: int
    total_size_bytes: int
    file_types: list[FileTypeSummary]
    top_level_directories: list[DirectoryNode]
    notable_files: list[str] = Field(
        default_factory=list,
        description="Files at repo root that are significant: Dockerfile, README, etc."
    )


# ── Tool definition ─────────────────────────────────────────────────────────────

REPO_ANALYZER_TOOL: dict[str, Any] = {
    "name": "scan_repo_structure",
    "description": (
        "Scans a local repository directory and returns a structured summary of its file layout. "
        "Reports total file and directory counts, file type breakdown, top-level directory structure, "
        "and notable root-level files. Use this tool when asked to analyze, summarize, or understand "
        "the structure of a code repository or infrastructure project."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "repo_path": {
                "type": "string",
                "description": "Absolute or relative path to the repository root directory to scan."
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum directory depth to traverse. Defaults to 5.",
                "default": 5
            },
            "include_hidden": {
                "type": "boolean",
                "description": "Whether to include hidden files and directories (starting with '.'). Defaults to false.",
                "default": False
            }
        },
        "required": ["repo_path"]
    }
}


# ── Constants ──────────────────────────────────────────────────────────────────

ALWAYS_IGNORE_DIRS: set[str] = {
    "__pycache__", ".git", ".venv", "venv", "env",
    "node_modules", ".terraform", "dist", "build", ".pytest_cache",
    ".mypy_cache", ".ruff_cache",
}

NOTABLE_ROOT_FILES: set[str] = {
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "Makefile", "README.md", "README.rst",
    "pyproject.toml", "setup.py", "requirements.txt",
    "package.json", ".github",
}


# ── Scanner implementation ─────────────────────────────────────────────────────

def scan_repo_structure(
    repo_path: str,
    max_depth: int = 5,
    include_hidden: bool = False,
) -> RepoStructureSummary:
    """
    Walks the repository tree and produces a structured layout summary.

    Args:
        repo_path: Path to the repository root.
        max_depth: Maximum traversal depth.
        include_hidden: Whether to include hidden files/dirs.

    Returns:
        RepoStructureSummary with file counts, type breakdown, and directory structure.

    Raises:
        ValueError: If repo_path does not exist or is not a directory.
    """
    # Resolve to an absolute path and validate it's an existing directory
    root = Path(repo_path).resolve()

    if not root.exists():
        raise ValueError(f"Path does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"Path is not a directory: {root}")

    # Accumulators updated by both the top-level loop and the recursive _walk
    total_files: int = 0
    total_dirs: int = 0
    total_size: int = 0
    ext_counts: dict[str, list[str]] = {}  # extension -> list of relative paths
    top_level_dirs: list[DirectoryNode] = []
    notable_files: list[str] = []

    # Collect any well-known root-level files (Dockerfile, README, etc.) before walking
    for item in sorted(root.iterdir()):
        if item.name in NOTABLE_ROOT_FILES:
            notable_files.append(item.name)

    def _should_skip(path: Path) -> bool:
        """Return True if this path should be excluded from the scan."""
        if path.name in ALWAYS_IGNORE_DIRS:
            return True
        # Optionally skip dotfiles / hidden directories
        if not include_hidden and path.name.startswith("."):
            return True
        return False

    def _walk(current: Path, depth: int) -> tuple[int, int]:
        """
        Recursively walk `current`, counting files and subdirectories.
        Updates the outer-scope totals (total_files, total_dirs, total_size, ext_counts).
        Returns (file_count, dir_count) for the immediate children of `current`.
        """
        # Mutate the enclosing function's accumulators directly rather than
        # passing them around, since _walk recurses and returning aggregates
        # up the call stack would require extra merging logic.
        nonlocal total_files, total_dirs, total_size

        # Local counters track only the *immediate* children of `current`,
        # so the caller can build DirectoryNode entries with per-directory counts.
        file_count = 0
        dir_count = 0

        # Stop recursing once we hit the depth limit
        if depth > max_depth:
            return file_count, dir_count

        try:
            entries = sorted(current.iterdir())
        except PermissionError:
            # Skip directories we can't read
            return file_count, dir_count

        for entry in entries:
            if _should_skip(entry):
                continue

            if entry.is_file():
                total_files += 1
                file_count += 1
                try:
                    total_size += entry.stat().st_size
                except OSError:
                    pass  # Skip files whose size can't be read (e.g. broken symlinks)
                # Normalize extension to lowercase; use a sentinel for files with no extension
                ext = entry.suffix.lower() if entry.suffix else "(no extension)"
                rel_path = str(entry.relative_to(root))
                if ext not in ext_counts:
                    ext_counts[ext] = []
                ext_counts[ext].append(rel_path)

            elif entry.is_dir():
                total_dirs += 1   # global tally
                dir_count += 1    # immediate-child tally returned to caller
                _walk(entry, depth + 1)

        return file_count, dir_count

    # Iterate top-level items to build DirectoryNode entries and tally root-level files.
    # Subdirectories are walked starting at depth=2 (root=1, first subdir=2) so that
    # max_depth is measured consistently from the repo root across all recursive calls.
    for item in sorted(root.iterdir()):
        if _should_skip(item):
            continue
        if item.is_dir():
            sub_files, sub_dirs = _walk(item, depth=2)
            top_level_dirs.append(DirectoryNode(
                name=item.name,
                path=str(item.relative_to(root)),
                file_count=sub_files,
                subdirectory_count=sub_dirs,
            ))
        elif item.is_file():
            # Count root-level files directly; _walk is only called on directories,
            # so the root's own files must be tallied here to avoid undercounting.
            total_files += 1
            try:
                total_size += item.stat().st_size
            except OSError:
                pass
            ext = item.suffix.lower() if item.suffix else "(no extension)"
            rel_path = str(item.relative_to(root))
            if ext not in ext_counts:
                ext_counts[ext] = []
            ext_counts[ext].append(rel_path)

    # Build the file-type breakdown, sorted by frequency descending.
    # Only the first 3 example paths are kept per extension to keep the output concise.
    file_types = sorted(
        [
            FileTypeSummary(
                extension=ext,
                count=len(paths),
                example_paths=paths[:3],
            )
            for ext, paths in ext_counts.items()
        ],
        key=lambda x: x.count,
        reverse=True,
    )

    return RepoStructureSummary(
        root_path=str(root),
        total_files=total_files,
        total_directories=total_dirs,
        total_size_bytes=total_size,
        file_types=file_types,
        top_level_directories=top_level_dirs,
        notable_files=sorted(notable_files),
    )