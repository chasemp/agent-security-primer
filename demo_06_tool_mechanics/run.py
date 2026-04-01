"""Demo 6: Tool Mechanics — The Ender's Game.

THIS IS THE MOST EDUCATIONAL DEMO IN THE TALK.

It shows the exact mechanism by which models "call tools" — and reveals that
tool calls are just JSON output. The model writes JSON. Your code decides
what's real.

HOW TOOL CALLS ACTUALLY WORK:
  1. You define a tool schema (name, description, parameters)
  2. You send a prompt that might need the tool
  3. The model responds with a tool_use content block — just JSON
  4. The response has stop_reason: "tool_use" — your code's cue to act
  5. [YOUR CODE RUNS HERE] — you decide whether to execute
  6. You feed the result back as a tool_result content block
  7. The model uses the result to produce its final answer

  Step 5 is the Bouncer. Every security control in Sections 5-9 lives there.

SDK USAGE:
  Uses query() with a tool defined via @tool decorator. The SDK handles the
  agentic loop. We display each step with pauses for narration.
"""

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
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
    Presenter,
    code_block,
    thinking_block,
    tool_use_block,
)
from shared.models import DEFAULT_DEMO_MODEL
from shared.runner import Demo
from shared.token_counter import TokenCounter

# The hardcoded tool result. The point is the MECHANISM, not the data.
TOOL_RESULT = "Alice is a Senior Engineer in Platform"

PROMPT = "Look up the user 'alice' and tell me their role."

TOOL_SCHEMA_DISPLAY = """\
@tool("lookup_user",
      "Look up a user in the company directory",
      {"username": str})
async def lookup_user(username: str) -> str:
    # [YOUR CODE RUNS HERE]
    return user_database[username]"""


class ToolMechanics(Demo):
    """Demo 6: Tool Mechanics — The Ender's Game."""

    number = "6"
    name = "tool_mechanics"
    section = "Section 3"
    description = "How tool calls really work: the model writes JSON, your code decides what's real."

    async def run(self, console: Console, **kwargs) -> None:
        model = kwargs.get("model") or DEFAULT_DEMO_MODEL
        no_pause = kwargs.get("no_pause", False)
        p = Presenter(console, interactive=not no_pause)
        counter = TokenCounter(model=model)

        # --- Header ---
        p.show(DemoPanel(
            title="Tool Mechanics — The Ender's Game",
            section="Section 3 — What Is an Agent",
            description=(
                "The model doesn't execute tools. It writes JSON. "
                "Your code decides whether to comply."
            ),
        ))

        # --- Step 1: Show the tool ---
        p.step("Define a tool: lookup_user(username) -> str", number=1)
        p.show(code_block(TOOL_SCHEMA_DISPLAY, language="python"))

        # --- Step 2: Send the prompt ---
        p.step(f'Prompt: "{PROMPT}"', number=2)

        # --- Step 3: Call the SDK ---
        p.step("Calling the model with the tool available...", number=3)

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

        # Collect all messages
        messages: list = []
        async for message in query(prompt=PROMPT, options=options):
            messages.append(message)
            if isinstance(message, AssistantMessage) and message.usage:
                counter.update(message.usage)

        # --- Walk through each message step by step ---
        # This is the educational core. Each content block gets its own
        # step so the presenter can explain what's happening.
        step_num = 4
        for message in messages:
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, ThinkingBlock):
                        p.step("Model is thinking...", number=step_num)
                        p.show(thinking_block(block.thinking))
                        step_num += 1

                    elif isinstance(block, ToolUseBlock):
                        # THE KEY MOMENT: the model wrote JSON requesting a tool call.
                        p.step("Model produced a tool_use block:", number=step_num)
                        p.show(tool_use_block({
                            "type": "tool_use",
                            "name": block.name,
                            "input": block.input,
                            "id": block.id,
                        }))
                        step_num += 1

                        p.step(
                            f'stop_reason: "{message.stop_reason}" '
                            "— this is how your code knows the model wants to act",
                            number=step_num,
                        )
                        step_num += 1

                        # THE ENDER'S GAME MOMENT
                        p.show(Panel(
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
                        step_num += 1

                    elif isinstance(block, ToolResultBlock):
                        p.step("Tool result fed back to model:", number=step_num)
                        result_text = block.content if isinstance(block.content, str) else str(block.content)
                        p.show(Panel(
                            Text(result_text),
                            title="tool_result",
                            border_style="green",
                        ))
                        step_num += 1

                    elif isinstance(block, TextBlock):
                        p.step("Model's final response:", number=step_num)
                        p.show(Panel(Text(block.text), border_style="bright_blue"))
                        step_num += 1

        p.show(counter)

        # --- Punchline ---
        p.punchline("The model writes JSON. Your code decides what's real.")
