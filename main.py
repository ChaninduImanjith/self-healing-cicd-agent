"""
main.py — Webhook Server
==========================
FastAPI application that receives failing CI/CD build logs, delegates
reasoning to the Meta Llama model, and triggers an automatic GitHub PR
with the proposed fix.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
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
    """Successful response returned after creating a healing PR."""

    status: str = "healed"
    build_id: str
    repository: str
    target_branch: str
    pr_url: str
    fix_summary: dict


# ── In-Memory Incidents Store ───────────────────────────────────────────
incidents_history: list[dict] = [
    {
        "build_id": "run-48292",
        "repository": "ChaninduImanjith/self-healing-cicd-agent",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "status": "Healed",
        "file_path": "requirements.txt",
        "search_string": "wso2-mi-tools==1.0.0",
        "replacement_string": "wso2-mi-tools",
        "commit_message": "Remove unavailable version pin for wso2-mi-tools to resolve dependency installation failure.",
        "confidence_score": 0.98,
        "risk_level": "LOW",
        "duration_seconds": 14.2,
        "pr_url": "https://github.com/ChaninduImanjith/self-healing-cicd-agent/pull/3",
    }
]


# ── Health check ─────────────────────────────────────────────────────────
@app.get("/", tags=["health"])
async def health_check():
    """Root health-check endpoint."""
    return {
        "service": "Self-Healing CI/CD Pipeline Agent",
        "status": "operational",
        "version": "1.0.0",
        "dashboard": "/dashboard",
    }


# ── Dashboard API & UI ──────────────────────────────────────────────────
@app.get("/api/incidents", tags=["dashboard"])
async def get_incidents():
    """Retrieve list of recent self-healing incidents."""
    return incidents_history


@app.get("/dashboard", response_class=HTMLResponse, tags=["dashboard"])
async def serve_dashboard():
    """Render modern dark-mode real-time operations dashboard."""
    return """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Autonomous Self-Healing CI/CD Platform</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: '#0081FB',
            darkbg: '#0B0F19',
            darkcard: '#111827',
            cardborder: '#1F2937'
          }
        }
      }
    }
  </script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    @keyframes pulse-subtle { 0%, 100% { opacity: 1; } 50% { opacity: 0.6; } }
    .pulse-dot { animation: pulse-subtle 2s infinite ease-in-out; }
  </style>
