"""Server operations tools — query status, health, logs, and maintenance.

A realistic set of tools for an infrastructure operations agent.
Production agents commonly have 5-10+ tools with detailed schemas —
these tool definitions are re-sent to the API every turn, making
them a significant caching opportunity.

This demo uses 6 tools to show that caching tool definitions
alongside the system prompt reduces per-turn cost.
"""

import json


# Simulated server inventory by rack
_SERVERS = {
    7: [
        {"server_id": "SRV-1001", "name": "web-prod-1", "rack": 7, "status": "running"},
        {"server_id": "SRV-1002", "name": "api-prod-3", "rack": 7, "status": "running"},
        {"server_id": "SRV-1003", "name": "cache-west", "rack": 7, "status": "degraded"},
        {"server_id": "SRV-1004", "name": "worker-batch", "rack": 7, "status": "running"},
    ],
    12: [
        {"server_id": "SRV-2001", "name": "web-prod-5", "rack": 12, "status": "running"},
        {"server_id": "SRV-2002", "name": "db-replica-2", "rack": 12, "status": "maintenance"},
        {"server_id": "SRV-2003", "name": "api-prod-7", "rack": 12, "status": "running"},
    ],
}

# Simulated health metrics
_HEALTH = {
    "SRV-1001": {"cpu": 45, "memory": 62, "disk": 38, "packet_loss": 0.01, "p95_ms": 120},
    "SRV-1002": {"cpu": 55, "memory": 58, "disk": 42, "packet_loss": 0.02, "p95_ms": 95},
    "SRV-1003": {"cpu": 88, "memory": 91, "disk": 55, "packet_loss": 1.5, "p95_ms": 450},
    "SRV-1004": {"cpu": 30, "memory": 45, "disk": 35, "packet_loss": 0.0, "p95_ms": 80},
    "SRV-2001": {"cpu": 40, "memory": 55, "disk": 50, "packet_loss": 0.01, "p95_ms": 110},
    "SRV-2002": {"cpu": 0, "memory": 0, "disk": 72, "packet_loss": 0.0, "p95_ms": 0},
    "SRV-2003": {"cpu": 52, "memory": 60, "disk": 44, "packet_loss": 0.03, "p95_ms": 105},
}

# Simulated recent log entries
_LOGS = {
    "SRV-1003": [
        {"timestamp": "2026-04-08T14:32:01Z", "level": "ERROR", "message": "Redis connection pool exhausted, 12 clients waiting"},
        {"timestamp": "2026-04-08T14:31:45Z", "level": "WARN", "message": "Memory pressure: OOM killer threshold at 88%"},
        {"timestamp": "2026-04-08T14:30:12Z", "level": "ERROR", "message": "Packet loss spike detected on eth0: 1.5%"},
    ],
    "SRV-2002": [
        {"timestamp": "2026-04-08T12:00:00Z", "level": "INFO", "message": "Maintenance window started: scheduled replication sync"},
        {"timestamp": "2026-04-08T11:59:30Z", "level": "INFO", "message": "Draining connections for maintenance"},
    ],
}

# Simulated maintenance windows
_MAINTENANCE = {
    "SRV-2002": {
        "window_id": "MW-2026-0408",
        "start": "2026-04-08T12:00:00Z",
        "end": "2026-04-08T18:00:00Z",
        "reason": "Scheduled replication sync and index rebuild",
        "approved_by": "ops-team",
    },
}

# Simulated network topology
_TOPOLOGY = {
    7: {
        "switch": "TOR-7A",
        "uplink": "CORE-EAST-1",
        "vlan": 107,
        "subnet": "10.1.7.0/24",
        "gateway": "10.1.7.1",
        "dns": ["10.0.0.53", "10.0.0.54"],
    },
    12: {
        "switch": "TOR-12A",
        "uplink": "CORE-EAST-2",
        "vlan": 112,
        "subnet": "10.1.12.0/24",
        "gateway": "10.1.12.1",
        "dns": ["10.0.0.53", "10.0.0.54"],
    },
}


def query_servers(rack):
    """List all servers in a rack."""
    rack_num = int(rack)
    servers = _SERVERS.get(rack_num, [])
    if not servers:
        return json.dumps({"results": [], "message": f"No servers found in rack {rack_num}"})
    return json.dumps({"results": servers})


def check_health(server_id):
    """Get health metrics for a specific server."""
    metrics = _HEALTH.get(server_id)
    if not metrics:
        return json.dumps({"error": f"No health data for {server_id}"})
    return json.dumps({"server_id": server_id, "metrics": metrics})


