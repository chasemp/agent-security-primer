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
              api_key=None, max_turns=10, plan=False, cache=False,
              thinking=False, max_tokens_budget=None):
    """Run the agent loop. Returns a result dict with response, steps, and cost.

    If plan is True, shows proposed tool calls without executing them.
    This is 'terraform plan' for agents — the model proposes, you review.

    If cache is True, wraps system prompt with cache_control for prompt caching.
    If thinking is True, enables extended thinking (reasoning tokens).
    If max_tokens_budget is set, stops the loop when cumulative tokens exceed it.
    """
    client = anthropic.Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])

    tool_defs = tools_module.TOOL_DEFINITIONS
    handlers = tools_module.TOOL_HANDLERS

    if cache:
        system = [{"type": "text", "text": system_prompt,
                   "cache_control": {"type": "ephemeral"}}]
        # Cache tool definitions: copy and add cache_control to last tool
        tool_defs = [dict(d) for d in tool_defs]
        tool_defs[-1]["cache_control"] = {"type": "ephemeral"}
    else:
        system = system_prompt

    messages = [{"role": "user", "content": task}]
    steps = []
    total_input = 0
    total_output = 0
    total_cache_creation = 0
    total_cache_read = 0
    turns = 0
    response_text = ""
    budget_exceeded = False

    for _ in range(max_turns):
        kwargs = {
            "model": model,
            "max_tokens": 4096,
            "system": system,
            "tools": tool_defs,
            "messages": messages,
        }

        if thinking:
            budget = thinking if isinstance(thinking, int) and thinking is not True else 5000
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
            kwargs["max_tokens"] = max(budget + 4096, 16000)

        response = client.messages.create(**kwargs)

        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens
        total_cache_creation += getattr(response.usage, 'cache_creation_input_tokens', 0) or 0
        total_cache_read += getattr(response.usage, 'cache_read_input_tokens', 0) or 0
        turns += 1

        # Circuit breaker: stop if cumulative tokens exceed budget
        if max_tokens_budget is not None and (total_input + total_output) > max_tokens_budget:
            budget_exceeded = True
            break

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

        if cache and tool_results:
            tool_results[-1]["cache_control"] = {"type": "ephemeral"}

        messages.append({"role": "user", "content": tool_results})

    input_price, output_price = PRICING[model]
    cost = (
        total_input * input_price
        + total_cache_creation * input_price * 1.25
        + total_cache_read * input_price * 0.10
        + total_output * output_price
    ) / 1_000_000

    result = {
        "response": response_text,
        "steps": steps,
        "turns": turns,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "cost_usd": cost,
        "model": model,
        "plan": plan,
    }

    if total_cache_creation or total_cache_read:
        result["total_cache_creation_tokens"] = total_cache_creation
        result["total_cache_read_tokens"] = total_cache_read

    if max_tokens_budget is not None:
        result["budget_exceeded"] = budget_exceeded

    return result


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

    if result.get("budget_exceeded"):
        lines.append("[BUDGET EXCEEDED — circuit breaker tripped]")
        lines.append("")

    if result["response"]:
        lines.append(f"[RESPONSE] {result['response']}")
    lines.append("")
    lines.append(f"--- {result['model']} ({result['turns']} turns) ---")
    lines.append(f"Input:  {result['total_input_tokens']} tokens")
    lines.append(f"Output: {result['total_output_tokens']} tokens")
    if result.get("total_cache_creation_tokens") or result.get("total_cache_read_tokens"):
        lines.append(f"Cache write: {result.get('total_cache_creation_tokens', 0)} tokens")
        lines.append(f"Cache read:  {result.get('total_cache_read_tokens', 0)} tokens")
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

    cache = False
    if "--cache" in args:
        args.remove("--cache")
        cache = True

    enable_thinking = False
    if "--thinking" in args:
        idx = args.index("--thinking")
        if idx + 1 < len(args) and args[idx + 1].isdigit():
            enable_thinking = int(args[idx + 1])
            del args[idx:idx + 2]
        else:
            enable_thinking = True
            del args[idx]

    max_tokens_budget = None
    if "--budget" in args:
        idx = args.index("--budget")
        max_tokens_budget = int(args[idx + 1])
        del args[idx:idx + 2]

    if not tools_path:
        print("Error: --tools is required", file=sys.stderr)
        sys.exit(1)

    tools_module = load_tools_module(tools_path)
    result = run_agent(system_prompt, task, tools_module, model=model,
                       plan=plan, cache=cache, thinking=enable_thinking,
                       max_tokens_budget=max_tokens_budget)
    print(format_agent_result(result))
