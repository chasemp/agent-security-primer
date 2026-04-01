"""Demo 6: Tool Mechanics — The Ender's Game.

THIS IS THE MOST EDUCATIONAL DEMO IN THE TALK.

It shows the exact mechanism by which models "call tools" — and reveals that
tool calls are just JSON output. The model writes JSON. Your code decides
what's real.

THE ENDER'S GAME ANALOGY:
  In the novel, Ender thinks he's playing a simulation, but it's real.
  With LLMs, it's the OPPOSITE: the model thinks it's doing something real
  (looking up a user), but it's just writing JSON. YOUR CODE runs in the
  gap between the model's request and the actual execution. That gap is
  where every security control in this talk lives.

HOW TOOL CALLS ACTUALLY WORK:
  1. You define a tool schema (name, description, parameters)
  2. You send a prompt that might need the tool
  3. The model responds with a tool_use content block:
       {"type": "tool_use", "name": "lookup_user", "input": {"username": "alice"}, "id": "toolu_abc123"}
  4. The response has stop_reason: "tool_use" — this is how your code knows
     the model wants to act
  5. [YOUR CODE RUNS HERE] — you decide whether to execute, and with what
  6. You feed the result back as a tool_result content block
  7. The model uses the result to produce its final answer

  Step 5 is the Bouncer. Every security control in Sections 5-9 of the talk
  lives in that box. The audience needs to see the box before they see what
  goes in it.

SDK USAGE:
  Uses query() with a tool defined via @tool decorator. The SDK handles the
  agentic loop (tool execution and result injection). We display each step
  with pauses so the presenter can narrate the mechanism.
"""

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    McpSdkServerConfig,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from shared.display import (
    DemoPanel,
    code_block,
    punchline,
    step,
    thinking_block,
    tool_use_block,
)
from shared.models import DEFAULT_DEMO_MODEL
from shared.runner import Demo
from shared.token_counter import TokenCounter

# The hardcoded tool result. The point of this demo is the MECHANISM
# (how tool calls work), not the DATA (what Alice's role is).
# Using a hardcoded result keeps the demo fast and predictable.
TOOL_RESULT = "Alice is a Senior Engineer in Platform"

# The prompt that triggers a tool call. Simple and direct —
# the model should immediately want to call lookup_user.
PROMPT = "Look up the user 'alice' and tell me their role."

# The tool schema, shown to the audience as code. This is what the model
# sees — it defines what tools are available and what parameters they accept.
TOOL_SCHEMA_DISPLAY = """\
@tool("lookup_user",
      "Look up a user in the company directory",
      {"username": str})
async def lookup_user(username: str) -> str:
    # [YOUR CODE RUNS HERE]
    return user_database[username]"""


class ToolMechanics(Demo):
    """Demo 6: Tool Mechanics — The Ender's Game.

    Shows the exact mechanism of tool calls: the model writes JSON,
    stop_reason tells your code to act, and your code decides what's real.
    """

    number = "6"
    name = "tool_mechanics"
    section = "Section 3"
    description = "How tool calls really work: the model writes JSON, your code decides what's real."

    async def run(self, console: Console, **kwargs) -> None:
        model = kwargs.get("model") or DEFAULT_DEMO_MODEL
        counter = TokenCounter(model=model)

        # --- Header ---
        console.print(DemoPanel(
            title="Tool Mechanics — The Ender's Game",
            section="Section 3 — What Is an Agent",
            description=(
                "The model doesn't execute tools. It writes JSON requesting a tool call. "
                "Your code decides whether to comply. "
                "This is where every security control lives."
            ),
        ))

        # --- Step 1: Show the tool definition ---
        # The audience sees what the model knows about the tool.
        # This is the contract: name, description, parameters.
        console.print(step("Define a tool: lookup_user(username) → str", number=1))
        console.print(code_block(TOOL_SCHEMA_DISPLAY, language="python"))
        console.print()

        # --- Step 2: Send the prompt ---
        console.print(step(f'Prompt: "{PROMPT}"', number=2))
        console.print()

        # --- Step 3: Call the SDK with the tool ---
        # We define the tool using the @tool decorator and create an MCP server.
        # The SDK handles the agentic loop: if the model requests a tool call,
        # the SDK executes our tool function and feeds the result back.
        console.print(step("Calling the model with the tool available...", number=3))
        console.print()

        @tool("lookup_user", "Look up a user in the company directory", {"username": str})
        async def lookup_user(username: str) -> str:
            return TOOL_RESULT

        server = create_sdk_mcp_server(
            "directory", version="1.0.0", tools=[lookup_user]
        )

        options = ClaudeAgentOptions(
            model=model,
            max_turns=3,
            mcp_servers={"directory": server},
        )

        # Collect all messages to display step-by-step
        messages: list = []
        async for message in query(prompt=PROMPT, options=options):
            messages.append(message)

            # Update token counter from assistant messages
            if isinstance(message, AssistantMessage) and message.usage:
                counter.update(message.usage)

        # --- Step 4: Walk through each message for the audience ---
        # This is the educational core. We show each step with commentary
        # so the audience understands the mechanism, not just the result.
        step_num = 4
        for message in messages:
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ThinkingBlock):
                        # If thinking is enabled, show the model's reasoning
                        console.print(step("Model is thinking...", number=step_num))
                        console.print(thinking_block(block.thinking))
                        console.print()
                        step_num += 1

                    elif isinstance(block, ToolUseBlock):
                        # THE KEY MOMENT: the model produced a tool_use block.
                        # It's just JSON — the model didn't execute anything.
                        console.print(step("Model produced a tool_use block:", number=step_num))
                        console.print(tool_use_block({
                            "type": "tool_use",
                            "name": block.name,
                            "input": block.input,
                            "id": block.id,
                        }))
                        console.print()
                        step_num += 1

                        # Show stop_reason — this is how your code knows to act
                        console.print(step(
                            f'stop_reason: "{message.stop_reason}" — '
                            "this is how your code knows the model wants to act",
                            number=step_num,
                        ))
                        console.print()
                        step_num += 1

                        # THE ENDER'S GAME MOMENT
                        # The model thinks it called a tool. But nothing happened yet.
                        # YOUR CODE runs in this gap. This is the Bouncer's jurisdiction.
                        console.print(Panel(
                            Text(
                                "[ YOUR CODE RUNS HERE ]\n\n"
                                "The model requested a tool call.\n"
                                "Nothing has happened yet.\n"
                                "Your code decides: execute, modify, or deny.",
                                justify="center",
                            ),
                            border_style="bold yellow",
                            title="The Bouncer's Jurisdiction",
                            padding=(1, 4),
                        ))
                        console.print()
                        step_num += 1

                    elif isinstance(block, ToolResultBlock):
                        # The tool result was fed back to the model.
                        # Show what data the model received.
                        console.print(step("Tool result fed back to model:", number=step_num))
                        result_text = block.content if isinstance(block.content, str) else str(block.content)
                        console.print(Panel(
                            Text(result_text),
                            title="tool_result",
                            border_style="green",
                        ))
                        console.print()
                        step_num += 1

                    elif isinstance(block, TextBlock):
                        # The model's final answer, using the tool result.
                        console.print(step("Model's final response:", number=step_num))
                        console.print(Panel(
                            Text(block.text),
                            border_style="bright_blue",
                        ))
                        console.print()
                        step_num += 1

        # --- Token counter ---
        console.print(counter)
        console.print()

        # --- Punchline ---
        console.print(punchline("The model writes JSON. Your code decides what's real."))
