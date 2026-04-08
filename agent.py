#!/usr/bin/env python3
"""Run a simple agent with tools. System prompt from file, task from stdin.

This is a minimal agentic loop: send a message, check if the model wants
to call a tool, execute it, send the result back, repeat until done.

Tools are defined in a Python module with:
  TOOL_DEFINITIONS — list of tool schemas (sent to the API)
  TOOL_HANDLERS    — dict mapping tool names to handler functions

Usage:
    cat task.txt | python agent.py system_prompt.txt --tools tools.py
    cat task.txt | python agent.py system_prompt.txt --tools tools.py --model claude-sonnet-4-6
"""

import importlib.util
import json
import os
import sys

import anthropic

PRICING = {
    "claude-haiku-4-5":  (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-6":   (5.00, 25.00),
}


def run_agent(system_prompt, task, tools_module, model="claude-haiku-4-5",
              api_key=None, max_turns=10, plan=False):
    """Run the agent loop. Returns a result dict with response, steps, and cost.

    If plan is True, shows proposed tool calls without executing them.
    This is 'terraform plan' for agents — the model proposes, you review.
    """
    client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])

    tool_defs = tools_module.TOOL_DEFINITIONS
    handlers = tools_module.TOOL_HANDLERS

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
            system=system_prompt,
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

        # In plan mode, record proposed calls and stop
        if plan:
            for block in response.content:
                if block.type == "tool_use":
                    steps.append({"tool": block.name, "input": block.input,
                                  "output": None, "error": None})
            break

        # Execute each tool call
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            handler = handlers[block.name]
            step = {"tool": block.name, "input": block.input, "output": None, "error": None}

            try:
                result = handler(**block.input)
                step["output"] = result
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
            except Exception as e:
                step["error"] = str(e)
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
        "plan": plan,
    }


def format_agent_result(result):
    """Format an agent result for terminal display."""
    lines = []

    if result.get("plan"):
        lines.append("[DRY RUN — proposed actions, not executed]")
        lines.append("")

    for i, step in enumerate(result["steps"], 1):
        if result.get("plan"):
            lines.append(f"[PROPOSED {i}] {step['tool']}({json.dumps(step['input'])})")
        else:
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


def load_tools_module(path):
    """Load a Python file as a module."""
    spec = importlib.util.spec_from_file_location("tools", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: cat task.txt | python agent.py system_prompt.txt --tools tools.py", file=sys.stderr)
        sys.exit(1)

    args = list(sys.argv[1:])
    system_prompt = open(args.pop(0)).read().strip()
    task = sys.stdin.read().strip()

    tools_path = None
    if "--tools" in args:
        idx = args.index("--tools")
        tools_path = args[idx + 1]
        del args[idx:idx + 2]

    model = "claude-haiku-4-5"
    if "--model" in args:
        idx = args.index("--model")
        model = args[idx + 1]
        del args[idx:idx + 2]

    plan = False
    if "--plan" in args:
        args.remove("--plan")
        plan = True

    if not tools_path:
        print("Error: --tools is required", file=sys.stderr)
        sys.exit(1)

    tools_module = load_tools_module(tools_path)
    result = run_agent(system_prompt, task, tools_module, model=model, plan=plan)
    print(format_agent_result(result))