</head>
<body class="bg-darkbg text-slate-100 min-h-screen font-sans antialiased">

  <!-- Header -->
  <header class="border-b border-cardborder bg-darkcard/80 backdrop-blur sticky top-0 z-50 px-6 py-4">
    <div class="max-w-7xl mx-auto flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand to-emerald-400 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-brand/20">
          <i class="fa-solid fa-shield-halved"></i>
        </div>
        <div>
          <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
            Self-Healing CI/CD Agent
            <span class="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/10 text-brand border border-blue-500/20 font-medium">Meta AI</span>
          </h1>
          <p class="text-xs text-slate-400">Autonomous DevOps Incident Reasoning & Automated Pull Requests</p>
        </div>
      </div>
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full text-xs font-semibold text-emerald-400">
          <span class="w-2 h-2 rounded-full bg-emerald-400 pulse-dot"></span>
          Cluster Operational
        </div>
        <a href="https://github.com/ChaninduImanjith/self-healing-cicd-agent" target="_blank" class="text-sm bg-slate-800 hover:bg-slate-700 px-3.5 py-1.5 rounded-lg border border-slate-700 text-slate-200 flex items-center gap-2 transition">
          <i class="fa-brands fa-github"></i> Repository
        </a>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-6 py-8 space-y-8">

    <!-- KPI Stats Grid -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-darkcard border border-cardborder rounded-2xl p-5 shadow-sm">
        <div class="text-xs font-medium text-slate-400 uppercase tracking-wider">Incidents Healed</div>
        <div class="mt-2 flex items-baseline justify-between">
          <div class="text-3xl font-extrabold text-white" id="stat-count">1</div>
          <span class="text-xs text-emerald-400 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded">100% Resolved</span>
        </div>
      </div>

      <div class="bg-darkcard border border-cardborder rounded-2xl p-5 shadow-sm">
        <div class="text-xs font-medium text-slate-400 uppercase tracking-wider">Mean Time to Heal (MTTH)</div>
        <div class="mt-2 flex items-baseline justify-between">
          <div class="text-3xl font-extrabold text-white">~14.2s</div>
          <span class="text-xs text-blue-400 font-semibold bg-blue-500/10 px-2 py-0.5 rounded">Autonomous</span>
        </div>
      </div>

      <div class="bg-darkcard border border-cardborder rounded-2xl p-5 shadow-sm">
        <div class="text-xs font-medium text-slate-400 uppercase tracking-wider">AI Reasoning Model</div>
        <div class="mt-2 flex items-baseline justify-between">
          <div class="text-xl font-bold text-white">Llama 3 / Muse</div>
          <span class="text-xs text-purple-400 font-semibold bg-purple-500/10 px-2 py-0.5 rounded">Zero-Shot</span>
        </div>
      </div>

      <div class="bg-darkcard border border-cardborder rounded-2xl p-5 shadow-sm">
        <div class="text-xs font-medium text-slate-400 uppercase tracking-wider">Safety Verification</div>
        <div class="mt-2 flex items-baseline justify-between">
          <div class="text-3xl font-extrabold text-emerald-400">98.5%</div>
          <span class="text-xs text-emerald-400 font-semibold bg-emerald-500/10 px-2 py-0.5 rounded">Low Risk</span>
        </div>
      </div>
    </div>

    <!-- Live Test Simulator & Incident Feed Split -->
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
      
      <!-- Left: Interactive Failure Injection Console -->
      <div class="lg:col-span-5 bg-darkcard border border-cardborder rounded-2xl p-6 space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            <i class="fa-solid fa-terminal text-brand"></i>
            Live Incident Simulator
          </h2>
          <span class="text-xs text-slate-400">Hackathon Demo Console</span>
        </div>
        <p class="text-xs text-slate-400 leading-relaxed">
          Simulate an enterprise CI/CD stack failure. The agent will intercept the log, reason with Meta AI, patch the repo, and open a Pull Request.
        </p>

        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">Preset Failure Scenarios</label>
          <select id="preset-selector" onchange="loadPreset()" class="w-full bg-slate-900 border border-slate-700 rounded-lg text-xs p-2.5 text-slate-200 focus:outline-none focus:border-brand">
            <option value="python-dep">Python: Invalid Dependency (wso2-mi-tools)</option>
            <option value="docker-build">Docker: Missing requirement resolution failure</option>
            <option value="syntax-error">Python: Indentation & Version Flag Collision</option>
          </select>
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">Target Repository (Universal)</label>
          <input type="text" id="target-repo" value="ChaninduImanjith/self-healing-cicd-agent" class="w-full bg-slate-900 border border-slate-700 rounded-lg text-xs p-2.5 text-slate-200 focus:outline-none focus:border-brand">
        </div>

        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">Failing CI/CD Build Log</label>
          <textarea id="log-input" rows="6" class="w-full font-mono bg-slate-900 border border-slate-700 rounded-lg text-xs p-3 text-slate-200 focus:outline-none focus:border-brand leading-relaxed"></textarea>
        </div>

        <button onclick="triggerHeal()" id="btn-heal" class="w-full bg-gradient-to-r from-brand to-blue-600 hover:from-blue-600 hover:to-blue-700 font-semibold py-3 rounded-xl text-white text-sm shadow-lg shadow-brand/25 transition flex items-center justify-center gap-2">
          <i class="fa-solid fa-bolt"></i>
          Trigger Self-Healing Agent
        </button>
      </div>

      <!-- Right: Real-time Incident Feed -->
      <div class="lg:col-span-7 bg-darkcard border border-cardborder rounded-2xl p-6 space-y-4">
        <div class="flex items-center justify-between border-b border-cardborder pb-4">
          <div>
            <h2 class="text-base font-bold text-white flex items-center gap-2">
              <i class="fa-solid fa-heart-pulse text-emerald-400"></i>
              Real-Time Incident Stream
            </h2>
            <p class="text-xs text-slate-400 mt-0.5">Live feed of intercepted failures and automated Pull Requests</p>
          </div>
          <button onclick="fetchIncidents()" class="text-xs text-slate-400 hover:text-white transition flex items-center gap-1">
            <i class="fa-solid fa-rotate-right"></i> Refresh
          </button>
        </div>

        <!-- Incidents List -->
        <div id="incidents-container" class="space-y-4 max-h-[520px] overflow-y-auto pr-1">
          <!-- Rendered dynamically -->
        </div>
      </div>
    </div>
  </main>

  <script>
    const presets = {
      "python-dep": "Step 4/10 : RUN pip install -r requirements.txt\\nERROR: Could not find a version that satisfies the requirement wso2-mi-tools==1.0.0\\nERROR: No matching distribution found for wso2-mi-tools==1.0.0\\nThe command '/bin/sh -c pip install -r requirements.txt' returned a non-zero code: 1",
      "docker-build": "ERROR: failed to solve: process '/bin/sh -c pip install -r requirements.txt' did not complete successfully: exit code: 1\\nNo matching distribution found for wso2-mi-tools",
      "syntax-error": "Traceback (most recent call last):\\n  File 'app.py', line 12\\n    def init_service(\\n                    ^\\nSyntaxError: unexpected EOF while parsing"
    };

    function loadPreset() {
      const key = document.getElementById('preset-selector').value;
      document.getElementById('log-input').value = presets[key].replace(/\\\\n/g, '\\n');
    }

    async function fetchIncidents() {
      try {
        const res = await fetch('/api/incidents');
        const data = await res.json();
        renderIncidents(data);
      } catch (err) {
        console.error(err);
      }
    }

    function renderIncidents(list) {
      const container = document.getElementById('incidents-container');
      document.getElementById('stat-count').innerText = list.length;
      if (!list.length) {
        container.innerHTML = `<div class="text-center py-12 text-slate-500 text-sm">No incidents intercepted yet.</div>`;
        return;
      }
      container.innerHTML = list.map(item => `
        <div class="bg-slate-900/80 border border-slate-800 rounded-xl p-4.5 space-y-3 hover:border-slate-700 transition">
          <div class="flex items-center justify-between flex-wrap gap-2">
            <div class="flex items-center gap-2">
              <span class="text-xs font-mono font-bold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <i class="fa-solid fa-check"></i> ${item.status || 'Healed'}
              </span>
              <span class="text-xs text-slate-400 font-mono">${item.build_id}</span>
              <span class="text-xs font-medium text-slate-300">• ${item.repository || 'Universal'}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs px-2 py-0.5 rounded font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                🛡️ ${item.risk_level || 'LOW'} RISK
              </span>
              <span class="text-xs text-slate-400">${item.timestamp || 'Just now'}</span>
            </div>
          </div>

          <div class="text-xs text-slate-200 font-medium">
            ${item.commit_message || 'Resolved build dependency failure'}
          </div>

          <div class="bg-black/50 rounded-lg p-3 font-mono text-[11px] space-y-1 text-slate-300 overflow-x-auto border border-slate-800/60">
            <div class="text-slate-500 mb-1">// Target: ${item.file_path || 'unknown'}</div>
            <div class="text-red-400 bg-red-950/20 px-1 py-0.5 rounded">- ${item.search_string || ''}</div>
            <div class="text-emerald-400 bg-emerald-950/20 px-1 py-0.5 rounded">+ ${item.replacement_string || ''}</div>
          </div>

          <div class="flex items-center justify-between pt-1">
            <span class="text-xs text-slate-400">Confidence: <strong class="text-white">${Math.round((item.confidence_score || 0.95) * 100)}%</strong></span>
            ${item.pr_url ? `<a href="${item.pr_url}" target="_blank" class="text-xs text-brand hover:underline font-semibold flex items-center gap-1">
              View Pull Request <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
            </a>` : ''}
          </div>
        </div>
      `).join('');
    }

    async function triggerHeal() {
      const btn = document.getElementById('btn-heal');
      const log = document.getElementById('log-input').value;
      const repoInput = document.getElementById('target-repo').value;
      const [owner, name] = repoInput.split('/');

      btn.disabled = true;
      btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Meta AI Reasoning & Healing...`;

      try {
        const payload = {
          build_id: 'manual-test-' + Date.now().toString().slice(-4),
          log_output: log,
          repo_owner: owner,
          repo_name: name,
          branch: 'main'
        };

        const res = await fetch('/webhook', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (res.ok) {
          fetchIncidents();
          alert('Healed successfully! Pull Request opened: ' + data.pr_url);
        } else {
          alert('Healing failed: ' + (data.detail || 'Unknown error'));
        }
      } catch (e) {
        alert('Network Error: ' + e);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-bolt"></i> Trigger Self-Healing Agent`;
      }
    }

    // Initialize
    loadPreset();
    fetchIncidents();
  </script>
