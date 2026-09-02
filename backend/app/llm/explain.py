"""LLM explanation service — Gemini structured output integration.

Uses Gemini's free tier for natural-language explanations of
deterministic insights. The LLM never generates scores or evidence —
it only explains pre-computed facts.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.config import settings
from app.llm.prompts import (
    SYSTEM_PROMPT,
    build_insight_explanation_prompt,
    build_next_challenge_prompt,
    build_profile_summary_prompt,
)
from app.llm.validators import validate_explanation, validate_json_response
from app.logging_config import get_logger

logger = get_logger(__name__)


async def _call_gemini(prompt: str) -> Optional[str]:
    """Call Gemini API and return the text response.

    Returns None if the API is unavailable or fails.
    """
    if not settings.gemini_api_key:
        logger.debug("gemini_api_key_not_set, skipping LLM call")
        return None

    try:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "temperature": 0.3,
                "max_output_tokens": 500,
                "response_mime_type": "application/json",
            },
        )

        if response and response.text:
            return response.text.strip()
        return None

    except ImportError:
        logger.warning("google_genai_not_installed")
        return None
    except Exception as e:
        logger.warning("gemini_api_error", error=str(e))
        return None


async def explain_insight(
    insight_title: str,
    insight_type: str,
    score: float,
    evidence: List[Dict[str, Any]],
) -> Dict[str, str]:
    """Generate an LLM explanation for a single insight.

    Returns dict with 'explanation' and 'recommendation' keys.
    Falls back to empty strings if LLM is unavailable.
    """
    prompt = build_insight_explanation_prompt(
        insight_title, insight_type, score, evidence,
    )

    raw = await _call_gemini(prompt)
    if not raw:
        return {"explanation": "", "recommendation": ""}

    parsed = validate_json_response(raw)
    if not parsed:
        return {"explanation": "", "recommendation": ""}

    # Validate the explanation doesn't contain fabricated claims
    explanation = parsed.get("explanation", "")
    recommendation = parsed.get("recommendation", "")

    if not validate_explanation(explanation, evidence):
        logger.warning("explanation_failed_validation", title=insight_title)
        return {"explanation": "", "recommendation": ""}

    return {
        "explanation": explanation,
        "recommendation": recommendation,
    }


async def generate_profile_summary(
    username: str,
    fingerprint: Dict[str, float],
    confidence: float,
    repos_analyzed: int,
    top_strengths: List[str],
    top_gaps: List[str],
) -> Dict[str, str]:
    """Generate a natural-language profile summary.

    Returns dict with 'summary' and 'headline' keys.
    """
    prompt = build_profile_summary_prompt(
        username, fingerprint, confidence,
        repos_analyzed, top_strengths, top_gaps,
    )

    raw = await _call_gemini(prompt)
    if not raw:
        # Fallback: generate a simple summary without LLM
        strong = ", ".join(s.replace("_", " ").title() for s in top_strengths[:3])
        return {
            "summary": f"Based on {repos_analyzed} analyzed repositories, "
                       f"this profile shows strength in {strong or 'general development'}. "
                       f"Profile confidence: {confidence:.0%}.",
            "headline": f"Developer with {repos_analyzed} analyzed projects",
        }

    parsed = validate_json_response(raw)
    if not parsed:
        return {
            "summary": "",
            "headline": f"Developer with {repos_analyzed} analyzed projects",
        }

    return {
        "summary": parsed.get("summary", ""),
        "headline": parsed.get("headline", ""),
    }


async def generate_next_challenge(
    top_gaps: List[str],
    current_strengths: List[str],
    target_role: str,
    existing_technologies: List[str],
) -> Optional[Dict[str, Any]]:
    """Generate a next-challenge project recommendation.

    Returns a challenge dict or None if LLM is unavailable.
    """
    prompt = build_next_challenge_prompt(
        top_gaps, current_strengths, target_role, existing_technologies,
    )

    raw = await _call_gemini(prompt)
    if not raw:
        return None

    parsed = validate_json_response(raw)
    return parsed
