"""LLM prompt templates for evidence-based explanations.

All prompts enforce:
- Evidence-only context (no invented data)
- Structured JSON output
- Observable-pattern language (no personality claims)
"""

from __future__ import annotations

from typing import Any, Dict, List


SYSTEM_PROMPT = """You are MIRROR AI's explanation engine. You generate concise, evidence-backed explanations of developer engineering patterns.

RULES:
1. Only reference evidence provided in the context. Never invent achievements or metrics.
2. Use "observable pattern" language: say "The repositories show..." not "The developer is..."
3. Never infer personality, intelligence, creativity, or psychological traits.
4. If evidence is weak or sparse, say so explicitly.
5. Keep explanations under 3 sentences.
6. Be specific — reference repo names, metric values, and file patterns.
7. Output valid JSON matching the requested schema exactly."""


def build_insight_explanation_prompt(
    insight_title: str,
    insight_type: str,
    score: float,
    evidence: List[Dict[str, Any]],
) -> str:
    """Build a prompt for explaining a single insight."""
    evidence_text = "\n".join(
        f"  - {e.get('repo_name', 'unknown')}: {e.get('metric_name', '')} = {e.get('metric_value', 0)}"
        f" ({e.get('context', '')})"
        for e in evidence
    )

    return f"""Explain this engineering insight in 2-3 sentences. Reference the evidence directly.

INSIGHT: {insight_title}
TYPE: {insight_type}
SCORE: {score}/100

EVIDENCE:
{evidence_text if evidence_text.strip() else "  No specific evidence available."}

Respond with JSON:
{{"explanation": "Your 2-3 sentence explanation referencing the evidence.", "recommendation": "One actionable next step."}}"""


def build_profile_summary_prompt(
    username: str,
    fingerprint: Dict[str, float],
    confidence: float,
    repos_analyzed: int,
    top_strengths: List[str],
    top_gaps: List[str],
) -> str:
    """Build a prompt for generating a profile summary."""
    dims = "\n".join(f"  - {k.replace('_', ' ').title()}: {v:.0f}/100" for k, v in fingerprint.items())

    return f"""Generate a 3-4 sentence engineering profile summary for GitHub user '{username}'.

PROFILE DATA:
  Confidence: {confidence:.0%}
  Repositories analyzed: {repos_analyzed}

DIMENSIONS:
{dims}

TOP STRENGTHS: {', '.join(s.replace('_', ' ').title() for s in top_strengths) if top_strengths else 'None identified'}
TOP GAPS: {', '.join(g.replace('_', ' ').title() for g in top_gaps) if top_gaps else 'None identified'}

RULES:
- Reference actual dimension scores
- Use "observable patterns" language
- Mention confidence level if below 50%
- Do not claim personality traits

Respond with JSON:
{{"summary": "Your 3-4 sentence profile summary.", "headline": "A one-line tagline like 'ML-focused engineer with strong testing discipline'"}}"""


def build_next_challenge_prompt(
    top_gaps: List[str],
    current_strengths: List[str],
    target_role: str,
    existing_technologies: List[str],
) -> str:
    """Build a prompt for generating a next-challenge project recommendation."""
    return f"""Recommend ONE project that closes the developer's top skill gaps while leveraging existing strengths.

TARGET ROLE: {target_role}
TOP GAPS: {', '.join(g.replace('_', ' ').title() for g in top_gaps)}
STRENGTHS: {', '.join(s.replace('_', ' ').title() for s in current_strengths)}
EXISTING TECH: {', '.join(existing_technologies)}

The project must:
- Address at least 2 of the top gaps
- Use some existing technologies (don't start from scratch)
- Be achievable in 2-4 weeks
- Produce a deployable artifact

Respond with JSON:
{{"title": "Project title", "description": "2-3 sentence description", "technologies": ["tech1", "tech2"], "milestones": ["step1", "step2", "step3", "step4", "step5"], "why_this_project": "1 sentence explaining gap closure"}}"""
