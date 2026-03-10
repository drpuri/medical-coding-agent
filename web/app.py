"""
Medical Coding Portal — Web Server
Run with: python app.py
Then open http://localhost:5000
"""

import os
import json
import re
import time
import logging
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import anthropic

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from system_prompt import SYSTEM_PROMPT_PROVIDER, SYSTEM_PROMPT_ENRICH, SYSTEM_PROMPT_COPYPASTE
import subprocess

from cms_data.hcc_lookup import lookup_icd10


def cached_system(prompt_text):
    """Wrap a system prompt string for Anthropic prompt caching."""
    return [{"type": "text", "text": prompt_text, "cache_control": {"type": "ephemeral"}}]


MODEL_MAP = {
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-6",
}

CACHED_PROVIDER = cached_system(SYSTEM_PROMPT_PROVIDER)
CACHED_ENRICH = cached_system(SYSTEM_PROMPT_ENRICH)
CACHED_COPYPASTE = cached_system(SYSTEM_PROMPT_COPYPASTE)

def get_version():
    """Get git short hash for version display. Falls back to 'dev'."""
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        # Vercel sets VERCEL_GIT_COMMIT_SHA
        sha = os.environ.get('VERCEL_GIT_COMMIT_SHA', '')
        return sha[:7] if sha else 'dev'

APP_VERSION = get_version()

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
)
app.config['MAX_CONTENT_LENGTH'] = 512 * 1024  # 512 KB

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
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
                "JSON parse failed after brace extraction. Error: %s | response_length=%d",
                str(e), len(raw_text)
            )
            return None

    # 4. Nothing worked
    logger.error(
        "No JSON object found in LLM response. response_length=%d",
        len(raw_text)
    )
    return None


def _enrich_hcc_from_accumulated(accumulated_text):
    """Parse accumulated LLM sections and enrich ICD-10 codes with deterministic HCC/RAF.

    Returns dict with:
        code_map: {icd10_code: {"category": "HCC X", "raf": "0.XXX"} or null}
        scorecard: [{condition, hcc_category, raf, status, rec_num}, ...]
        codes_mapped: int count of codes with HCC mappings
    """
    sections = accumulated_text.split("---SECTION---")
    # Section order: summary, billing_alerts, em_code, tier1, tier2, tier3, additional_codes
    tier1, tier2, tier3 = [], [], []
    for i, raw in enumerate(sections):
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if i == 3:
            tier1 = parsed if isinstance(parsed, list) else []
        elif i == 4:
            tier2 = parsed if isinstance(parsed, list) else []
        elif i == 5:
            tier3 = parsed if isinstance(parsed, list) else []

    code_map = {}   # code -> hcc info or None
    scorecard = []  # HCC scorecard entries

    # Process tier1 codes
    for item in tier1:
        code = item.get("code", "")
        if not code:
            continue
        results = lookup_icd10(code)
        if results:
            # Use first (primary) HCC mapping
            r = results[0]
            hcc_info = {"category": f"HCC {r['hcc']}", "raf": str(r["raf_weight"])}
            code_map[code] = hcc_info
            status = "action_needed" if item.get("status") == "action_needed" else "captured"
            scorecard.append({
                "condition": item.get("description", ""),
                "hcc_category": hcc_info["category"],
                "raf": hcc_info["raf"],
                "status": status,
                "rec_num": item.get("rec_num"),
            })
        else:
            code_map[code] = None

    # Process tier2 option codes
    for item in tier2:
        for opt in item.get("options", []):
            code = opt.get("code", "")
            if not code or code in code_map:
                continue
            results = lookup_icd10(code)
            if results:
                r = results[0]
                hcc_info = {"category": f"HCC {r['hcc']}", "raf": str(r["raf_weight"])}
                code_map[code] = hcc_info
                scorecard.append({
                    "condition": opt.get("label", ""),
                    "hcc_category": hcc_info["category"],
                    "raf": hcc_info["raf"],
                    "status": "opportunity",
                    "rec_num": item.get("rec_num"),
                })
            else:
                code_map[code] = None

    # Process tier3 codes
    for item in tier3:
        code = item.get("code", "")
        if not code or code in code_map:
            continue
        results = lookup_icd10(code)
        if results:
            r = results[0]
            hcc_info = {"category": f"HCC {r['hcc']}", "raf": str(r["raf_weight"])}
            code_map[code] = hcc_info
            scorecard.append({
                "condition": item.get("condition", ""),
                "hcc_category": hcc_info["category"],
                "raf": hcc_info["raf"],
                "status": "opportunity",
                "rec_num": item.get("rec_num"),
            })
        else:
            code_map[code] = None

    # Sort scorecard by RAF descending
    scorecard.sort(key=lambda x: float(x.get("raf", 0)), reverse=True)

    return {
        "code_map": code_map,
        "scorecard": scorecard,
        "codes_mapped": sum(1 for v in code_map.values() if v is not None),
    }


