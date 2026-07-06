"""Entry point for the startup <-> company matching pipeline.

Usage:
    python main.py                # fetch new emails + run full pipeline
    python main.py --no-fetch     # skip Gmail, process files already in runtime/incoming
    MOCK_CLAUDE=1 python main.py --no-fetch   # free dry-run, no API calls
"""

import sys

from src.controller import main

if __name__ == "__main__":
    fetch = "--no-fetch" not in sys.argv
    main(fetch=fetch)
