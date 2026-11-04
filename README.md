# 🛡️ Autonomous Self-Healing CI/CD Pipeline Agent

> **Built for the Meta Global AI Developer Hackathon**  
> An autonomous, enterprise-grade DevOps AI agent that intercepts failing CI/CD builds, performs deep root cause analysis using **Meta AI**, surgically applies code fixes to isolated Git branches, and opens production-ready GitHub Pull Requests — **completely autonomous, zero human intervention required.**

[![Meta AI Powered](https://img.shields.io/badge/AI%20Engine-Meta%20Llama%20(muse--spark--1.3)-0064e0?style=for-the-badge&logo=meta&logoColor=white)](https://ai.meta.com/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![GitHub API](https://img.shields.io/badge/Integration-GitHub%20REST%20%2F%20PyGithub-181717?style=for-the-badge&logo=github&logoColor=white)](https://pygithub.readthedocs.io/)
[![Docker](https://img.shields.io/badge/Deployment-Docker%20%26%20Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

---

## 📌 Table of Contents

- [Overview](#-overview)
- [The Problem vs. The Solution](#-the-problem-vs-the-solution)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Incident Assessment & PR Guardrails](#-incident-assessment--pr-guardrails)
- [Multi-Tenant & Universal Repository Support](#-multi-tenant--universal-repository-support)
- [Project Structure](#-project-structure)
- [Quick Start & Local Setup](#-quick-start--local-setup)
- [Running with Docker & Docker Compose](#-running-with-docker--docker-compose)
- [End-to-End Testing & Demo Walkthrough](#-end-to-end-testing--demo-walkthrough)
- [Connecting External CI/CD Pipelines](#-connecting-external-cicd-pipelines)
- [Enterprise Safety & Defense-in-Depth](#-enterprise-safety--defense-in-depth)
- [Contributing & License](#-contributing--license)

---

## 💡 Overview

Modern software engineering teams waste thousands of hours debugging broken CI/CD pipelines. Typical breaks stem from unavailable upstream packages, syntax slips, breaking configuration changes, Dockerfile regressions, or missing environment variables.

The **Self-Healing CI/CD Pipeline Agent** automates this entire remediation lifecycle:
1. **Listens** to real-time build failures via CI/CD webhooks or GitHub Action lifecycle triggers.
2. **Sanitizes** noisy terminal output (removing ANSI color sequences, runner timestamps, runner step prefixes, and post-job cleanup debris).
3. **Reasons** with Meta AI (`muse-spark-1.3` high-context reasoning engine) to deduce the exact root cause and formulate an exact surgical patch.
4. **Applies** the patch onto a freshly branched Git ref and submits a comprehensive Pull Request enriched with an **Incident Assessment**, **Confidence Score**, **Risk Classification**, and **Root Cause Explanation**.

Engineers arrive directly at the review step with an actionable PR waiting for one-click approval.

---

## ⚖️ The Problem vs. The Solution

| Traditional Incident Response | Autonomous Self-Healing Pipeline |
|---|---|
| 🔴 Build fails; engineer gets paged or checks Slack minutes later | 🟢 Intercepted in milliseconds via automated webhook trigger |
| 🔴 Developer sifts through 500+ lines of raw console logs | 🟢 Log sanitized and parsed down to the fatal error context |
| 🔴 Manual reproduction, local branch checkout, commit & push | 🟢 Meta AI deduces exact file, line, and replacement string |
| 🔴 High developer context-switching and pipeline downtime | 🟢 Automated branch created & structured Pull Request opened in ~15-20s |
| 🔴 Prone to hasty fixes and skipped review standards | 🟢 Guardrails: Confidence score, risk level, diff, human-in-the-loop merge |

---

## ✨ Key Features

- **🧠 Meta AI Reasoning (`muse-spark-1.3`)**: Employs deep chain-of-thought analysis to accurately isolate compiler, dependency, syntax, and container errors.
- **⚡ Asynchronous Non-Blocking Webhook Architecture**: FastAPI webhook acknowledges incoming payloads immediately (HTTP 200) to prevent upstream gateway timeouts (e.g. Cloudflare, AWS ALB), offloading AI reasoning and Git operations to background tasks.
- **🌐 Universal Multi-Tenant Capability**: Can monitor and heal **any repository across an entire GitHub organization** dynamically without hardcoding repository names or branch constraints.
- **🛡️ 4-Layer Defense-in-Depth Guardrails**:
  - Log sanitizer strips runner metadata prefixes (`<Job>\t<Step>\t<Timestamp>`) and post-job git cleanup noise.
  - LLM schema validation strictly enforces JSON output without Markdown clutter.
  - Dependency failover engine guarantees package index errors correctly update `requirements.txt` rather than corrupting CI workflows.
  - Partial line matching ensures version differences or trailing comments don't break string replacements.
- **📊 Enterprise Incident Assessment**: Every Pull Request includes a machine-evaluated confidence score, risk classification (🟢 LOW / 🟡 MEDIUM / 🔴 HIGH), root cause explanation, and unified diff preview.
- **✍️ Professional Git Commits**: Enforces clean, imperative, enterprise-standard commit messages (without conventional commit prefixes).

---

## 🏛️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           GitHub Actions / External CI                          │
│                                                                                 │
│   ┌────────────────────────┐                    ┌───────────────────────────┐   │
│   │ Continuous Integration │ ──( On Failure )─► │ Self-Heal Trigger Action  │   │
│   │   (Build / Test Step)  │                    │   (Pulls Failed Logs)     │   │
│   └────────────────────────┘                    └─────────────┬─────────────┘   │
└───────────────────────────────────────────────────────────────┼─────────────────┘
                                                                │ POST /webhook
                                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      Self-Healing CI/CD Agent Server                            │
│                                                                                 │
│   ┌───────────────────────────┐                                                 │
│   │      FastAPI Server       │ ──► [ HTTP 200 Acknowledged Immediately ]       │
│   │       (`main.py`)         │                                                 │
│   └─────────────┬─────────────┘                                                 │
│                 │ Background Task                                               │
│                 ▼                                                               │
│   ┌───────────────────────────┐         Raw Log          ┌──────────────────┐   │
│   │     AI Reasoning Engine   │ ───────────────────────► │ Meta AI Endpoint │   │
│   │      (`meta_llm.py`)      │ ◄─────────────────────── │ (muse-spark-1.3) │   │
│   └─────────────┬─────────────┘       Structured JSON    └──────────────────┘   │
│                 │                     (Fix Proposal)                            │
│                 ▼                                                               │
│   ┌───────────────────────────┐                                                 │
│   │   Git Automation Engine   │ ──► 1. Create `auto-fix/run-<timestamp>` branch │
│   │ (`github_integration.py`) │ ──► 2. Apply surgical file update               │
│   └─────────────┬─────────────┘ ──► 3. Open Pull Request with Incident Report   │
└─────────────────┼───────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              GitHub Repository                                  │
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  🚀 New Pull Request: "Remove unavailable dependency from requirements" │   │
│   │  • Confidence: 95%   • Risk: LOW 🟢   • Base: main                      │   │
│   │  • Human Reviewer clicks "Merge pull request"                           │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Incident Assessment & PR Guardrails

Every Pull Request generated by the agent features a structured incident briefing:

```markdown
## 🛡️ Autonomous Self-Healing Report

This pull request was automatically generated by the **Self-Healing CI/CD Pipeline Agent** powered by **Meta AI**.

### 📊 Incident Assessment
| Metric | Assessment |
|---|---|
| **Target File** | `requirements.txt` |
| **Confidence Score** | **95%** |
| **Risk Level** | **🟢 LOW** |
| **Target Branch** | `main` |

### 🔍 Root Cause Analysis
> Package wso2-mi-tools==1.0.0 could not be resolved from PyPI during pip installation. Commenting out the missing dependency allows the CI build pipeline to install all available packages cleanly.

### 📝 Code Diff
```diff
- wso2-mi-tools==1.0.0
+ # wso2-mi-tools==1.0.0 removed: dependency unavailable on PyPI
```

### 🔒 Safety Guardrails
- [x] Verified zero semantic breaking changes
- [x] Validated JSON patch integrity
- [x] Human-in-the-loop review ready
```

---

## 🌐 Multi-Tenant & Universal Repository Support

The agent acts as a **centralized self-healing hub** across multiple microservices and repositories. It does not require code changes inside the agent to service different repositories.

Simply pass the target coordinates in the webhook payload:

```json
{
  "build_id": "gh-run-418123982",
  "log_output": "npm ERR! 404 Not Found - GET https://registry.npmjs.org/@internal/legacy-core",
  "repo_owner": "AcmeCorp",
  "repo_name": "checkout-service",
  "branch": "main",
  "ci_provider": "github-actions"
}
```

The agent will:
1. Dynamically connect to `AcmeCorp/checkout-service`.
2. Inspect the remote target branch (`main`).
3. Branch to `auto-fix/run-<timestamp>`.
4. Apply the fix and open the Pull Request on the target repository.

---

## 📁 Project Structure

```
self-healing-cicd-agent/
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Main CI workflow (syntax, build, imports)
│       └── self-heal-trigger.yml      # Automatic failure interceptor & webhook dispatcher
├── main.py                            # FastAPI webhook server & asynchronous task orchestrator
├── meta_llm.py                        # Meta AI client (muse-spark-1.3) & log sanitization engine
├── github_integration.py              # PyGithub automation (branching, file commit, PR generation)
├── requirements.txt                   # Production Python dependencies
├── Dockerfile                         # Production-ready multi-stage Python 3.12 container
├── docker-compose.yml                 # Local container orchestration
├── .env.example                       # Environment variable template
├── .gitignore                         # Git exclusion rules
└── README.md                          # Comprehensive project documentation
```

---

## 🚀 Quick Start & Local Setup

### 1. Prerequisites
- **Python 3.10+** (tested on Python 3.12 and 3.14)
- **Meta Model API Key** (Meta Llama API access)
- **GitHub Personal Access Token** with `repo` permissions

### 2. Clone and Install

```bash
git clone https://github.com/ChaninduImanjith/self-healing-cicd-agent.git
cd self-healing-cicd-agent

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure Environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```ini
# Meta AI API Configuration
META_API_KEY=LLM_xxxxxxxxxxxxxxxxxxxxxx

# GitHub API Configuration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_REPO_OWNER=ChaninduImanjith
GITHUB_REPO_NAME=self-healing-cicd-agent
```

### 4. Start the Agent Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The server starts at `http://localhost:8000`. You can explore interactive Swagger documentation at `http://localhost:8000/docs`.

---

## 🐳 Running with Docker & Docker Compose

### Using Docker Compose (Recommended)

```bash
# Build and run in detached mode
docker compose up -d --build

# View real-time agent logs
docker compose logs -f

# Verify container health
docker compose ps
```

### Using Plain Docker

```bash
# Build image
docker build -t self-healing-cicd-agent .

# Run container with environment file
docker run -d \
  --name self-healing-agent \
  -p 8000:8000 \
  --env-file .env \
  self-healing-cicd-agent
```

---

## 🧪 End-to-End Testing & Demo Walkthrough

### Scenario: Broken Dependency Self-Healing

You can reproduce an autonomous end-to-end self-healing event in under 3 minutes:

#### Step 1: Inject a Breaking Dependency
Add a nonexistent package into `requirements.txt`:
```bash
echo "wso2-mi-tools==1.0.0" >> requirements.txt
git commit -am "Add enterprise middleware dependency to requirements"
git push origin main
```

#### Step 2: GitHub Actions Fails (Red Build)
- The `Continuous Integration` workflow runs `pip install -r requirements.txt`.
- Pip fails with: `ERROR: No matching distribution found for wso2-mi-tools==1.0.0`.
- The build exits with a non-zero exit code.

#### Step 3: Self-Healing Trigger Intercepts
- `.github/workflows/self-heal-trigger.yml` detects the failed run.
- It pulls failed logs using `gh run view --log-failed`, strips runner noise, and dispatches the payload to the agent's `/webhook` URL.

#### Step 4: Autonomous Pull Request Generated (Green Recovery)
- In ~15 seconds, the agent creates branch `auto-fix/run-<timestamp>`.
- A Pull Request is opened with the exact diff removing the broken dependency.
- Once merged, the `Continuous Integration` workflow triggers and turns **GREEN** 🟢.

---

### Manual Testing with cURL

You can also test the agent directly from the terminal without breaking your repo:

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "build_id": "manual-test-001",
    "log_output": "Step 4/10 : RUN pip install -r requirements.txt\nERROR: Could not find a version that satisfies the requirement wso2-mi-tools==1.0.0\nERROR: No matching distribution found for wso2-mi-tools==1.0.0\nThe command '\''/bin/sh -c pip install -r requirements.txt'\'' returned a non-zero code: 1",
    "repo_owner": "ChaninduImanjith",
    "repo_name": "self-healing-cicd-agent",
    "branch": "main",
    "ci_provider": "manual-test"
  }'
```

---

## 🔗 Connecting External CI/CD Pipelines

To connect this agent to any external CI/CD tool (Jenkins, GitLab CI, CircleCI, Bitbucket):

### GitHub Actions (Other Repositories)
Add the trigger step to your repository's workflow:

```yaml
name: Self-Healing Trigger
on:
  workflow_run:
    workflows: ["Continuous Integration"]
    types: [completed]

jobs:
  heal:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    steps:
      - name: Send Failed Log to Agent
        run: |
          LOG=$(gh run view ${{ github.event.workflow_run.id }} --log-failed 2>&1 | tail -n 80)
          jq -n \
            --arg build_id "gh-${{ github.event.workflow_run.id }}" \
            --arg log_output "$LOG" \
            --arg repo_owner "${{ github.repository_owner }}" \
            --arg repo_name "${{ github.event.repository.name }}" \
            --arg branch "${{ github.ref_name }}" \
            '{build_id: $build_id, log_output: $log_output, repo_owner: $repo_owner, repo_name: $repo_name, branch: $branch}' > payload.json
          
          curl -X POST "${{ secrets.HEALING_AGENT_WEBHOOK_URL }}" \
            -H "Content-Type: application/json" \
            -d @payload.json
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Exposing Local Agent with Cloudflare Tunnel
For local development or testing with GitHub Actions:

```bash
# Install cloudflared
# Expose port 8000 to a public HTTPS endpoint
cloudflared tunnel --url http://localhost:8000
```
Copy the generated `https://<random-subdomain>.trycloudflare.com` URL and set it as the `HEALING_AGENT_WEBHOOK_URL` secret in GitHub.

---

## 🛡️ Enterprise Safety & Defense-in-Depth

The agent incorporates four core layers of guardrails to prevent harmful, recursive, or invalid fixes:

1. **Deterministic String Patching**: The agent uses targeted string replacement rather than full-file overwrites, preventing unintentional deletion of unrelated code or comments.
2. **Failover Safeguard**: If Meta AI suggests patching a CI workflow YAML file in response to a dependency resolution error, the agent automatically detects the anomaly and safely redirects the patch to `requirements.txt`.
3. **No Direct Main Commits**: The agent never commits to protected production branches. All mutations are committed to an isolated `auto-fix/run-*` branch and submitted through a standard Pull Request.
4. **Human-in-the-Loop Verification**: Teams retain complete authority. Pull Requests require standard team reviews or automated branch-protection signoffs before merging into `main`.

---

## 📜 Contributing & License

Contributions are welcome! Please open an issue or submit a Pull Request.

Distributed under the **MIT License**. See `LICENSE` for more information.

---

<p align="center">
  <b>Built with ❤️ for the Meta Global AI Developer Hackathon</b>
</p>
