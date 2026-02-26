"""
Medical Coding Portal — Web Server
Run with: python app.py
Then open http://localhost:5000
"""

import os
import json
import re
import logging
from flask import Flask, render_template, request, jsonify
import anthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from system_prompt import SYSTEM_PROMPT

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
)


def extract_json(raw_text):
    """
    Extract a JSON object from LLM output, handling common wrapping patterns:
    - Clean JSON with no wrapping
    - ```json ... ``` code fences
    - ``` ... ``` code fences (no language tag)
    - Preamble text before the JSON
    - Trailing text after the JSON
    Returns parsed dict on success, None on failure.
    """
    text = raw_text.strip()

    # 1. Try direct parse first (cleanest case)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. Strip markdown code fences: ```json ... ``` or ``` ... ```
    fence_match = re.search(r'```(?:json)?\s*\n?(.*?)```', text, re.DOTALL)
    if fence_match:
        try:
            return json.loads(fence_match.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. Find the outermost { ... } and parse that
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        candidate = text[first_brace:last_brace + 1]
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "JSON parse failed after brace extraction. Error: %s\n"
                "--- RAW LLM RESPONSE (first 2000 chars) ---\n%s\n"
                "--- EXTRACTED CANDIDATE (first 2000 chars) ---\n%s\n"
                "-------------------------------------------",
                str(e),
                raw_text[:2000],
                candidate[:2000]
            )
            return None

    # 4. Nothing worked
    logger.error(
        "No JSON object found in LLM response.\n"
        "--- RAW LLM RESPONSE (first 2000 chars) ---\n%s\n"
        "-------------------------------------------",
        raw_text[:2000]
    )
    return None


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
            max_tokens=6144,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Analyze this de-identified clinical note. Return ONLY valid JSON following the schema in your instructions.\n\n{note_content}"
                }
            ]
        )

        raw_text = response.content[0].text
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens
        }

        # Extract and parse JSON from the response
        structured_data = extract_json(raw_text)
        if structured_data is not None:
            return jsonify({
                "structured": True,
                "data": structured_data,
                "usage": usage
            })
        else:
            # Fallback: return raw text for legacy rendering
            return jsonify({
                "structured": False,
                "analysis": raw_text,
                "usage": usage
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
        print("\n\u26a0\ufe0f  ANTHROPIC_API_KEY not set.")
        print("Run: export ANTHROPIC_API_KEY=your_key_here\n")
    app.run()
