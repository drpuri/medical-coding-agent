import anthropic
import json
from typing import Any
from system_prompt import SYSTEM_PROMPT

client = anthropic.Anthropic()

# ── Tool definitions ──────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "lookup_icd10_code",
        "description": (
            "Look up an ICD-10-CM diagnosis code to verify it exists, get its full description, "
            "and confirm it is valid for HIPAA billing. Use this to validate any code before recommending it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "ICD-10-CM code to look up (e.g. 'E11.65', 'N18.4')"
                }
            },
            "required": ["code"]
        }
    },
    {
        "name": "search_icd10_by_description",
        "description": (
            "Search for ICD-10-CM codes by clinical description. Use when you know the condition "
            "but need to find the correct code or verify specificity options."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Clinical term or description (e.g. 'chronic systolic heart failure', 'vascular dementia')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results to return (default 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_icd10_hierarchy",
        "description": (
            "Get all subcodes under a given ICD-10 prefix. Use this to show a provider all "
            "specificity options for a condition (e.g. all F02.x codes for Alzheimer's dementia)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code_prefix": {
                    "type": "string",
                    "description": "Code prefix to expand (e.g. 'I50', 'F02', 'N18')"
                }
            },
            "required": ["code_prefix"]
        }
    },
    {
        "name": "check_cms_coverage",
        "description": (
            "Look up a National Coverage Determination (NCD) for a service or condition. "
            "Use when coverage of a procedure or service is in question."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Condition or service to search (e.g. 'continuous oxygen therapy', 'glucose monitors')"
                }
            },
            "required": ["keyword"]
        }
    }
]


# ── Tool execution ─────────────────────────────────────────────────────────────

def execute_tool(tool_name: str, tool_input: dict) -> Any:
    """Route tool calls to the appropriate external API."""

    # Lazy imports to keep startup fast
    import importlib

    if tool_name == "lookup_icd10_code":
        from icd10_client import lookup_code
        return lookup_code(tool_input["code"])

    elif tool_name == "search_icd10_by_description":
        from icd10_client import search_codes
        limit = tool_input.get("limit", 5)
        return search_codes(tool_input["query"], limit)

    elif tool_name == "get_icd10_hierarchy":
        from icd10_client import get_hierarchy
        return get_hierarchy(tool_input["code_prefix"])

    elif tool_name == "check_cms_coverage":
        from cms_client import search_ncd
        return search_ncd(tool_input["keyword"])

    else:
        return {"error": f"Unknown tool: {tool_name}"}


# ── Agent loop ─────────────────────────────────────────────────────────────────

def run_coding_agent(note_input: str, verbose: bool = False) -> str:
    """
    Run the medical coding agent on a note.
    
    Args:
        note_input: Clinical note text or JSON string
        verbose: Print tool calls as they happen
    
    Returns:
        Formatted coding analysis string
    """
    messages = [
        {
            "role": "user",
            "content": (
                "Please analyze the following clinical note and provide a full coding analysis "
                "using the three-tier framework.\n\n"
                f"<note>\n{note_input}\n</note>"
            )
        }
    ]

    # Agentic loop — runs until model stops calling tools
    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        # Check stop reason
        if response.stop_reason == "end_turn":
            # Extract final text response
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            return final_text

        elif response.stop_reason == "tool_use":
            # Process all tool calls in this response
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    if verbose:
                        print(f"\n[Tool call] {block.name}({json.dumps(block.input, indent=2)})")

                    result = execute_tool(block.name, block.input)

                    if verbose:
                        print(f"[Tool result] {json.dumps(result, indent=2)[:300]}...")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })

            # Append assistant response and tool results to message history
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        else:
            # Unexpected stop reason
            return f"Agent stopped unexpectedly: {response.stop_reason}"


# ── Interactive CLI ────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Medical Coding Agent — SNF/ALF Primary Care")
    print("=" * 60)
    print("\nPaste a clinical note (or JSON), then press Enter twice.\n")

    while True:
        lines = []
        try:
            while True:
                line = input()
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
        except EOFError:
            break

        note = "\n".join(lines).strip()
        if not note:
            continue

        print("\n" + "─" * 60)
        print("Analyzing note...")
        print("─" * 60 + "\n")

        result = run_coding_agent(note, verbose=True)
        print(result)
        print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    main()