def get_logs(server_id, level="ALL"):
    """Get recent log entries for a server, optionally filtered by level."""
    entries = _LOGS.get(server_id, [])
    if level != "ALL":
        entries = [e for e in entries if e["level"] == level.upper()]
    if not entries:
        return json.dumps({"server_id": server_id, "logs": [], "message": "No recent log entries"})
    return json.dumps({"server_id": server_id, "logs": entries})


def get_maintenance_window(server_id):
    """Check if a server has an active or scheduled maintenance window."""
    window = _MAINTENANCE.get(server_id)
    if not window:
        return json.dumps({"server_id": server_id, "maintenance": None, "message": "No maintenance window"})
    return json.dumps({"server_id": server_id, "maintenance": window})


def get_network_topology(rack):
    """Get network topology information for a rack."""
    rack_num = int(rack)
    topo = _TOPOLOGY.get(rack_num)
    if not topo:
        return json.dumps({"error": f"No topology data for rack {rack_num}"})
    return json.dumps({"rack": rack_num, "topology": topo})


def list_racks(datacenter="US-EAST-1"):
    """List all rack numbers in a data center."""
    dc_racks = {
        "US-EAST-1": list(range(1, 21)),
        "US-WEST-2": list(range(21, 41)),
        "EU-CENTRAL-1": list(range(41, 61)),
    }
    racks = dc_racks.get(datacenter.upper())
    if not racks:
        return json.dumps({"error": f"Unknown data center: {datacenter}"})
    return json.dumps({"datacenter": datacenter, "racks": racks})


TOOL_DEFINITIONS = [
    {
        "name": "query_servers",
        "description": "List all servers in a given rack number. Returns server ID, name, rack, and current status for each server.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rack": {
                    "type": "integer",
                    "description": "Rack number to query (1-60)",
                },
            },
            "required": ["rack"],
        },
    },
    {
        "name": "check_health",
        "description": "Get detailed health metrics for a specific server including CPU utilization, memory utilization, disk utilization, network packet loss percentage, and p95 response time in milliseconds.",
        "input_schema": {
            "type": "object",
            "properties": {
                "server_id": {
                    "type": "string",
                    "description": "Server ID (e.g., SRV-1001)",
                },
            },
            "required": ["server_id"],
        },
    },
    {
        "name": "get_logs",
        "description": "Get recent log entries for a server. Returns timestamped log messages with severity levels. Use the level filter to focus on errors or warnings during incident investigation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "server_id": {
                    "type": "string",
                    "description": "Server ID (e.g., SRV-1001)",
                },
                "level": {
                    "type": "string",
                    "description": "Filter by log level. Options: ALL, ERROR, WARN, INFO. Default: ALL",
                    "enum": ["ALL", "ERROR", "WARN", "INFO"],
                },
            },
            "required": ["server_id"],
        },
    },
    {
        "name": "get_maintenance_window",
        "description": "Check if a server has an active or scheduled maintenance window. Returns window ID, start/end times, reason for maintenance, and who approved it. Returns null if no maintenance window exists.",
        "input_schema": {
            "type": "object",
            "properties": {
                "server_id": {
                    "type": "string",
                    "description": "Server ID (e.g., SRV-2002)",
                },
            },
            "required": ["server_id"],
        },
    },
    {
        "name": "get_network_topology",
        "description": "Get network topology information for a rack including top-of-rack switch, uplink to core switch, VLAN ID, subnet CIDR, gateway IP, and DNS server addresses. Useful for diagnosing network-related issues or checking connectivity paths.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rack": {
                    "type": "integer",
                    "description": "Rack number to query (1-60)",
                },
            },
            "required": ["rack"],
        },
    },
    {
        "name": "list_racks",
        "description": "List all rack numbers in a data center. Use this to discover available racks before querying individual rack contents. Data centers: US-EAST-1 (racks 1-20, production), US-WEST-2 (racks 21-40, staging), EU-CENTRAL-1 (racks 41-60, EU customer-facing).",
        "input_schema": {
            "type": "object",
            "properties": {
                "datacenter": {
                    "type": "string",
                    "description": "Data center identifier. Options: US-EAST-1, US-WEST-2, EU-CENTRAL-1. Default: US-EAST-1",
                    "enum": ["US-EAST-1", "US-WEST-2", "EU-CENTRAL-1"],
                },
            },
        },
    },
]

TOOL_HANDLERS = {
    "query_servers": query_servers,
    "check_health": check_health,
    "get_logs": get_logs,
    "get_maintenance_window": get_maintenance_window,
    "get_network_topology": get_network_topology,
    "list_racks": list_racks,
}
