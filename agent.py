"""
Medical Coding Agent — SNF/ALF Primary Care
Built for Claude Code using the Anthropic SDK
"""

from __future__ import annotations

import anthropic
import json
from system_prompt import SYSTEM_PROMPT


def run_coding_agent(note_input: str | dict) -> str:
    """
    Analyze a clinical note and return tiered coding recommendations.
    
    Args:
        note_input: Either raw note text (str) or structured JSON (dict)
    
    Returns:
        Formatted coding analysis as string
    """
    client = anthropic.Anthropic()

    # Normalize input
    if isinstance(note_input, dict):
        note_text = json.dumps(note_input, indent=2)
        user_message = f"""Please analyze this clinical note and provide coding recommendations 
following your tiered framework:\n\n{note_text}"""
    else:
        user_message = f"""Please analyze this clinical note and provide coding recommendations 
following your tiered framework:\n\n{note_input}"""

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=5120,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )

    return response.content[0].text


def run_followup_question(note_input: str | dict, question: str, prior_analysis: str) -> str:
    """
    Ask a follow-up question about a note after initial analysis.
    Maintains conversation context so provider can drill into specific codes.
    
    Args:
        note_input: Original note (text or dict)
        question: Provider's follow-up question
        prior_analysis: The agent's previous response
    
    Returns:
        Follow-up response as string
    """
    client = anthropic.Anthropic()

    if isinstance(note_input, dict):
        note_text = json.dumps(note_input, indent=2)
    else:
        note_text = note_input

    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Please analyze this clinical note:\n\n{note_text}"
            },
            {
                "role": "assistant",
                "content": prior_analysis
            },
            {
                "role": "user",
                "content": question
            }
        ]
    )

    return response.content[0].text


def interactive_session():
    """
    Run an interactive coding session in the terminal.
    Provider can paste a note, get analysis, then ask follow-up questions.
    """
    print("\n" + "="*60)
    print("  MEDICAL CODING AGENT — SNF/ALF Primary Care")
    print("="*60)
    print("\nPaste your clinical note below.")
    print("When done, type '---END---' on a new line and press Enter.\n")

    # Collect multiline note input
    lines = []
    while True:
        line = input()
        if line.strip() == "---END---":
            break
        lines.append(line)

    note = "\n".join(lines)

    if not note.strip():
        print("No note provided. Exiting.")
        return

    print("\n⏳ Analyzing note...\n")
    analysis = run_coding_agent(note)
    print(analysis)

    # Follow-up question loop
    print("\n" + "-"*60)
    print("Ask follow-up questions about this note, or type 'exit' to quit.")
    print("-"*60 + "\n")

    while True:
        question = input("Your question: ").strip()
        if question.lower() in ("exit", "quit", "q"):
            print("\nSession ended.")
            break
        if not question:
            continue

        print("\n⏳ Thinking...\n")
        followup = run_followup_question(note, question, analysis)
        print(followup)
        print("\n" + "-"*60 + "\n")

        # Update analysis context for chained follow-ups
        analysis = followup


if __name__ == "__main__":
    interactive_session()
