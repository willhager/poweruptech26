"""Entry point for the startup <-> company matching pipeline.

Usage:
    python main.py                # fetch new emails + run full pipeline + email report
    python main.py --no-fetch     # skip Gmail, process files already in runtime/incoming
    python main.py --no-send      # run the pipeline but don't email the report back
    MOCK_LLM=1 python main.py --no-fetch      # free dry-run, no API calls

Provider (see config.py): defaults to Gemini's free tier for testing.
    GEMINI_API_KEY=... python main.py                     # run on Gemini
    LLM_PROVIDER=claude ANTHROPIC_API_KEY=... python main.py   # switch to Claude
"""

import sys

from src.controller import main

if __name__ == "__main__":
    fetch = "--no-fetch" not in sys.argv
    send = "--no-send" not in sys.argv
    main(fetch=fetch, send=send)
