#!/usr/bin/env python3
"""Send a prompt to Claude. Reads system prompt from a file, user content from stdin.

Usage:
    cat report.txt | python ask_claude.py system_prompt.txt
    cat report.txt | python ask_claude.py system_prompt.txt --model claude-sonnet-4-6
    cat report.txt | python ask_claude.py system_prompt.txt --schema schema.json
    cat report.txt | python ask_claude.py system_prompt.txt --thinking
    cat report.txt | python ask_claude.py system_prompt.txt --temperature 0
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


def send_message(system_prompt, user_content, model="claude-haiku-4-5",
                 api_key=None, schema=None, temperature=None, thinking=False,
                 effort=None):
    """Send a message to Claude and return the result.

    thinking: False to disable, True for default budget (5000),
              an int to set a specific budget_tokens value,
              or "adaptive" for Claude to decide when/how much to think.
    effort: None, or "low"/"medium"/"high"/"max" to control token spend.
            Works with or without thinking. Controls ALL output tokens.
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

    if thinking == "adaptive":
        kwargs["thinking"] = {"type": "adaptive"}
        kwargs["max_tokens"] = 16000
    elif thinking:
        budget = thinking if isinstance(thinking, int) and thinking is not True else 5000
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
        kwargs["max_tokens"] = max(budget + 4096, 16000)

    if effort:
        kwargs["output_config"] = {"effort": effort}

    if schema:
        kwargs["tools"] = [{
            "name": "structured_output",
            "description": "Produce structured output matching the schema.",
            "input_schema": schema,
        }]
        kwargs["tool_choice"] = {"type": "tool", "name": "structured_output"}

    response = client.messages.create(**kwargs)

    # Extract text from response blocks
    thinking_text = None
    text = ""

    if schema:
        text = json.dumps(
            next(b.input for b in response.content if b.type == "tool_use"),
            indent=2,
        )
    elif thinking:
        parts = []
        for block in response.content:
            if block.type == "thinking":
                thinking_text = block.thinking
            elif block.type == "text":
                parts.append(block.text)
        text = "".join(parts)
    else:
        text = response.content[0].text

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    input_price, output_price = PRICING[model]
    cost = (input_tokens * input_price + output_tokens * output_price) / 1_000_000

    return {
        "text": text,
        "thinking": thinking_text,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost,
    }


def format_result(result):
    """Format a result dict for terminal display."""
    lines = []

    if result.get("thinking"):
        lines.append("[THINKING]")
        lines.append(result["thinking"])
        lines.append("")
        lines.append("[RESPONSE]")

    lines.append(result["text"])
    lines.append("")
    lines.append(f"--- {result['model']} ---")
    lines.append(f"Input:  {result['input_tokens']} tokens")
    lines.append(f"Output: {result['output_tokens']} tokens")
    lines.append(f"Cost:   ${result['cost_usd']:.6f}")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: cat data.txt | python ask_claude.py system_prompt.txt [options]", file=sys.stderr)
        print("  --model MODEL        Model to use (default: claude-haiku-4-5)", file=sys.stderr)
        print("  --schema FILE        Force structured JSON output via tool_use", file=sys.stderr)
        print("  --thinking [N]       Enable extended thinking (budget_tokens, default 5000)", file=sys.stderr)
        print("  --adaptive           Adaptive thinking (Claude decides when/how much)", file=sys.stderr)
        print("  --effort LEVEL       Token spend control: low, medium, high, max", file=sys.stderr)
        print("  --temperature N      Sampling temperature (0=deterministic)", file=sys.stderr)
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

    enable_thinking = False
    if "--adaptive" in args:
        args.remove("--adaptive")
        enable_thinking = "adaptive"
    elif "--thinking" in args:
        idx = args.index("--thinking")
        # Check if next arg is a number (budget), otherwise default
        if idx + 1 < len(args) and args[idx + 1].isdigit():
            enable_thinking = int(args[idx + 1])
            del args[idx:idx + 2]
        else:
            enable_thinking = True
            del args[idx]

    effort = None
    if "--effort" in args:
        idx = args.index("--effort")
        effort = args[idx + 1]
        del args[idx:idx + 2]

    model = "claude-haiku-4-5"
    if "--model" in args:
        idx = args.index("--model")
        model = args[idx + 1]
        del args[idx:idx + 2]
    elif args:
        model = args[0]

    result = send_message(system_prompt, user_content, model,
                          schema=schema, temperature=temperature,
                          thinking=enable_thinking, effort=effort)

    if schema:
        print(result["text"])
        print(format_result({**result, "text": ""}), file=sys.stderr)
    else:
        print(format_result(result))