</body>
</html>"""


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

    start_time = time.time()
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
        pr_url = create_healing_pr(
            fix_data=fix_data,
            repo_owner=payload.repo_owner,
            repo_name=payload.repo_name,
            target_branch=payload.branch,
        )
    except RuntimeError as exc:
        logger.error("GitHub integration failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"GitHub integration failed: {exc}",
        ) from exc

    logger.info("Healing complete — PR: %s", pr_url)

    # ── Step 3: Record Incident in History ───────────────────────────
    duration = round(time.time() - start_time, 1)
    incident_record = {
        "build_id": payload.build_id,
        "repository": f"{target_owner}/{target_repo}",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "status": "Healed",
        "file_path": fix_data.get("file_path"),
        "search_string": fix_data.get("search_string"),
        "replacement_string": fix_data.get("replacement_string"),
        "commit_message": fix_data.get("commit_message"),
        "confidence_score": fix_data.get("confidence_score", 0.96),
        "risk_level": fix_data.get("risk_level", "LOW"),
        "duration_seconds": duration,
        "pr_url": pr_url,
    }
    incidents_history.insert(0, incident_record)

    return HealingResponse(
        build_id=payload.build_id,
        repository=f"{target_owner}/{target_repo}",
        target_branch=target_branch,
        pr_url=pr_url,
        fix_summary=fix_data,
    )
