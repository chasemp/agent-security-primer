#!/usr/bin/env python3
"""MCP client — connect to an MCP server and run an agentic loop.

This is agent.py but with tools coming from an MCP server instead of
a Python module. Shows how MCP tool definitions become API tool_use
calls — the model sees the same JSON schema either way.

The client connects, discovers tools, then runs the standard loop:
  send task → model proposes tool_use → route call to MCP server → loop

Usage:
    # Inspect server tools (no LLM, no API key needed)
    python mcp_client.py demos/21_mcp_basics/server.py --inspect

    # Run with stdio transport (default — launches server as subprocess)
    cat task.txt | python mcp_client.py demos/21_mcp_basics/server.py

    # Run with HTTP transport (connect to running server)
    cat task.txt | python mcp_client.py http://localhost:8000/mcp

    # Verbose mode — show protocol messages
    cat task.txt | python mcp_client.py server.py --verbose
"""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager

import anthropic
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import (
    CreateMessageResult,
    Implementation,
    ListRootsResult,
    Root,
    TextContent,
)

PRICING = {
    "claude-haiku-4-5":  (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-6":   (5.00, 25.00),
}


def mcp_tool_to_anthropic(tool):
    """Convert an MCP Tool to Anthropic API tool format.

    MCP uses camelCase (inputSchema), Anthropic uses snake_case (input_schema).
    Otherwise the schemas are identical — both are JSON Schema objects.
    """
    return {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": tool.inputSchema,
    }


async def run_inspect(session, server_info=None):
    """Print server info and discovered tools. No LLM involved."""
    tools_result = await session.list_tools()
    tools = tools_result.tools

    if server_info:
        print(f"[SERVER] {server_info.name} v{server_info.version}")
    print(f"[TOOLS]  {len(tools)} tool(s) discovered")
    print()

    for tool in tools:
        print(f"  {tool.name}")
        if tool.description:
            print(f"    {tool.description}")
        props = tool.inputSchema.get("properties", {})
        if props:
            for prop_name, prop_def in props.items():
                ptype = prop_def.get("type", "any")
                desc = prop_def.get("description", "")
                line = f"    {prop_name}: {ptype}"
                if desc:
                    line += f"  — {desc}"
                print(line)
        print()


async def run_agent(session, task, model="claude-haiku-4-5",
                    api_key=None, max_turns=10, verbose=False,
                    server_info=None):
    """Run the agentic loop using MCP tools.

    Same loop as agent.py: send task → handle tool_use → route to server → repeat.
    """
    client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])

    tools_result = await session.list_tools()
    tool_defs = [mcp_tool_to_anthropic(t) for t in tools_result.tools]

    if verbose:
        name = server_info.name if server_info else "server"
        print(f"[HANDSHAKE] {name} — {len(tool_defs)} tool(s)")
        for td in tool_defs:
            print(f"  {td['name']}: {td['description']}")
        print()

    messages = [{"role": "user", "content": task}]
    steps = []
    total_input = 0
    total_output = 0
    turns = 0
    response_text = ""

    for _ in range(max_turns):
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            tools=tool_defs,
            messages=messages,
        )

        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens
        turns += 1

        if response.stop_reason != "tool_use":
            for block in response.content:
                if block.type == "text":
                    response_text += block.text
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            step = {"tool": block.name, "input": block.input,
                    "output": None, "error": None}

            if verbose:
                print(f"[TOOL CALL] {block.name}({json.dumps(block.input)})")

            try:
                result = await session.call_tool(block.name, block.input)
                output = ""
                for content in result.content:
                    if hasattr(content, "text"):
                        output += content.text
                step["output"] = output

                if verbose:
                    print(f"[TOOL RESULT] {output}")
                    print()

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": output,
                })
            except Exception as e:
                step["error"] = str(e)
                if verbose:
                    print(f"[TOOL ERROR] {e}")
                    print()
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(e),
                    "is_error": True,
                })

            steps.append(step)

        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    input_price, output_price = PRICING[model]
    cost = (total_input * input_price + total_output * output_price) / 1_000_000

    return {
        "response": response_text,
        "steps": steps,
        "turns": turns,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "cost_usd": cost,
        "model": model,
    }


