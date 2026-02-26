"""
Medical Coding Portal — Web Server
Run with: python app.py
Then open http://localhost:5000
"""

import os
import json
from flask import Flask, render_template, request, jsonify
import anthropic

from system_prompt import SYSTEM_PROMPT

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
)


def get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()

    # Validate de-identification acknowledgment
    if not data.get("deidentified_confirmed"):
        return jsonify({
            "error": "You must confirm the note has been de-identified before submission."
        }), 400

    note_content = data.get("note", "").strip()
    if not note_content:
        return jsonify({"error": "No note content provided."}), 400

    if len(note_content) < 50:
        return jsonify({"error": "Note appears too short to analyze."}), 400

    # Try to parse as JSON if it looks like structured data
    try:
        if note_content.strip().startswith("{") or note_content.strip().startswith("["):
            parsed = json.loads(note_content)
            note_content = json.dumps(parsed, indent=2)
    except json.JSONDecodeError:
        pass  # Treat as plain text

    try:
        client = get_client()
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=5120,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Please analyze this de-identified clinical note and provide coding recommendations following your tiered framework:\n\n{note_content}"
                }
            ]
        )

        return jsonify({
            "analysis": response.content[0].text,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        })

    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except anthropic.APIError as e:
        return jsonify({"error": f"API error: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/followup", methods=["POST"])
def followup():
    data = request.get_json()
    note = data.get("note", "").strip()
    question = data.get("question", "").strip()
    prior_analysis = data.get("prior_analysis", "").strip()

    if not question:
        return jsonify({"error": "No question provided."}), 400

    try:
        client = get_client()
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Please analyze this de-identified clinical note:\n\n{note}"
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

        return jsonify({
            "answer": response.content[0].text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n⚠️  ANTHROPIC_API_KEY not set.")
        print("Run: export ANTHROPIC_API_KEY=your_key_here\n")
    app.run()
