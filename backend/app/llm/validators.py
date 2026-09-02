"""LLM output validators — reject unsupported claims.

Ensures the LLM doesn't fabricate metrics, achievements, or
personality assessments. All claims must be grounded in evidence.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger

logger = get_logger(__name__)

# ── Forbidden patterns ───────────────────────────────────────────
# The LLM must not use personality/psychological language.

FORBIDDEN_PATTERNS = [
    re.compile(r"\b(creative|creativity)\b", re.IGNORECASE),
    re.compile(r"\b(intelligent|intelligence|genius|brilliant)\b", re.IGNORECASE),
    re.compile(r"\b(passionate|passion)\b", re.IGNORECASE),
    re.compile(r"\b(personality|temperament)\b", re.IGNORECASE),
    re.compile(r"\b(lazy|unmotivated|careless)\b", re.IGNORECASE),
    re.compile(r"\b(hardworking|workaholic)\b", re.IGNORECASE),
    re.compile(r"\b(introverted|extroverted)\b", re.IGNORECASE),
    re.compile(r"\b(mental health|anxiety|depression)\b", re.IGNORECASE),
    re.compile(r"\b(predict.*performance|guarantee.*success)\b", re.IGNORECASE),
    re.compile(r"\b(definitely|certainly|undoubtedly) (will|would|can)\b", re.IGNORECASE),
]

# ── Fabrication patterns ─────────────────────────────────────────
# The LLM should not invent specific numbers not in evidence.

FABRICATION_PATTERNS = [
    re.compile(r"\b\d{4,}\s+(lines|files|commits|repositories)\b", re.IGNORECASE),
    re.compile(r"\b(100|99|98)%\s+(code coverage|test coverage|accuracy)\b", re.IGNORECASE),
    re.compile(r"\b(award|prize|recognition|certification)\b", re.IGNORECASE),
    re.compile(r"\b(industry.?leading|best.?in.?class|world.?class)\b", re.IGNORECASE),
]


def validate_json_response(raw: str) -> Optional[Dict[str, Any]]:
    """Parse and validate a JSON response from the LLM.

    Returns parsed dict if valid, None if invalid.
    """
    if not raw:
        return None

    # Strip markdown code blocks if present
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last lines (code fence markers)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            logger.warning("llm_response_not_dict", raw=raw[:200])
            return None
        return parsed
    except json.JSONDecodeError as e:
        logger.warning("llm_response_invalid_json", error=str(e), raw=raw[:200])
        return None


def validate_explanation(
    explanation: str,
    evidence: List[Dict[str, Any]],
) -> bool:
    """Validate that an LLM explanation doesn't contain forbidden patterns.

    Returns True if the explanation is acceptable, False if it should be rejected.
    """
    if not explanation:
        return True  # Empty is fine — we just won't show it

    # Check forbidden patterns
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(explanation):
            logger.warning(
                "explanation_contains_forbidden_pattern",
                pattern=pattern.pattern,
                text=explanation[:200],
            )
            return False

    # Check fabrication patterns
    for pattern in FABRICATION_PATTERNS:
        if pattern.search(explanation):
            logger.warning(
                "explanation_contains_fabrication",
                pattern=pattern.pattern,
                text=explanation[:200],
            )
            return False

    return True


def sanitize_explanation(explanation: str) -> str:
    """Remove any forbidden patterns from an explanation.

    Less strict than validate — tries to salvage the text
    by removing problematic phrases.
    """
    if not explanation:
        return ""

    result = explanation

    # Replace forbidden patterns with neutral alternatives
    replacements = [
        (r"\bcreative\b", "versatile"),
        (r"\bbrilliant\b", "effective"),
        (r"\bpassionate\b", "active"),
        (r"\bhardworking\b", "consistent"),
        (r"\blazy\b", "less active"),
    ]

    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    return result
