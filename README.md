# 🛡️ Self-Healing CI/CD Pipeline Agent

> An autonomous AI agent that intercepts failing CI/CD builds, diagnoses root causes using Meta Llama 3, and opens GitHub Pull Requests with the fix — zero human intervention required.

[![Meta Llama 3](https://img.shields.io/badge/AI-Meta%20Llama%203%2070B-blue?style=flat-square)](https://ai.meta.com/)
[![FastAPI](https://img.shields.io/badge/Server-FastAPI-009688?style=flat-square)](https://fastapi.tiangolo.com/)
[![GitHub API](https://img.shields.io/badge/Integration-GitHub%20API-181717?style=flat-square)](https://docs.github.com/en/rest)

---

## The Problem

CI/CD pipelines break constantly — dependency version conflicts, Docker misconfigurations, missing environment variables, syntax regressions. Engineers spend hours reading stack traces, identifying root causes, switching branches, and pushing fixes. In enterprise environments with Docker, WSO2, Kubernetes, and Terraform, this cycle is expensive and slow.

## The Solution

This agent **closes the loop** automatically:

```
CI/CD Failure → Webhook → Meta Llama 3 Analysis → GitHub PR → Human Review → Merge
```

It doesn't replace engineers — it gives them a head start by arriving at the PR review step with a proposed fix already written, committed, and ready for one-click merge.

## Architecture

```
┌─────────────────────┐
│   CI/CD Platform     │   GitHub Actions, Jenkins, GitLab CI, etc.
│   (Build Fails)      │
└────────┬────────────┘
         │  POST /webhook
         ▼
┌─────────────────────┐
│   main.py            │   FastAPI webhook server
│   (Orchestrator)     │   Validates payload, coordinates modules
└────────┬────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────────────┐
│meta_llm│ │github_integration│
│  .py   │ │      .py         │
└────┬───┘ └────────┬─────────┘
     │              │
     ▼              ▼
  Meta Llama     GitHub API
  3 70B-Instruct  (PyGithub)
     │              │
     │  Structured  │  Branch → Commit → PR
     │  JSON Fix    │
     └──────────────┘
```

### Module Breakdown

| Module | Responsibility |
|---|---|
| **`main.py`** | FastAPI server with `/webhook` endpoint. Receives `build_id` + `log_output`, orchestrates the healing pipeline, returns the PR URL. |
| **`meta_llm.py`** | Sends the raw build log to Meta Llama 3 70B-Instruct with a strict system prompt that forces JSON-only output (`file_path`, `search_string`, `replacement_string`, `commit_message`). |
| **`github_integration.py`** | Authenticates via PyGithub, creates a timestamped `auto-fix/run-*` branch, applies the search-and-replace fix, and opens a Pull Request with a detailed diff description. |

## Why This Isn't Another "AI Wrapper"

Most AI hackathon projects fall into the trap of being a thin UI over an LLM chat endpoint. This project is different because:

1. **It operates autonomously** — no human types a prompt. A CI/CD webhook triggers the entire pipeline.
2. **It produces real artifacts** — not chat text, but an actual Git branch, commit, and Pull Request with a clean diff.
3. **It's constrained by design** — the LLM is forced into a strict JSON schema. No freeform "here's what I think" responses. Either it produces a machine-parseable fix or the pipeline halts.
4. **It's enterprise-scoped** — the system prompt is tuned for Docker, WSO2, Python, Node, Java/Maven, Terraform, and Kubernetes stack traces.
5. **It respects the human** — every fix goes through a PR review. The agent proposes; the engineer disposes.

## Quick Start

### Prerequisites

- Python 3.10+
- A Meta Model API key (\$150 hackathon credits)
- A GitHub Personal Access Token (with `repo` scope)
- A target GitHub repository to heal

### Installation

```bash
# Clone the project
git clone https://github.com/YOUR_USERNAME/self-healing-cicd-agent.git
cd self-healing-cicd-agent

# Create a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your real keys
```

### Configuration

Edit `.env` with your credentials:

```env
META_API_KEY=your_meta_api_key_here
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_REPO_OWNER=your-username
GITHUB_REPO_NAME=your-target-repo
```

### Running the Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs).

### Triggering a Heal (Demo Command)

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "build_id": "run-48291",
    "log_output": "Step 4/10 : RUN pip install -r requirements.txt\nERROR: Could not find a version that satisfies the requirement wso2-mi-tools==1.0.0\nERROR: No matching distribution found for wso2-mi-tools==1.0.0\nThe command '\''/bin/sh -c pip install -r requirements.txt'\'' returned a non-zero code: 1"
  }'
```

**Expected response:**

```json
{
  "status": "healed",
  "build_id": "run-48291",
  "repository": "your-username/your-repo",
  "target_branch": "main",
  "pr_url": "https://github.com/your-username/your-repo/pull/42",
  "fix_summary": {
    "file_path": "requirements.txt",
    "search_string": "wso2-mi-tools==1.0.0",
    "replacement_string": "wso2-mi-tools>=0.9.0,<2.0.0",
    "commit_message": "Relax wso2-mi-tools version constraint to resolve pip dependency resolution failure"
  }
}
```

## 🌐 Universal Multi-Project Support (Any Repository)

This agent acts as a **centralized self-healing platform** for entire engineering organizations. It is not limited to healing itself—it can autonomously heal **any repository, microservice, or technology stack** (Node.js, Go, Python, Java, Docker, Kubernetes manifests).

To connect any repository, include `repo_owner`, `repo_name`, and optional `branch` in the webhook payload:

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "build_id": "payment-svc-build-812",
    "repo_owner": "YourOrg",
    "repo_name": "payments-microservice",
    "branch": "develop",
    "ci_provider": "github-actions",
    "log_output": "npm ERR! code ENOENT\nnpm ERR! syscall open\nnpm ERR! path /package.json"
  }'
```

The agent will automatically authenticate to `YourOrg/payments-microservice`, branch from `develop`, apply the surgical fix, and open the Pull Request on that target repository!

## Connecting to a Real CI/CD System

### GitHub Actions

Add a workflow step that fires on failure:

```yaml
on:
  workflow_run:
    workflows: ["Build"]
    types: [completed]

jobs:
  self-heal:
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
    runs-on: ubuntu-latest
    steps:
      - name: Fetch failed logs and trigger healing
        run: |
          LOG=$(gh run view ${{ github.event.workflow_run.id }} --log-failed 2>&1 | tail -100)
          curl -X POST https://your-server.com/webhook \
            -H "Content-Type: application/json" \
            -d "{\"build_id\": \"run-${{ github.event.workflow_run.id }}\", \"log_output\": $(echo "$LOG" | jq -Rs .)}"
```

### Jenkins

Use a `post { failure { ... } }` block in your Jenkinsfile to POST the console output to `/webhook`.

## Project Structure

```
self-healing-cicd-agent/
├── .env.example              # Environment variable template
├── .gitignore
├── requirements.txt          # Python dependencies
├── meta_llm.py               # AI reasoning module (Meta Llama 3)
├── github_integration.py     # GitHub auto-healing module (PyGithub)
├── main.py                   # FastAPI webhook server
└── README.md                 # This file
```

## License

MIT — built for the Meta Global AI Developer Hackathon.
