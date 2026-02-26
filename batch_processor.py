"""
Batch Note Processor
Run coding analysis on multiple notes from a JSON file.
Useful for end-of-day coding review or audit workflows.

Usage:
    python batch_processor.py notes.json
    python batch_processor.py notes.json --output results.json
"""

import anthropic
import json
import argparse
import time
from pathlib import Path
from system_prompt import SYSTEM_PROMPT


def analyze_note(client: anthropic.Anthropic, note: dict | str, note_id: str = "") -> dict:
    """Analyze a single note and return structured result."""
    
    if isinstance(note, dict):
        note_text = json.dumps(note, indent=2)
    else:
        note_text = note

    try:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Please analyze this clinical note and provide coding recommendations:\n\n{note_text}"
                }
            ]
        )
        
        return {
            "note_id": note_id,
            "status": "success",
            "analysis": response.content[0].text,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        }

    except Exception as e:
        return {
            "note_id": note_id,
            "status": "error",
            "error": str(e),
            "analysis": None
        }


def process_batch(input_file: str, output_file: str = None):
    """
    Process a batch of notes from a JSON file.
    
    Input JSON format:
    [
        {"id": "note_001", "content": "...note text or structured JSON..."},
        {"id": "note_002", "content": {...}},
    ]
    """
    client = anthropic.Anthropic()
    
    with open(input_file) as f:
        notes = json.load(f)

    print(f"\nProcessing {len(notes)} notes...\n")
    
    results = []
    for i, note_entry in enumerate(notes, 1):
        note_id = note_entry.get("id", f"note_{i:03d}")
        content = note_entry.get("content", note_entry)
        
        print(f"[{i}/{len(notes)}] Analyzing {note_id}...")
        result = analyze_note(client, content, note_id)
        results.append(result)
        
        if result["status"] == "success":
            print(f"  ✓ Complete ({result['output_tokens']} tokens)")
        else:
            print(f"  ✗ Error: {result['error']}")
        
        # Rate limit courtesy pause between notes
        if i < len(notes):
            time.sleep(1)

    # Output results
    if output_file:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n✓ Results saved to {output_file}")
    else:
        # Print to stdout
        for result in results:
            print("\n" + "="*60)
            print(f"NOTE: {result['note_id']}")
            print("="*60)
            if result["status"] == "success":
                print(result["analysis"])
            else:
                print(f"ERROR: {result['error']}")

    # Summary
    successful = sum(1 for r in results if r["status"] == "success")
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE: {successful}/{len(notes)} notes processed successfully")
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch medical coding analysis")
    parser.add_argument("input", help="Input JSON file with notes")
    parser.add_argument("--output", help="Output JSON file for results", default=None)
    args = parser.parse_args()
    
    process_batch(args.input, args.output)
