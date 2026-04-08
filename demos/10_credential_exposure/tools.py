"""Vulnerable tools — credentials are accessible to the model.

This tool set includes read_config, which returns environment variable
values including database connection strings with embedded passwords.
The model can (and will) call this tool, putting credentials into
the context window.

.env solved the git problem — credentials aren't in source control.
But they're still in the process environment, and any tool that can
read env vars puts them one tool call away from the context window.
"""

import json


# Simulated environment — these would be os.environ in production.
# We simulate them so the demo doesn't use real credentials.
SIMULATED_ENV = {
    "DATABASE_URL": "postgresql://admin:s3cret_P@ssw0rd_2026@db-primary.internal:5432/infradb",
    "REDIS_URL": "redis://:r3dis_t0ken_x9f@cache-west.internal:6379/0",
    "API_SECRET": "sk-infra-7f3a2b1c9d4e4a8fb5c62e1d0f9a8b7c",
    "SMTP_PASSWORD": "mail_s3cret_2026!",
    "APP_ENV": "production",
    "LOG_LEVEL": "info",
}

# Simulated database query results
SERVERS_IN_RACK_7 = [
    {"server_id": "SRV-1002", "name": "payments-db", "rack": 7, "status": "running"},
    {"server_id": "SRV-1003", "name": "cache-west", "rack": 7, "status": "degraded"},
]


def read_config(key):
    """Read a configuration value. THIS IS THE VULNERABILITY.
    It returns env var values including secrets."""
    value = SIMULATED_ENV.get(key, None)
    if value is None:
        return json.dumps({"error": f"Config key '{key}' not found"})
    return json.dumps({"key": key, "value": value})


def query_database(query):
    """Run a database query. Returns simulated results."""
    if "rack" in query.lower() and "7" in query:
        return json.dumps({"rows": SERVERS_IN_RACK_7})
    return json.dumps({"rows": [], "message": "No results"})


TOOL_DEFINITIONS = [
    {
        "name": "read_config",
        "description": "Read a configuration or environment variable by key name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Configuration key to read (e.g., DATABASE_URL, APP_ENV)",
                },
            },
            "required": ["key"],
        },
    },
    {
        "name": "query_database",
        "description": "Query the infrastructure database for server information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "SQL query to execute",
                },
            },
            "required": ["query"],
        },
    },
]

TOOL_HANDLERS = {
    "read_config": read_config,
    "query_database": query_database,
}