def get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    return anthropic.Anthropic(api_key=api_key)


@app.before_request
def csrf_protect():
    if request.method == "POST":
        content_type = request.content_type or ""
        if "application/json" not in content_type:
            return jsonify({"error": "Invalid content type."}), 415


@app.route("/")
def index():
    return render_template("index.html", version=APP_VERSION)


@app.route("/analyze", methods=["POST"])
@limiter.limit("10/minute")
def analyze():
    """Call 1: Streaming provider-view analysis via SSE."""
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

    if len(note_content) > 100_000:
        return jsonify({"error": "Note exceeds maximum length (100,000 characters)."}), 400

    model_key = data.get("model", "opus")
    model_id = MODEL_MAP.get(model_key, MODEL_MAP["opus"])

    # Try to parse as JSON if it looks like structured data
    try:
        if note_content.strip().startswith("{") or note_content.strip().startswith("["):
            parsed = json.loads(note_content)
            note_content = json.dumps(parsed, indent=2)
    except json.JSONDecodeError:
        pass  # Treat as plain text

    def generate():
        try:
            client = get_client()
            t0 = time.time()
            logger.info("Starting PROVIDER stream (model=%s, max_tokens=4096)", model_id)
            accumulated = ""

            with client.messages.stream(
                model=model_id,
                max_tokens=4096,
                temperature=0,
                system=CACHED_PROVIDER,
                messages=[
                    {
                        "role": "user",
                        "content": f"Analyze this de-identified clinical note. Return ONLY valid JSON following the schema in your instructions.\n\n<clinical_note>\n{note_content}\n</clinical_note>"
                    }
                ]
            ) as stream:
                for text in stream.text_stream:
                    accumulated += text
                    yield f"data: {json.dumps({'type': 'chunk', 'text': text})}\n\n"

                response = stream.get_final_message()

            elapsed = time.time() - t0
            logger.info("Raw usage object: %s", response.usage)
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_read": getattr(response.usage, 'cache_read_input_tokens', 0),
                "cache_creation": getattr(response.usage, 'cache_creation_input_tokens', 0),
            }
            logger.info(
                "PROVIDER stream complete: %.1fs | input=%d output=%d | cache_read=%d cache_create=%d | stop=%s",
                elapsed, usage["input_tokens"], usage["output_tokens"],
                usage["cache_read"], usage["cache_creation"],
                response.stop_reason
            )

            # Enrich ICD-10 codes with deterministic HCC/RAF data
            hcc_data = _enrich_hcc_from_accumulated(accumulated)
            logger.info("HCC enrichment: %d codes mapped, %d scorecard entries",
                        hcc_data.get("codes_mapped", 0), len(hcc_data.get("scorecard", [])))

            yield f"data: {json.dumps({'type': 'done', 'usage': usage, 'hcc': hcc_data})}\n\n"

        except Exception as e:
            logger.error("PROVIDER stream error: %s", str(e))
            yield f"data: {json.dumps({'type': 'error', 'error': 'Analysis failed. Please try again.'})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )


