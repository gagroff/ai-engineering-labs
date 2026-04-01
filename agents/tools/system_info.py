# agents/tools/system_info.py
"""
Tool definition and implementation for system_info.
Follows Anthropic API tool use format.
"""

from typing import Any


# This dict is what you send to the Anthropic API in the `tools` parameter.
# The `input_schema` tells Claude what arguments the tool accepts.
SYSTEM_INFO_TOOL: dict[str, Any] = {
    "name": "get_system_info",
    "description": (
        "Retrieves current system health metrics for a named host. "
        "Returns CPU usage percentage, memory usage percentage, and disk usage percentage. "
        "Use this tool when the user asks about system health, resource usage, or host status."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "hostname": {
                "type": "string",
                "description": "The hostname or IP address of the system to check."
            }
        },
        "required": ["hostname"]
    }
}


def get_system_info(hostname: str) -> dict[str, Any]:
    """
    Simulated system info lookup.
    In a real IT Ops implementation, this would call a monitoring API
    (Datadog, Prometheus, Azure Monitor, etc.) or SSH into the host.
    """
    # Fake metrics — realistic enough to represent an IT Ops scenario
    fake_metrics: dict[str, dict[str, Any]] = {
        "prod-api-01": {"cpu_pct": 78, "memory_pct": 62, "disk_pct": 45, "status": "degraded"},
        "prod-db-01":  {"cpu_pct": 22, "memory_pct": 81, "disk_pct": 71, "status": "healthy"},
        "prod-lb-01":  {"cpu_pct": 14, "memory_pct": 38, "disk_pct": 23, "status": "healthy"},
    }

    if hostname in fake_metrics:
        return {"hostname": hostname, **fake_metrics[hostname]}

    return {
        "hostname": hostname,
        "cpu_pct": 0,
        "memory_pct": 0,
        "disk_pct": 0,
        "status": "unknown",
        "error": f"Host '{hostname}' not found in inventory"
    }

# Tool definition for list_hosts — note there are no parameters,
# so "properties" is empty and "required" is an empty list.
LIST_HOSTS_TOOL: dict[str, Any] = {
    "name": "list_hosts",
    "description": (
        "Returns the list of all known hostnames in the inventory. "
        "Use this tool when the user asks which hosts are available, "
        "what systems can be checked, or what hosts exist."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

def list_hosts() -> dict[str, Any]:
    """
    Returns all known hostnames in the inventory.
    In a real IT Ops implementation this would query a CMDB,
    Azure resource list, or Ansible inventory file.
    """
    return {
        "hosts": ["prod-api-01", "prod-db-01", "prod-lb-01"]
    }