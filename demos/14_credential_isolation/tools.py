"""Isolated tools — credentials never enter the context window.

The tool connects to the database using credentials stored in its
own scope. The model only sees the query and the results. No
connection strings, no passwords, no API keys.

Compare to Demo 9: same data, same query capability. But the model
has no tool to read configuration, and the query tool doesn't expose
its connection details.

The credential lives in YOUR code. It travels through YOUR code.
It never becomes a token in the model's context.
"""

import json


# Credentials live here — in the tool's scope, not the model's context.
# In production, this reads from os.environ or a secrets manager.
# The model has no way to access this variable.
_DATABASE_URL = "postgresql://admin:s3cret_P@ssw0rd_2026@db-primary.internal:5432/infradb"

# Simulated query results (same data as Demo 9)
_SERVERS_IN_RACK_7 = [
    {"server_id": "SRV-1002", "name": "payments-db", "rack": 7, "status": "running"},
    {"server_id": "SRV-1003", "name": "cache-west", "rack": 7, "status": "degraded"},
]


def query_database(query):
    """Query the database. Connects using internal credentials.
    Returns only the query results — never the connection details."""
    # In production: use _DATABASE_URL to connect, execute query, return rows.
    # The credential is used but never exposed in the return value.
    if "rack" in query.lower() and "7" in query:
        return json.dumps({"results": _SERVERS_IN_RACK_7})
    return json.dumps({"results": [], "message": "No results"})


# No read_config tool. The model can query data but cannot
# inspect the environment. This is least privilege: the model
# gets the capability it needs (query) without the capability
# it doesn't (read secrets).

TOOL_DEFINITIONS = [
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
    "query_database": query_database,
}
