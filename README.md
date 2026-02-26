# Medical Coding Agent — SNF/ALF Primary Care

AI-powered coding consultant for primary care providers practicing in skilled nursing facilities (SNFs), assisted living facilities (ALFs), and long-term care settings. Analyzes de-identified clinical notes and returns tiered ICD-10/CPT coding recommendations with HCC capture guidance.

Built on Claude (Anthropic SDK). Designed for clinicians, not coders.

## What It Does

Paste a de-identified clinical note and get back:

1. **Billing Alerts** — Hospice modifier issues, POS errors, denial risks flagged first
2. **E/M Code** — Correct code family (SNF vs ALF) with MDM justification
3. **Tier 1 — Code These Now** — Conditions addressed in A&P with full ICD-10 specificity
4. **Tier 2 — Confirm Relevance** — Conditions in HPI/meds that need an A&P entry to be billable
5. **Tier 3 — Documentation Flags** — PMH conditions not connected to today's visit (do not code)
6. **Documentation Gap Prompts** — Exact language the provider can add to close gaps
7. **HCC Capture Scorecard** — Medicare/MA risk adjustment impact ranked by RAF weight

## Quick Start

```bash
# Install dependencies
pip install anthropic flask

# Set your API key
export ANTHROPIC_API_KEY=your_key_here
```

### Web Portal

```bash
python web/app.py
# Open http://localhost:5001
```

Two-panel interface: paste note on the left, get structured analysis on the right. Supports follow-up questions.

### CLI (Interactive)

```bash
python agent.py
```

Paste a note, type `---END---`, get analysis. Follow-up questions supported in the same session.

### Batch Processing

```bash
python batch_processor.py example_notes.json
python batch_processor.py notes.json --output results.json
```

Process multiple notes from a JSON file. Useful for end-of-day coding review.

### Programmatic

```python
from agent import run_coding_agent
analysis = run_coding_agent(note_text)
```

## Input Format

Accepts plain text notes or structured JSON:

```json
[
  {
    "id": "note_001",
    "content": {
      "document_type": "clinical_progress_note",
      "patient": { "age_range": "early_80s", "cognitive_status": "advanced dementia" },
      "diagnoses": [...],
      "assessment_and_plan": {...}
    }
  }
]
```

See `example_notes.json` for a complete example.

## Project Structure

```
agent.py              # Interactive CLI agent + programmatic API
batch_processor.py    # Multi-note batch processing
system_prompt.py      # Domain knowledge and output rules
example_notes.json    # Test notes for validation
web/
  app.py              # Flask server
  templates/
    index.html        # Web portal (single-page app)
```

## Key Design Decisions

- **Three-tier output** prevents overcoding while surfacing missed HCC captures
- **Billing alerts first** — modifier and denial risks before any coding discussion
- **Provider language** — explains _why_ a code matters clinically and financially
- **No pipe characters or markdown tables** — output formatted for clean web rendering
- **HCC-aware** — every condition flagged for Medicare risk adjustment impact

## Model

Uses `claude-opus-4-6` for maximum coding accuracy. The system prompt encodes SNF/ALF-specific E/M families, combination code rules (HTN+CHF+CKD), hospice billing modifiers, PDPM awareness, and commonly missed codes in this setting.

## Limitations

- Cannot verify codes against live CMS databases (yet)
- No access to full chart history beyond the note provided
- Not a substitute for certified coder review on complex claims
- All notes must be de-identified before submission

## License

Private use. Not intended for production clinical billing without human review.
