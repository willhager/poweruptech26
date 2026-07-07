"""Central configuration for the matching pipeline.

Tuning models and token budgets here is the main lever for controlling how
much of the LLM API budget each run consumes. All filesystem paths the
pipeline reads or writes are also defined here so nothing is hard-coded deep
in the modules.
"""

import os
from pathlib import Path

# --- Paths ------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent

# Load variables from a project-root .env file (e.g. GEMINI_API_KEY,
# ANTHROPIC_API_KEY, LLM_PROVIDER) so they don't have to be exported by hand.
# Real environment variables always take precedence over .env values.
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    # python-dotenv is optional; without it, only real env vars are used.
    pass

DATA_DIR = PROJECT_ROOT / "data"
COMPANIES_FILE = DATA_DIR / "companies.json"

PROMPTS_DIR = PROJECT_ROOT / "src" / "prompts"

# Everything generated at runtime lives under runtime/ (gitignored).
RUNTIME_DIR = PROJECT_ROOT / "runtime"
INCOMING_DIR = RUNTIME_DIR / "incoming"    # emails fetched from Gmail
PROCESSED_DIR = RUNTIME_DIR / "processed"  # emails already handled
RESULTS_DIR = RUNTIME_DIR / "results"      # final pipeline output JSON
DEBUG_DIR = RUNTIME_DIR / "debug"          # raw agent responses for debugging

# --- Provider ---------------------------------------------------------------
# Which LLM backend to use. Defaults to Gemini, whose free tier is ideal for
# testing. Set LLM_PROVIDER=claude (and ANTHROPIC_API_KEY) to switch to Claude
# once the pipeline is verified — no other code changes required.
#   Gemini auth: set GEMINI_API_KEY (or GOOGLE_API_KEY)
#   Claude auth: set ANTHROPIC_API_KEY
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").strip().lower()

# --- Models -----------------------------------------------------------------
# Two tiers so reasoning-heavy work can use a stronger model while the
# mechanical extraction/drafting steps can use a cheaper/faster one. Defaults
# depend on the selected provider; override either via env var.
#
# Gemini free-tier note: the *-flash models are covered by the free tier. For
# stronger reasoning on Agent 2 you can set SMART_MODEL=gemini-2.5-pro, but the
# pro free-tier quota is much smaller.
_DEFAULT_MODELS = {
    "gemini": {"fast": "gemini-2.5-flash", "smart": "gemini-2.5-flash"},
    "claude": {"fast": "claude-sonnet-5", "smart": "claude-sonnet-5"},
}
_defaults = _DEFAULT_MODELS.get(LLM_PROVIDER, _DEFAULT_MODELS["gemini"])

FAST_MODEL = os.environ.get("FAST_MODEL", _defaults["fast"])    # extraction + drafting
SMART_MODEL = os.environ.get("SMART_MODEL", _defaults["smart"])  # matching / reasoning

# --- Output token ceilings (output tokens dominate cost) --------------------
# These must be large enough to hold the FULL JSON answer — if the model runs
# out of budget mid-object, the truncated JSON fails to parse. Agent 1's
# profile schema in particular is big, and Gemini is more verbose than Claude,
# so the ceilings are generous. Lower them via env var to cap spend once you
# know your typical output sizes.
AGENT1_MAX_TOKENS = int(os.environ.get("AGENT1_MAX_TOKENS", "4096"))  # profile JSON
AGENT2_MAX_TOKENS = int(os.environ.get("AGENT2_MAX_TOKENS", "4096"))  # matches + reasoning
AGENT3_MAX_TOKENS = int(os.environ.get("AGENT3_MAX_TOKENS", "4096"))  # up to 3 drafts

# --- Free dry-run mode ------------------------------------------------------
# Set MOCK_LLM=1 to run the ENTIRE pipeline end-to-end using canned responses
# and zero API calls. Use this to verify wiring before spending any credits.
# (The legacy MOCK_CLAUDE name is still honored for backwards compatibility.)
MOCK_LLM = os.environ.get("MOCK_LLM", os.environ.get("MOCK_CLAUDE", "0")) == "1"
