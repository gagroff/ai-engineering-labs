# tests/tools/test_system_info.py
"""
Unit tests for the system_info tool.
Tests the Python function in isolation — NOT the Anthropic API.
Run with: pytest tests/tools/test_system_info.py -v
"""

import pytest
from agents.tools.system_info import get_system_info, SYSTEM_INFO_TOOL


class TestGetSystemInfo:
    def test_known_host_returns_metrics(self) -> None:
        """prod-api-01 should return the specific fake metrics we defined."""
        result = get_system_info("prod-api-01")
        assert result["hostname"] == "prod-api-01"
        assert result["cpu_pct"] == 78
        assert result["status"] == "degraded"

    def test_unknown_host_returns_error_field(self) -> None:
        """A host not in inventory should return an error field, not raise an exception."""
        result = get_system_info("nonexistent-host")
        assert "error" in result
        assert result["status"] == "unknown"

    def test_all_known_hosts_return_status(self) -> None:
        """Every known host should return a valid status string."""
        for hostname in ["prod-api-01", "prod-db-01", "prod-lb-01"]:
            result = get_system_info(hostname)
            assert "status" in result
            assert result["status"] in {"healthy", "degraded", "critical"}


class TestToolDefinition:
    def test_tool_has_required_keys(self) -> None:
        """The tool definition dict must have all three keys the API expects."""
        assert "name" in SYSTEM_INFO_TOOL
        assert "description" in SYSTEM_INFO_TOOL
        assert "input_schema" in SYSTEM_INFO_TOOL

    def test_input_schema_requires_hostname(self) -> None:
        """hostname must be both defined in properties AND listed as required."""
        schema = SYSTEM_INFO_TOOL["input_schema"]
        assert "hostname" in schema["properties"]
        assert "hostname" in schema["required"]