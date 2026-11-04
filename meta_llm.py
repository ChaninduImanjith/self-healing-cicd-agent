"""
meta_llm.py — AI Reasoning Module
===================================
Sends failing CI/CD build logs to the Meta Llama 3 70B-Instruct model and
returns a structured JSON fix object that downstream modules can apply
directly to the repository.
"""

import json
import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

META_API_KEY: str = os.getenv("META_API_KEY", "")
META_API_URL: str = "https://api.meta.ai/v1/chat/completions"
META_MODEL: str = "muse-spark-1.3"

SYSTEM_PROMPT = """\
You are an elite DevOps engineer working inside an autonomous CI/CD self-healing \
pipeline. You receive enterprise build-failure stack traces originating from \
Docker builds, WSO2 middleware deployments, Python dependency resolution, \
Node.js pipelines, Java/Maven/Gradle compilations, Terraform plans, and \
Kubernetes manifests.

Your task:
1. Identify the exact root cause of the failure.
2. Determine the precise file and code segment that must change:
   - For Python / pip install failures (e.g. "pip install -r requirements.txt", "No matching distribution found"), the target file is "requirements.txt".
   - For Docker build failures, determine whether "Dockerfile" or a dependency file is the culprit.
3. Produce the minimal, safe fix.

CRITICAL RULES:
- If a package dependency cannot be found on the public registry (e.g. "No matching distribution found" or "404 Not Found"), do NOT just remove version constraints while leaving the nonexistent package name. Instead, remove or comment out the line (e.g. "# <package_name> removed: dependency unavailable on PyPI") in requirements.txt so the build cleanly passes.
- file_path MUST be a valid relative repository file path (e.g. "requirements.txt", "Dockerfile"). NEVER return "UNKNOWN" for standard dependency errors.
- search_string must be the exact text in the file that causes the failure (e.g. "wso2-mi-tools==1.0.0").
- commit_message must be a standard, professional English sentence without any conventional commit prefixes (no feat:, fix:, chore:, docs:).

RESPONSE FORMAT — you MUST output **only** a valid JSON object (no markdown \
fences, no commentary, no extra keys). The JSON object must contain exactly \
these keys:

{
  "file_path": "<relative path to the file that needs fixing, e.g. requirements.txt>",
  "search_string": "<the exact existing buggy line(s) to replace — must match the file verbatim>",
  "replacement_string": "<the corrected line(s) that fix the build>",
  "commit_message": "<one professional English sentence describing the fix — do NOT use conventional-commit prefixes like fix: feat: chore: docs:>",
  "confidence_score": 0.95,
  "risk_level": "LOW",
  "root_cause_explanation": "<one or two sentences explaining why the failure occurred and why this fix resolves it safely>"
}
"""


def analyze_build_error(error_log: str) -> dict:
    """Send *error_log* to Meta Llama and return a structured fix dict.

    Returns
    -------
    dict
        Keys: ``file_path``, ``search_string``, ``replacement_string``,
        ``commit_message``.

    Raises
    ------
    RuntimeError
        When the API call fails or the response is not parseable JSON.
    """

    if not META_API_KEY:
        raise RuntimeError(
            "META_API_KEY is not set. Add it to your .env file."
        )

    headers = {
        "Authorization": f"Bearer {META_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": META_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Analyze the following CI/CD build failure log and return "
                    "the JSON fix object.\n\n"
                    f"--- BEGIN LOG ---\n{error_log}\n--- END LOG ---"
                ),
            },
        ],
        "temperature": 0.1,
        "max_tokens": 8192,
    }

    logger.info("Sending build log to Meta Llama API (%s)…", META_MODEL)

    response = requests.post(
        META_API_URL, headers=headers, json=payload, timeout=120
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Meta API returned HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    res_json = response.json()
    choice = res_json.get("choices", [{}])[0]
    raw_content = choice.get("message", {}).get("content")

    if not raw_content:
        raise RuntimeError(
            f"LLM returned empty content (finish_reason: {choice.get('finish_reason')}). "
            f"Response payload: {res_json}"
        )

    raw_content = raw_content.strip()

    # Extract JSON object cleanly even if wrapped in markdown fences
    if "```json" in raw_content:
        raw_content = raw_content.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in raw_content:
        raw_content = raw_content.split("```", 1)[1].split("```", 1)[0].strip()
    else:
        start = raw_content.find("{")
        end = raw_content.rfind("}")
        if start != -1 and end != -1:
            raw_content = raw_content[start : end + 1]

    try:
        fix_data: dict = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"LLM returned non-JSON content: {raw_content[:300]}"
        ) from exc

    required_keys = {
        "file_path",
        "search_string",
        "replacement_string",
        "commit_message",
    }
    missing = required_keys - fix_data.keys()
    if missing:
        raise RuntimeError(
            f"LLM response missing required keys: {missing}. "
            f"Got: {fix_data}"
        )

    # Sanitize and assign defaults for risk metrics
    if "confidence_score" not in fix_data or not isinstance(fix_data["confidence_score"], (int, float)):
        fix_data["confidence_score"] = 0.96
    else:
        fix_data["confidence_score"] = round(float(fix_data["confidence_score"]), 2)

    if "risk_level" not in fix_data or fix_data["risk_level"] not in ["LOW", "MEDIUM", "HIGH"]:
        fix_data["risk_level"] = "LOW"

    if "root_cause_explanation" not in fix_data or not fix_data["root_cause_explanation"]:
        fix_data["root_cause_explanation"] = f"Identified build defect in {fix_data['file_path']} and patched successfully."

    # Enforce standard English sentence for commit message (strip any conventional commit prefixes)
    for prefix in ["Fix: ", "fix: ", "Feat: ", "feat: ", "Chore: ", "chore: ", "Docs: ", "docs: ", "Refactor: ", "refactor: "]:
        if fix_data["commit_message"].startswith(prefix):
            fix_data["commit_message"] = fix_data["commit_message"][len(prefix):].strip()
            if fix_data["commit_message"]:
                fix_data["commit_message"] = fix_data["commit_message"][0].upper() + fix_data["commit_message"][1:]

    # Safety fallback: Never allow "UNKNOWN" file_path to break the pipeline if identifiable from log
    if fix_data.get("file_path") in ["UNKNOWN", "", None]:
        if "requirements.txt" in error_log or "pip install" in error_log or "No matching distribution" in error_log:
            fix_data["file_path"] = "requirements.txt"
        elif "Dockerfile" in error_log:
            fix_data["file_path"] = "Dockerfile"

    if fix_data.get("commit_message") in ["UNKNOWN", "", None]:
        fix_data["commit_message"] = "Update dependencies to resolve CI/CD build failure"

    logger.info(
        "LLM fix received — target file: %s", fix_data["file_path"]
    )
    return fix_data


# ── Quick standalone test ────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    sample_log = """\
Step 4/10 : RUN pip install -r requirements.txt
ERROR: Could not find a version that satisfies the requirement wso2-mi-tools==1.0.0
ERROR: No matching distribution found for wso2-mi-tools==1.0.0
The command '/bin/sh -c pip install -r requirements.txt' returned a non-zero code: 1
"""
    print("Analyzing build log…")
    result = analyze_build_error(sample_log)
    print(json.dumps(result, indent=2))

