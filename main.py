"""
main.py — Webhook Server
==========================
FastAPI application that receives failing CI/CD build logs, delegates
reasoning to the Meta Llama model, and triggers an automatic GitHub PR
with the proposed fix.
"""

import logging
import os
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field

from github_integration import create_healing_pr
from meta_llm import analyze_build_error

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agent.log", mode="a", encoding="utf-8"),
    ],
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
    """Payload sent by any CI/CD system (GitHub Actions, Jenkins, GitLab, etc.)."""

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
    repo_owner: Optional[str] = Field(
        None,
        description="Target GitHub organization or username (optional, falls back to .env default).",
        examples=["ChaninduImanjith"],
    )
    repo_name: Optional[str] = Field(
        None,
        description="Target GitHub repository name (optional, falls back to .env default).",
        examples=["self-healing-cicd-agent"],
    )
    branch: Optional[str] = Field(
        None,
        description="Target base branch to branch off and merge into (optional, defaults to repo default branch).",
        examples=["main"],
    )
    ci_provider: Optional[str] = Field(
        "github-actions",
        description="Originating CI/CD platform (e.g. github-actions, jenkins, gitlab-ci).",
        examples=["github-actions"],
    )


class HealingResponse(BaseModel):
    """Response returned upon receiving and processing a self-healing event."""

    status: str = "processing"
    build_id: str
    repository: str
    target_branch: str
    message: str
    pr_url: Optional[str] = None
    fix_summary: Optional[dict] = None


def execute_self_healing(payload: CIWebhookPayload) -> None:
    """Asynchronous background worker that performs Meta AI analysis and opens GitHub PR."""
    target_owner = payload.repo_owner or os.getenv("GITHUB_REPO_OWNER", "")
    target_repo = payload.repo_name or os.getenv("GITHUB_REPO_NAME", "")
    target_branch = payload.branch or "default"

    logger.info(
        "Beginning background healing — build_id=%s, target=%s/%s (branch: %s)",
        payload.build_id,
        target_owner,
        target_repo,
        target_branch,
    )
    logger.info("Received build log preview: %s", repr(payload.log_output[:150]))

    try:
        fix_data = analyze_build_error(payload.log_output)
        logger.info(
            "AI fix proposed — file: %s | commit: %s",
            fix_data.get("file_path"),
            fix_data.get("commit_message"),
        )
        pr_url = create_healing_pr(
            fix_data=fix_data,
            repo_owner=payload.repo_owner,
            repo_name=payload.repo_name,
            target_branch=payload.branch,
        )
        if pr_url:
            logger.info("Autonomous healing complete — PR: %s", pr_url)
        else:
            logger.info("Target file already clean on target branch — no PR required.")
    except Exception as exc:
        logger.error("Background healing failed: %s", exc, exc_info=True)


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
    summary="Receive a failing CI/CD build log and auto-heal it asynchronously",
)
async def receive_webhook(
    payload: CIWebhookPayload,
    background_tasks: BackgroundTasks,
):
    """
    End-to-end self-healing pipeline:

    1. **Acknowledge** webhook immediately to prevent upstream timeouts (e.g. Cloudflare / API gateways).
    2. **Analyze** the log asynchronously using Meta AI (muse-spark-1.3 reasoning engine).
    3. **Apply** the fix on a new branch and open a Pull Request via GitHub API.
    """
    target_owner = payload.repo_owner or os.getenv("GITHUB_REPO_OWNER", "")
    target_repo = payload.repo_name or os.getenv("GITHUB_REPO_NAME", "")
    target_branch = payload.branch or "default"

    logger.info(
        "Webhook received — build_id=%s, target=%s/%s (branch: %s), provider=%s",
        payload.build_id,
        target_owner,
        target_repo,
        target_branch,
        payload.ci_provider,
    )

    # Queue background task for non-blocking execution
    background_tasks.add_task(execute_self_healing, payload)

    return HealingResponse(
        status="processing",
        build_id=payload.build_id,
        repository=f"{target_owner}/{target_repo}",
        target_branch=target_branch,
        message="Self-healing pipeline initiated. Analysis and PR generation running asynchronously.",
    )
