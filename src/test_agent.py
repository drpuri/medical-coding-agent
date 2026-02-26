"""
Quick test — runs the agent against a sample note to validate setup.
Run from /src directory: python test_agent.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from agent import run_coding_agent

# Minimal test note — chronic systolic CHF follow-up in SNF
TEST_NOTE = """
Patient: Elderly male, mid-80s. Setting: Skilled Nursing Facility.
Visit: Subsequent, routine follow-up.

HPI: Patient seen for chronic condition management. No acute complaints.
Hemodynamically stable. Weight unchanged from last week. No lower extremity edema today.

Active Diagnoses Addressed:
- Chronic systolic congestive heart failure — stable, continue current regimen
- Type 2 diabetes with peripheral neuropathy — last HbA1c 7.8, continue metformin  
- Hypertension — BP 128/76 today, continue lisinopril
- CKD Stage 3 — stable creatinine 1.6

PMH: Coronary artery disease, prior MI, CABG x3 (2018)

Medications reviewed. No changes today.

Assessment: All chronic conditions stable. Continue current management.
Follow up in 2 weeks or sooner if acute change.
"""

if __name__ == "__main__":
    print("Running test note through coding agent...\n")
    print("─" * 60)
    
    result = run_coding_agent(TEST_NOTE, verbose=True)
    
    print("\n" + "─" * 60)
    print("AGENT OUTPUT:")
    print("─" * 60)
    print(result)
