import os
import sys
import subprocess


def install_deps():
    """Install missing dependencies before importing them."""
    try:
        import openai  # noqa: F401
        import openenv  # noqa: F401
        from dotenv import load_dotenv  # noqa: F401
    except ImportError:
        print("[INFO] Installing missing dependencies...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "--upgrade",
            "openai>=2.30.0",
            "openenv-core>=0.2.3",
            "python-dotenv",
        ])


# Install dependencies before any other imports
install_deps()

import asyncio  # noqa: E402
from typing import List, Optional  # noqa: E402

from openai import OpenAI  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from client import CodeReviewEnv  # noqa: E402
from models import CodeReviewAction  # noqa: E402

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
ENV_URL = os.getenv("API_URL", "http://localhost:8000")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-Coder-7B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

SYSTEM_PROMPT = """You are an expert AI Code Reviewer. Fix the code for the given level.

EASY: Fix PEP8, formatting, remove unused imports.
MEDIUM: Secure subprocess calls (remove shell=True).
HARD: Flatten nested logic using guard clauses.

RULES:
- Do NOT change function names or arguments.
- Reply ONLY with raw Python code. No markdown fences.
- Ensure exactly one newline at end of file.
"""

TASK_IDS = ["easy", "medium", "hard"]


def log_start(task: str, env_name: str, model: str) -> None:
    print(f"[START] task={task} env={env_name} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    preview = action.replace("\n", "\\n")[:50] + "..."
    print(
        f"[STEP] step={step} action={preview} reward={reward:.2f} "
        f"done={str(done).lower()} error={error or 'null'}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    reward_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={reward_str}",
        flush=True,
    )


async def run_task(env: CodeReviewEnv, task_id: str, ai_client: Optional[OpenAI]) -> None:
    """Run one full episode for a single task_id and emit the required log lines."""
    log_start(task_id, "rl-code-review-agent", MODEL_NAME)

    result = await env.reset()
    obs = result.observation
    rewards: List[float] = []
    is_success = False

    for step_count in range(1, 11):
        user_prompt = (
            f"LEVEL: {obs.task_type}\n"
            f"FEEDBACK: {obs.feedback}\n"
            f"CURRENT_CODE:\n{obs.messy_code}"
        )

        llm_code = obs.messy_code  # fallback: unchanged code
        if ai_client is not None:
            try:
                response = ai_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.01,
                )
                raw = response.choices[0].message.content or ""
                for fence in ["```python", "```py", "```"]:
                    raw = raw.replace(fence, "")
                llm_code = raw.strip()
            except Exception as e:
                log_step(step_count, "error", 0.0, True, str(e))
                break

        step_res = await env.step(CodeReviewAction(code=llm_code))
        obs = step_res.observation
        reward = step_res.reward
        done = step_res.done
        rewards.append(reward)
        log_step(step_count, llm_code, reward, done, None)

        if reward >= 0.95:
            is_success = True
            break
        if done:
            break

    final_score = rewards[-1] if rewards else 0.0
    log_end(is_success, len(rewards), final_score, rewards)


async def run_inference() -> None:
    ai_client: Optional[OpenAI] = None
    if HF_TOKEN:
        ai_client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    env = CodeReviewEnv(base_url=ENV_URL)

    # KEY FIX: loop per task, each gets its own [START]...[END] block
    for task_id in TASK_IDS:
        await run_task(env, task_id, ai_client)


if __name__ == "__main__":
    asyncio.run(run_inference())
