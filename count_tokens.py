#!/usr/bin/env python3
"""Count tokens and show cost across all three Claude models.

Uses the /v1/messages/count_tokens API to count tokens WITHOUT
generating a response. Shows exactly what a message would cost
before you send it.

Usage:
    # Count tokens for text from stdin
    echo "Hello, Claude" | python count_tokens.py

    # Count tokens for a file
    cat demos/17_tokenomics/walden_excerpt.txt | python count_tokens.py

    # Count with a system prompt (shows the real cost of prompt overhead)
    cat demos/17_tokenomics/walden_excerpt.txt | python count_tokens.py \
        --system demos/17_tokenomics/system_prompt.txt

    # Count with system prompt AND tools (full agent cost)
    cat demos/17_tokenomics/walden_excerpt.txt | python count_tokens.py \
        --system demos/17_tokenomics/system_prompt.txt \
        --tools demos/17_tokenomics/tools.py
"""

import importlib.util
import json
import os
import sys

import anthropic

MODELS = [
    "claude-haiku-4-5",
    "claude-sonnet-4-6",
    "claude-opus-4-6",
]

PRICING_INPUT = {
    "claude-haiku-4-5":  1.00,
    "claude-sonnet-4-6": 3.00,
    "claude-opus-4-6":   15.00,
}


def calculate_input_cost(model, input_tokens):
    """Calculate the input cost in USD for a given model and token count."""
    price_per_mtok = PRICING_INPUT[model]
    return input_tokens * price_per_mtok / 1_000_000


def format_cost_table(rows):
    """Format token count rows as a table.

    Each row: {"model": str, "input_tokens": int}
    """
    lines = []
    lines.append(f"  {'Model':<22} {'Tokens':>8}  {'Input Cost':>12}")
    lines.append(f"  {'─' * 22} {'─' * 8}  {'─' * 12}")
    for row in rows:
        model = row["model"]
        tokens = row["input_tokens"]
        cost = calculate_input_cost(model, tokens)
        lines.append(f"  {model:<22} {tokens:>8,}  ${cost:>11.6f}")
    return "\n".join(lines)


def count_for_model(client, model, messages, system=None, tools=None):
    """Count tokens for a single model. Returns input_tokens."""
    kwargs = {
        "model": model,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools

    result = client.messages.count_tokens(**kwargs)
    return result.input_tokens


def main():
    args = list(sys.argv[1:])

    system_prompt = None
    if "--system" in args:
        idx = args.index("--system")
        system_prompt = open(args[idx + 1]).read().strip()
        del args[idx:idx + 2]

    tools = None
    if "--tools" in args:
        idx = args.index("--tools")
        tools_path = args[idx + 1]
        del args[idx:idx + 2]
        spec = importlib.util.spec_from_file_location("tools", tools_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tools = module.TOOL_DEFINITIONS

    user_content = sys.stdin.read().strip()
    if not user_content:
        print("Usage: echo 'text' | python count_tokens.py [--system FILE] [--tools FILE]",
              file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
    )
    messages = [{"role": "user", "content": user_content}]

    # Show what we're counting
    preview = user_content[:80] + ("..." if len(user_content) > 80 else "")
    print(f"[TEXT] {preview}")
    print(f"[CHARS] {len(user_content):,}")
    if system_prompt:
        print(f"[SYSTEM] {len(system_prompt):,} chars")
    if tools:
        print(f"[TOOLS] {len(tools)} tool definition(s)")
    print()

    rows = []
    for model in MODELS:
        tokens = count_for_model(
            client, model, messages,
            system=system_prompt, tools=tools,
        )
        rows.append({"model": model, "input_tokens": tokens})

    print(format_cost_table(rows))
    print()

    # Show the cost multiplier
    if len(rows) >= 2:
        cheapest = min(r["input_tokens"] for r in rows)
        for row in rows:
            if row["input_tokens"] != cheapest:
                # Cost comparison, not token comparison
                cheap_cost = calculate_input_cost(rows[0]["model"], rows[0]["input_tokens"])
                this_cost = calculate_input_cost(row["model"], row["input_tokens"])
                if cheap_cost > 0:
                    print(f"  {row['model']} costs {this_cost / cheap_cost:.1f}x vs {rows[0]['model']}")


if __name__ == "__main__":
    main()
