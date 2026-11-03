"""
main.py — Webhook Server
==========================
FastAPI application that receives failing CI/CD build logs, delegates
reasoning to the Meta Llama model, and triggers an automatic GitHub PR
with the proposed fix.
"""

import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from github_integration import create_healing_pr
from meta_llm import analyze_build_error

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── FastAPI app ──────────────────────────────────────────────────────────
app = FastAPI(
    title="Self-Healing CI/CD Pipeline Agent",
    description=(
        "Intercepts failing CI/CD build logs via webhook, uses Meta Llama 3 "
        "to deduce a code fix, and opens a GitHub Pull Request automatically."
    ),
    version="1.0.0",
)


# ── Request / Response models ───────────────────────────────────────────
class CIWebhookPayload(BaseModel):
    """Payload sent by a CI/CD system (GitHub Actions, Jenkins, etc.)."""

    build_id: str = Field(
        ...,
        description="Unique identifier of the failing build run.",
        examples=["run-48291"],
    )
    log_output: str = Field(
        ...,
        description="Raw log output from the failing build step.",
        examples=[
            "ERROR: Could not find a version that satisfies the requirement foo==9.9.9"
        ],
    )


class HealingResponse(BaseModel):
    """Successful response returned after creating a healing PR."""

    status: str = "healed"
    build_id: str
    pr_url: str
    fix_summary: dict


# ── Health check ─────────────────────────────────────────────────────────
@app.get("/", tags=["health"])
async def health_check():
    """Root health-check endpoint."""
    return {
        "service": "Self-Healing CI/CD Pipeline Agent",
        "status": "operational",
        "version": "1.0.0",
    }


# ── Webhook endpoint ────────────────────────────────────────────────────
@app.post(
    "/webhook",
    response_model=HealingResponse,
    tags=["webhook"],
    summary="Receive a failing CI/CD build log and auto-heal it",
)
async def receive_webhook(payload: CIWebhookPayload):
    """
    End-to-end self-healing pipeline:

    1. **Receive** the failing build log from any CI/CD system.
    2. **Analyze** the log with Meta Llama 3 70B-Instruct to produce a
       structured fix (file path, search/replace strings, commit message).
    3. **Apply** the fix on a new branch and open a Pull Request via the
       GitHub API.
    4. **Return** the PR URL so the CI system (or human) can review and
       merge.
    """

    logger.info(
        "Webhook received — build_id=%s, log length=%d chars",
        payload.build_id,
        len(payload.log_output),
    )

    # ── Step 1: AI Analysis ──────────────────────────────────────────
    try:
        fix_data = analyze_build_error(payload.log_output)
    except RuntimeError as exc:
        logger.error("LLM analysis failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"AI analysis failed: {exc}",
        ) from exc

    logger.info(
        "AI fix proposal — file: %s | commit: %s",
        fix_data.get("file_path"),
        fix_data.get("commit_message"),
    )

    # ── Step 2: GitHub Auto-Heal ─────────────────────────────────────
    try:
        pr_url = create_healing_pr(fix_data)
    except RuntimeError as exc:
        logger.error("GitHub integration failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"GitHub integration failed: {exc}",
        ) from exc

    logger.info("Healing complete — PR: %s", pr_url)

    return HealingResponse(
        build_id=payload.build_id,
        pr_url=pr_url,
        fix_summary=fix_data,
    )
