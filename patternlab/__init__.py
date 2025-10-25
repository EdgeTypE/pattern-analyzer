"""PatternLab - Binary pattern analysis framework."""

__version__ = "0.1.0"

# Expose a package-level logger so tests and plugins can call:
#   from patternlab import logger
#   logger.debug("...")
# The Engine configures handlers (e.g. JSONL FileHandler) when run with a `log_path`.
import logging
logger = logging.getLogger("patternlab")
# Provide a NullHandler by default to avoid "No handler found" warnings if not configured.
logger.addHandler(logging.NullHandler())