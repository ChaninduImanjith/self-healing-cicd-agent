"""
github_integration.py — Auto-Healing Module
=============================================
Uses PyGithub to apply the LLM-generated fix to a new branch and open a
Pull Request against the main branch.
"""

import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from github import Auth, Github, GithubException

load_dotenv()

logger = logging.getLogger(__name__)

GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO_OWNER: str = os.getenv("GITHUB_REPO_OWNER", "")
GITHUB_REPO_NAME: str = os.getenv("GITHUB_REPO_NAME", "")


def _get_repo():
    """Authenticate and return the target ``Repository`` object."""
    if not GITHUB_TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN is not set. Add it to your .env file."
        )
    if not GITHUB_REPO_OWNER or not GITHUB_REPO_NAME:
        raise RuntimeError(
            "GITHUB_REPO_OWNER and GITHUB_REPO_NAME must be set in .env."
        )

    gh = Github(auth=Auth.Token(GITHUB_TOKEN))
    repo = gh.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
    logger.info("Authenticated to GitHub repo: %s", repo.full_name)
    return repo


def create_healing_pr(fix_data: dict) -> str:
    """Apply *fix_data* to a new branch and open a Pull Request.

    Parameters
    ----------
    fix_data : dict
        Must contain ``file_path``, ``search_string``,
        ``replacement_string``, and ``commit_message``.

    Returns
    -------
    str
        The URL of the newly created Pull Request.

    Raises
    ------
    RuntimeError
        On GitHub API errors or when the target file / search string is
        not found.
    """

    file_path: str = fix_data["file_path"]
    search_string: str = fix_data["search_string"]
    replacement_string: str = fix_data["replacement_string"]
    commit_message: str = fix_data["commit_message"]

    repo = _get_repo()

    # ── 1. Resolve the default branch (usually "main") ───────────────
    default_branch: str = repo.default_branch
    base_ref = repo.get_git_ref(f"heads/{default_branch}")
    base_sha: str = base_ref.object.sha
    logger.info(
        "Default branch '%s' at commit %s", default_branch, base_sha[:8]
    )

    # ── 2. Create a uniquely-named fix branch ────────────────────────
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    new_branch = f"auto-fix/run-{timestamp}"

    try:
        repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=base_sha)
    except GithubException as exc:
        raise RuntimeError(
            f"Failed to create branch '{new_branch}': {exc.data}"
        ) from exc

    logger.info("Created branch: %s", new_branch)

    # ── 3. Fetch the target file from the new branch ─────────────────
    try:
        contents = repo.get_contents(file_path, ref=new_branch)
    except GithubException as exc:
        raise RuntimeError(
            f"File '{file_path}' not found in repo: {exc.data}"
        ) from exc

    original_content: str = contents.decoded_content.decode("utf-8")

    if search_string not in original_content:
        raise RuntimeError(
            f"search_string not found in '{file_path}'. "
            "The LLM may have hallucinated the snippet. "
            "Manual intervention required."
        )

    # ── 4. Apply the fix ─────────────────────────────────────────────
    updated_content = original_content.replace(
        search_string, replacement_string, 1
    )

    repo.update_file(
        path=file_path,
        message=commit_message,
        content=updated_content,
        sha=contents.sha,
        branch=new_branch,
    )
    logger.info("Committed fix to %s on branch %s", file_path, new_branch)

    # ── 5. Open a Pull Request ───────────────────────────────────────
    pr_title = commit_message  # Already a professional English sentence
    pr_body = (
        "## Automated Self-Healing Fix\n\n"
        "This pull request was generated automatically by the "
        "**Self-Healing CI/CD Pipeline Agent**.\n\n"
        f"**File changed:** `{file_path}`\n\n"
        "### What was wrong\n"
        "```\n"
        f"{search_string}\n"
        "```\n\n"
        "### What was applied\n"
        "```\n"
        f"{replacement_string}\n"
        "```\n\n"
        "> Review carefully before merging. "
        "AI-generated fixes should always be validated by a human."
    )

    try:
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=new_branch,
            base=default_branch,
        )
    except GithubException as exc:
        raise RuntimeError(
            f"Failed to create Pull Request: {exc.data}"
        ) from exc

    logger.info("Pull Request created: %s", pr.html_url)
    return pr.html_url

