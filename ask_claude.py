#!/usr/bin/env python3
"""Send a prompt to Claude. Reads system prompt from a file, user content from stdin.

Usage:
    cat report.txt | python ask_claude.py system_prompt.txt
    cat report.txt | python ask_claude.py system_prompt.txt --schema schema.json
    cat report.txt | python ask_claude.py system_prompt.txt claude-sonnet-4-6
"""

import json
import os
import sys

import anthropic

# Pricing per 1M tokens (input, output) — for the cost display
PRICING = {
    "claude-haiku-4-5":  (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-6":   (5.00, 25.00),
}


def send_message(system_prompt, user_content, model="claude-haiku-4-5", api_key=None, schema=None, temperature=None):
    """Send a message to Claude and return the result.

    If schema is provided, uses tool_use to get structured JSON output.
    If temperature is set, controls sampling randomness (0.0 = deterministic).
    """
    client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])

    kwargs = {
        "model": model,
        "max_tokens": 2048,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
    }

    if temperature is not None:
        kwargs["temperature"] = temperature

    if schema:
        kwargs["tools"] = [{
            "name": "structured_output",
            "description": "Produce structured output matching the schema.",
            "input_schema": schema,
        }]
        kwargs["tool_choice"] = {"type": "tool", "name": "structured_output"}

    response = client.messages.create(**kwargs)

    if schema:
        text = json.dumps(
            next(b.input for b in response.content if b.type == "tool_use"),
            indent=2,
        )
    else:
        text = response.content[0].text

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    input_price, output_price = PRICING[model]
    cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000

    return {
        "text": text,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }


def format_result(result):
    """Format a result dict for terminal display."""
    lines = [
        result["text"],
        "",
        f"--- {result['model']} ---",
        f"Input:  {result['input_tokens']} tokens",
        f"Output: {result['output_tokens']} tokens",
        f"Cost:   ${result['cost_usd']:.6f}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: cat data.txt | python ask_claude.py system_prompt.txt [--schema schema.json] [model]", file=sys.stderr)
        sys.exit(1)

    args = list(sys.argv[1:])
    system_prompt = open(args.pop(0)).read().strip()
    user_content = sys.stdin.read().strip()

    schema = None
    if "--schema" in args:
        idx = args.index("--schema")
        schema = json.loads(open(args[idx + 1]).read())
        del args[idx:idx + 2]

    temperature = None
    if "--temperature" in args:
        idx = args.index("--temperature")
        temperature = float(args[idx + 1])
        del args[idx:idx + 2]

    model = args[0] if args else "claude-haiku-4-5"

    result = send_message(system_prompt, user_content, model, schema=schema, temperature=temperature)

    if schema:
        print(result["text"])
        print(format_result({**result, "text": ""}), file=sys.stderr)
    else:
        print(format_result(result))
