# tests/tools/test_repo_analyzer.py
import pytest
from pathlib import Path
from agents.tools.repo_analyzer import (
    scan_repo_structure,
    REPO_ANALYZER_TOOL,
    RepoStructureSummary,
)


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    """Creates a minimal repo structure in a temp directory."""
    (tmp_path / "src").mkdir()
    (tmp_path / "k8s").mkdir()
    (tmp_path / ".git").mkdir()
    (tmp_path / "__pycache__").mkdir()

    (tmp_path / "Dockerfile").write_text("FROM python:3.12-slim")
    (tmp_path / "README.md").write_text("# My Repo")
    (tmp_path / "src" / "app.py").write_text("print('hello')")
    (tmp_path / "src" / "config.py").write_text("DEBUG = False")
    (tmp_path / "k8s" / "deployment.yaml").write_text("apiVersion: apps/v1")
    (tmp_path / ".git" / "config").write_text("[core]")

    return tmp_path


class TestScanRepoStructure:
    def test_returns_correct_type(self, sample_repo: Path) -> None:
        result = scan_repo_structure(str(sample_repo))
        assert isinstance(result, RepoStructureSummary)

    def test_correct_file_count_excludes_ignored_dirs(self, sample_repo: Path) -> None:
        result = scan_repo_structure(str(sample_repo))
        assert result.total_files == 5

    def test_notable_files_detected(self, sample_repo: Path) -> None:
        result = scan_repo_structure(str(sample_repo))
        assert "Dockerfile" in result.notable_files
        assert "README.md" in result.notable_files

    def test_raises_on_nonexistent_path(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            scan_repo_structure("/nonexistent/path/xyz")

    def test_raises_on_file_not_directory(self, sample_repo: Path) -> None:
        file_path = str(sample_repo / "Dockerfile")
        with pytest.raises(ValueError, match="not a directory"):
            scan_repo_structure(file_path)

    def test_file_types_sorted_by_count(self, sample_repo: Path) -> None:
        result = scan_repo_structure(str(sample_repo))
        counts = [ft.count for ft in result.file_types]
        assert counts == sorted(counts, reverse=True)


class TestToolDefinition:
    def test_tool_has_required_keys(self) -> None:
        assert "name" in REPO_ANALYZER_TOOL
        assert "description" in REPO_ANALYZER_TOOL
        assert "input_schema" in REPO_ANALYZER_TOOL

    def test_repo_path_is_required(self) -> None:
        schema = REPO_ANALYZER_TOOL["input_schema"]
        assert "repo_path" in schema["required"]