def format_mcp_result(result):
    """Format an MCP agent result for terminal display."""
    lines = []

    for i, step in enumerate(result["steps"], 1):
        lines.append(f"[TOOL CALL {i}] {step['tool']}({json.dumps(step['input'])})")
        if step["error"]:
            lines.append(f"[TOOL ERROR] {step['error']}")
        else:
            lines.append(f"[TOOL RESULT] {step['output']}")
        lines.append("")

    if result["response"]:
        lines.append(f"[RESPONSE] {result['response']}")
    lines.append("")
    lines.append(f"--- {result['model']} ({result['turns']} turns) ---")
    lines.append(f"Input:  {result['total_input_tokens']} tokens")
    lines.append(f"Output: {result['total_output_tokens']} tokens")
    lines.append(f"Cost:   ${result['cost_usd']:.6f}")
    return "\n".join(lines)


# --- Client-side callbacks for server-initiated requests ---

async def handle_roots_request(context):
    """Respond to server's roots/list request.

    This is what the server calls to discover your filesystem layout.
    In a real client (Claude Desktop, VS Code), this returns your
    project directories. Here we return a realistic-looking path.
    """
    return ListRootsResult(roots=[
        Root(uri="file:///Users/demo/git/my-project", name="my-project"),
    ])


async def handle_sampling_request(context, params):
    """Respond to server's sampling/createMessage request.

    The server is asking our LLM to generate a response on the
    server's behalf. This is the most powerful server-initiated
    capability — the server controls the prompt.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return CreateMessageResult(
            role="assistant",
            content=TextContent(type="text", text="[sampling unavailable]"),
            model="none",
        )

    client = anthropic.Anthropic(api_key=api_key)

    messages = []
    for msg in params.messages:
        content = msg.content
        if hasattr(content, "text"):
            content = content.text
        messages.append({"role": msg.role, "content": content})

    kwargs = {
        "model": "claude-haiku-4-5",
        "max_tokens": params.maxTokens,
        "messages": messages,
    }
    if params.systemPrompt:
        kwargs["system"] = params.systemPrompt

    response = client.messages.create(**kwargs)
    text = response.content[0].text if response.content else ""

    return CreateMessageResult(
        role="assistant",
        content=TextContent(type="text", text=text),
        model="claude-haiku-4-5",
    )


@asynccontextmanager
async def connect(target, verbose=False):
    """Connect to an MCP server via stdio or HTTP.

    Yields (session, server_info) tuple.
    If target starts with http, use HTTP transport.
    Otherwise treat it as a path and launch via stdio.
    """
    client_info = Implementation(name="mcp-demo-client", version="1.0.0")

    if target.startswith("http"):
        if verbose:
            print(f"[TRANSPORT] HTTP → {target}")
        async with streamablehttp_client(target) as (read, write, _get_session_id):
            async with ClientSession(
                read, write,
                client_info=client_info,
                list_roots_callback=handle_roots_request,
                sampling_callback=handle_sampling_request,
            ) as session:
                init_result = await session.initialize()
                yield session, init_result.serverInfo
    else:
        if verbose:
            print(f"[TRANSPORT] stdio → python {target}")
        params = StdioServerParameters(
            command=sys.executable,
            args=[target],
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(
                read, write,
                client_info=client_info,
                list_roots_callback=handle_roots_request,
                sampling_callback=handle_sampling_request,
            ) as session:
                init_result = await session.initialize()
                yield session, init_result.serverInfo


async def main():
    args = list(sys.argv[1:])

    if not args:
        print("Usage: python mcp_client.py <server.py | http://url> [options]",
              file=sys.stderr)
        print("  --inspect      Show server tools and exit (no LLM)", file=sys.stderr)
        print("  --verbose      Show protocol messages", file=sys.stderr)
        print("  --model MODEL  Model to use (default: claude-haiku-4-5)", file=sys.stderr)
        sys.exit(1)

    target = args.pop(0)

    inspect_mode = False
    if "--inspect" in args:
        args.remove("--inspect")
        inspect_mode = True

    verbose = False
    if "--verbose" in args:
        args.remove("--verbose")
        verbose = True

    model = "claude-haiku-4-5"
    if "--model" in args:
        idx = args.index("--model")
        model = args[idx + 1]
        del args[idx:idx + 2]

    async with connect(target, verbose=verbose) as (session, server_info):
        if inspect_mode:
            await run_inspect(session, server_info=server_info)
        else:
            task = sys.stdin.read().strip()
            result = await run_agent(session, task, model=model,
                                     verbose=verbose, server_info=server_info)
            print(format_mcp_result(result))


if __name__ == "__main__":
    asyncio.run(main())
