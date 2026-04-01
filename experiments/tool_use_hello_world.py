# experiments/tool_use_hello_world.py
"""
Demonstrates the Anthropic API tool use lifecycle end-to-end.

Run with:
    python experiments/tool_use_hello_world.py
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import anthropic

from agents.tools.system_info import SYSTEM_INFO_TOOL, get_system_info

# Create the Anthropic client using your API key from the environment variable
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
MODEL = "claude-opus-4-5"


def run_tool_use_loop(user_message: str) -> str:
    """
    Executes one full tool use cycle:
    1. Send user message + tool definitions to Claude
    2. If Claude requests a tool call, execute it locally
    3. Send tool result back to Claude
    4. Return Claude's final text response
    """
    # Build the initial message history — just the user's question
    messages: list[dict[str, Any]] = [
        {"role": "user", "content": user_message}
    ]

    print(f"\n{'='*60}")
    print(f"USER: {user_message}")
    print(f"{'='*60}")

    # ── ROUND 1: Send the initial request ──────────────────────────────────
    # We pass `tools=[SYSTEM_INFO_TOOL]` so Claude knows this tool exists.
    # Claude won't necessarily use it — it decides based on the user message.
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[SYSTEM_INFO_TOOL],
        messages=messages,
    )

    print(f"\n[Round 1] stop_reason: {response.stop_reason}")
    print(f"[Round 1] content blocks: {[block.type for block in response.content]}")

    # ── CHECK: Did Claude want to use a tool? ───────────────────────────────
    if response.stop_reason != "tool_use":
        # Claude answered directly from its own knowledge — no tool needed.
        # This is the expected behavior for general questions.
        final_text = next(
            (block.text for block in response.content if hasattr(block, "text")), ""
        )
        print(f"\nCLAUDE (no tool used): {final_text}")
        return final_text

    # ── ROUND 2: Execute the tool and send the result back ─────────────────
    # Step A: Add Claude's response (which contains the tool_use block)
    #         to the conversation history. This is required — Claude needs
    #         to see its own tool request in the history.
    messages.append({"role": "assistant", "content": response.content})

    # Step B: Find every tool_use block in Claude's response and execute them
    tool_results: list[dict[str, Any]] = []

    for block in response.content:
        if block.type != "tool_use":
            continue

        print(f"\n[Tool Call] name={block.name} | input={json.dumps(block.input, indent=2)}")

        # Execute the function locally
        if block.name == "get_system_info":
            result = get_system_info(**block.input)
        else:
            result = {"error": f"Unknown tool: {block.name}"}

        print(f"[Tool Result] {json.dumps(result, indent=2)}")

        # Build the tool_result block — note that tool_use_id links this
        # result back to the specific tool call Claude made.
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,   # Must match the id from block above
            "content": json.dumps(result),
        })

    # Step C: Add the tool results as a "user" message.
    # (In the API's model, tool results are sent in the user turn.)
    messages.append({"role": "user", "content": tool_results})

    # Step D: Send the second request — Claude now has the tool result
    #         and will write its final answer.
    final_response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        tools=[SYSTEM_INFO_TOOL],
        messages=messages,
    )

    print(f"\n[Round 2] stop_reason: {final_response.stop_reason}")

    final_text = next(
        (block.text for block in final_response.content if hasattr(block, "text")), ""
    )
    print(f"\nCLAUDE (final): {final_text}")
    return final_text


if __name__ == "__main__":
    # Test 1: A question that should trigger the tool
    # Claude should recognize "prod-api-01" as a host and call get_system_info
    run_tool_use_loop("What is the current CPU and memory usage on prod-api-01?")

    # Test 2: A general question that should NOT trigger the tool
    # Claude should answer from its own knowledge without calling any tool
    run_tool_use_loop("What does CPU utilization measure?")