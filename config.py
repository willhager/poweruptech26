"""Central configuration for the matching pipeline.

Tuning models and token budgets here is the main lever for controlling how
much of the Claude API credit budget each run consumes. All filesystem paths
the pipeline reads or writes are also defined here so nothing is hard-coded
deep in the modules.
"""

import os
from pathlib import Path

# --- Paths ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent

DATA_DIR = PROJECT_ROOT / "data"
COMPANIES_FILE = DATA_DIR / "companies.json"

PROMPTS_DIR = PROJECT_ROOT / "src" / "prompts"

# Everything generated at runtime lives under runtime/ (gitignored).
RUNTIME_DIR = PROJECT_ROOT / "runtime"
INCOMING_DIR = RUNTIME_DIR / "incoming"    # emails fetched from Gmail
PROCESSED_DIR = RUNTIME_DIR / "processed"  # emails already handled
RESULTS_DIR = RUNTIME_DIR / "results"      # final pipeline output JSON
DEBUG_DIR = RUNTIME_DIR / "debug"          # raw agent responses for debugging

# --- Models -----------------------------------------------------------------
# Two tiers so reasoning-heavy work can use a stronger (pricier) model while
# the mechanical extraction/drafting steps can use a cheaper one.
#
# To save credits, point FAST_MODEL at a Haiku-class model via env var, e.g.:
#   export FAST_MODEL="claude-haiku-..."
# Defaults intentionally match the model already used in the repo so nothing
# breaks out of the box.
FAST_MODEL = os.environ.get("FAST_MODEL", "claude-sonnet-5")   # extraction + drafting
SMART_MODEL = os.environ.get("SMART_MODEL", "claude-sonnet-5")  # matching / reasoning

# --- Output token ceilings (output tokens dominate cost) --------------------
AGENT1_MAX_TOKENS = int(os.environ.get("AGENT1_MAX_TOKENS", "1500"))  # profile JSON
AGENT2_MAX_TOKENS = int(os.environ.get("AGENT2_MAX_TOKENS", "1200"))  # matches + reasoning
AGENT3_MAX_TOKENS = int(os.environ.get("AGENT3_MAX_TOKENS", "1600"))  # up to 3 drafts

# --- Free dry-run mode ------------------------------------------------------
# Set MOCK_CLAUDE=1 to run the ENTIRE pipeline end-to-end using canned
# responses and zero API calls. Use this to verify wiring before spending
# any credits.
MOCK_CLAUDE = os.environ.get("MOCK_CLAUDE", "0") == "1"
