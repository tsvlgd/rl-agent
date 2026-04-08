---
title: RL Code Review Agent
emoji: 🤖
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
app_port: 8000
---

# AI Code Review Curriculum Environment

## Overview
This environment is a specialized Reinforcement Learning (RL) curriculum designed to evaluate and train agents in automated code review. The curriculum focuses on three distinct pillars of software engineering: PEP8 compliance, security best practices, and algorithmic complexity.

## Action & Observation Space
* **Action Space:** The agent provides a `string` containing the full, corrected Python source code.
* **Observation Space:** * `messy_code`: The current state of the source code requiring review.
    * `feedback`: Detailed strings containing unit test results and verbose Ruff linting errors (e.g., F401, E302).
    * `reward`: A scalar value from 0.0 to 1.0 based on functional correctness and code quality.

## Curriculum Stages
The environment implements a 3-stage progression. Success in a lower stage (Reward $\ge 0.95$) automatically transitions the agent to the next task.

1.  **EASY (Formatting & Cleanup):** Focuses on PEP8 compliance, removing unused imports, and fixing basic syntax.
2.  **MEDIUM (Security):** Focuses on secure coding practices, specifically identifying and fixing vulnerabilities in `subprocess` calls (e.g., `shell=True`).
3.  **HARD (Refactoring):** Focuses on code maintainability and complexity. Agents must flatten deeply nested logic using guard clauses.

## Scoring Logic
The reward is calculated using a weighted average:
$$Total\ Reward = (0.5 \times Functional\ Score) + (0.5 \times Quality\ Score)$$
* **Functional Score:** Percentage of unit tests passed.
* **Quality Score:** Calculated via Ruff static analysis, with penalties applied for each linting violation.

## Baseline Performance
The following log demonstrates the baseline agent (Qwen2.5-Coder-32B-Instruct) successfully navigating the curriculum:

```text
[START] task=curriculum_review env=CodeReviewEnvironment-v1 model=Qwen/Qwen2.5-Coder-32B-Instruct
[STEP] step=1 action=def add(a, b):\n    return a + b\n\nimport os\n# R... reward=0.80 done=false error=null
[STEP] step=2 action=def add(a, b):\n    return a + b\n# Removed unused... reward=0.00 done=false error=null
[STEP] step=3 action=import subprocess\n\n\ndef execute_command(cmd):\n... reward=0.00 done=false error=null
[STEP] step=4 action=def check(x):\n    if x <= 0:\n        return Fals... reward=0.95 done=true error=null
[END] success=true steps=4 score=0.950 rewards=0.80,0.00,0.00,0.95
```

## Local Setup & Deployment
### Prerequisites
* Docker
* Python 3.11+
* uv (Fast Python package manager)

### Build and Run
```bash
# Build the container
docker build -t code-review-env .

# Run the environment
docker run -p 8000:8000 --env-file .env code-review-env
```
