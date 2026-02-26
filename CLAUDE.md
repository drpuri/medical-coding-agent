# Medical Coding Agent — SNF/ALF Primary Care

## Project Purpose
AI-powered coding consultant for primary care providers practicing in skilled nursing 
facilities and assisted living communities. Analyzes clinical notes and returns tiered 
ICD-10/CPT coding recommendations with HCC capture guidance.

## Architecture

### Core Files
- `system_prompt.py` — The agent's domain knowledge and output rules. This is the brain.
- `agent.py` — Main agent logic. Interactive terminal session + programmatic API.
- `batch_processor.py` — Process multiple notes from a JSON file.
- `example_notes.json` — Test notes for validation.

### Key Design Decisions
1. **Three-tier output structure**: Tier 1 (code now) / Tier 2 (confirm relevance) / 
   Tier 3 (documentation flag only). Prevents overcoding while surfacing missed captures.
2. **HCC-aware**: Every output includes an HCC scorecard for Medicare/MA patients.
3. **Billing alerts first**: Hospice modifier issues, POS errors, denial risks go first.
4. **Provider language**: Output written for clinicians, not coders.

## Running the Agent

### Interactive session (single note):
```bash
python agent.py
```
Paste note, type `---END---`, get analysis. Follow-up questions supported.

### Batch processing:
```bash
python batch_processor.py example_notes.json
python batch_processor.py notes.json --output results.json
```

### Programmatic use:
```python
from agent import run_coding_agent
analysis = run_coding_agent(note_text)  # pass string or dict
```

## Environment Setup
```bash
export ANTHROPIC_API_KEY=your_key_here
pip install anthropic
```

## Model
Using claude-opus-4-6 for maximum coding accuracy. Switch to claude-sonnet-4-6 
for faster/cheaper batch processing once validated.

## System Prompt Maintenance
Update system_prompt.py when:
- CMS updates HCC model categories (annually, January)
- New ICD-10 codes released (October 1 each year)
- E/M guidelines change
- Payer-specific rules are added

## Extending the Agent
- ICD-10 live lookup: Integrate CMS Coverage MCP server
- LCD/NCD coverage checks: Add cms_coverage_lookup tool calls
- Gehrimed integration: Chrome extension reading note DOM into side panel

## Known Limitations
- Cannot verify codes against live CMS databases
- No access to full chart history beyond the note provided
- Not a substitute for certified coder review on complex claims