@app.route("/enrich", methods=["POST"])
@limiter.limit("15/minute")
def enrich():
    """Call 2: Coder-level detail enrichment + frailty analysis."""
    data = request.get_json()
    note = data.get("note", "").strip()
    prior_analysis = data.get("prior_analysis")

    if not note or not prior_analysis:
        return jsonify({"error": "Note and prior analysis required."}), 400

    prior_json = json.dumps(prior_analysis) if isinstance(prior_analysis, dict) else str(prior_analysis)

    try:
        client = get_client()
        t0 = time.time()
        logger.info("Starting ENRICH call (max_tokens=4096)")
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=CACHED_ENRICH,
            messages=[
                {
                    "role": "user",
                    "content": f"Clinical note:\n\n<clinical_note>\n{note}\n</clinical_note>"
                },
                {
                    "role": "assistant",
                    "content": prior_json
                },
                {
                    "role": "user",
                    "content": "Now provide detailed enrichment: coder-level rationale for each recommendation and a full frailty/advanced illness exclusion analysis. Return ONLY valid JSON following the enrichment schema."
                }
            ]
        )
        elapsed = time.time() - t0

        raw_text = response.content[0].text
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cache_read": getattr(response.usage, 'cache_read_input_tokens', 0),
            "cache_creation": getattr(response.usage, 'cache_creation_input_tokens', 0),
        }
        logger.info(
            "ENRICH call complete: %.1fs | input=%d output=%d | cache_read=%d cache_create=%d | stop=%s",
            elapsed, usage["input_tokens"], usage["output_tokens"],
            usage["cache_read"], usage["cache_creation"],
            response.stop_reason
        )

        structured_data = extract_json(raw_text)
        if structured_data is not None:
            return jsonify({
                "structured": True,
                "data": structured_data,
                "usage": usage
            })
        else:
            return jsonify({
                "structured": False,
                "raw": raw_text,
                "usage": usage
            })

    except ValueError as e:
        logger.error("ENRICH ValueError: %s", str(e))
        return jsonify({"error": "Enrichment failed. Please try again."}), 500
    except anthropic.APIError as e:
        logger.error("ENRICH APIError: %s", str(e))
        return jsonify({"error": "Enrichment failed. Please try again."}), 500
    except Exception as e:
        logger.error("ENRICH unexpected error: %s", str(e))
        return jsonify({"error": "Enrichment failed. Please try again."}), 500


@app.route("/copypaste", methods=["POST"])
@limiter.limit("15/minute")
def copypaste():
    """On-demand copy-paste documentation language for recommendations."""
    data = request.get_json()
    note = data.get("note", "").strip()
    prior_analysis = data.get("prior_analysis")

    if not note or not prior_analysis:
        return jsonify({"error": "Note and prior analysis required."}), 400

    prior_json = json.dumps(prior_analysis) if isinstance(prior_analysis, dict) else str(prior_analysis)

    try:
        client = get_client()
        t0 = time.time()
        logger.info("Starting COPYPASTE call (max_tokens=4096)")
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=CACHED_COPYPASTE,
            messages=[
                {
                    "role": "user",
                    "content": f"Clinical note:\n\n<clinical_note>\n{note}\n</clinical_note>\n\nCoding analysis:\n\n{prior_json}\n\nGenerate copy-paste documentation for each recommendation that needs it."
                }
            ]
        )
        elapsed = time.time() - t0

        raw_text = response.content[0].text
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cache_read": getattr(response.usage, 'cache_read_input_tokens', 0),
            "cache_creation": getattr(response.usage, 'cache_creation_input_tokens', 0),
        }
        logger.info(
            "COPYPASTE call complete: %.1fs | input=%d output=%d | cache_read=%d cache_create=%d | stop=%s",
            elapsed, usage["input_tokens"], usage["output_tokens"],
            usage["cache_read"], usage["cache_creation"],
            response.stop_reason
        )

        if response.stop_reason == "max_tokens":
            logger.warning("COPYPASTE response truncated — max_tokens reached. JSON likely incomplete.")

        structured_data = extract_json(raw_text)
        if structured_data is not None:
            return jsonify({"data": structured_data, "usage": usage})
        else:
            return jsonify({"error": "Failed to parse copy-paste response"}), 500

    except ValueError as e:
        logger.error("COPYPASTE ValueError: %s", str(e))
        return jsonify({"error": "Copy-paste generation failed. Please try again."}), 500
    except anthropic.APIError as e:
        logger.error("COPYPASTE APIError: %s", str(e))
        return jsonify({"error": "Copy-paste generation failed. Please try again."}), 500
    except Exception as e:
        logger.error("COPYPASTE unexpected error: %s", str(e))
        return jsonify({"error": "Copy-paste generation failed. Please try again."}), 500


@app.route("/followup", methods=["POST"])
@limiter.limit("15/minute")
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
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            system=CACHED_PROVIDER,
            messages=[
                {
                    "role": "user",
                    "content": f"Please analyze this de-identified clinical note:\n\n<clinical_note>\n{note}\n</clinical_note>"
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
        logger.error("FOLLOWUP error: %s", str(e))
        return jsonify({"error": "Follow-up failed. Please try again."}), 500


@app.after_request
def set_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://va.vercel-scripts.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self' https://va.vercel-scripts.com"
    )
    return response


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n\u26a0\ufe0f  ANTHROPIC_API_KEY not set.")
        print("Run: export ANTHROPIC_API_KEY=your_key_here\n")
    app.run()
