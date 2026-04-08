import asyncio
import os
import textwrap
from typing import List, Optional
from openai import OpenAI
from client import CodeReviewEnv
from models import CodeReviewAction
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
ENV_URL = os.getenv("API_URL", "http://localhost:8000")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-ai/deepseek-coder-33b-instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

ai_client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
env = CodeReviewEnv(base_url=ENV_URL)

SYSTEM_PROMPT = """You are an expert AI Code Reviewer. You must solve a 3-level curriculum:
1. EASY: Fix PEP8, formatting, and remove unused imports.
2. MEDIUM: Secure subprocess calls (remove shell=True).
3. HARD: Flatten nested logic using guard clauses.

CRITICAL RULES:
- Read the 'FEEDBACK' carefully. If it mentions a Ruff error code (like E302 or F401), fix it immediately.
- Ensure there is exactly ONE newline at the end of the file.
- Do not change function names or arguments.
- Reply ONLY with the raw Python code. Do not use markdown blocks (no ```python).
"""


def log_start(task: str, env_name: str, model: str):
    print(f"[START] task={task} env={env_name} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]):
    done_str = str(done).lower()
    preview = action.replace("\n", "\\n")[:50] + "..."
    print(
        f"[STEP] step={step} action={preview} reward={reward:.2f} done={done_str} error={error or 'null'}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]):
    reward_path = ",".join([f"{r:.2f}" for r in rewards])
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={reward_path}",
        flush=True,
    )


async def run_inference():
    log_start("curriculum_review", "CodeReviewEnvironment-v1", MODEL_NAME)

    result = await env.reset()
    obs = result.observation

    step_count = 0
    rewards = []
    is_success = False

    while step_count < 10:
        step_count += 1

        user_prompt = f"LEVEL: {obs.task_type}\nFEEDBACK: {obs.feedback}\nCURRENT_CODE:\n{obs.messy_code}"

        try:
            response = ai_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.01,
            )

            llm_code = response.choices[0].message.content.strip()
            for fence in ["```python", "```py", "```"]:
                llm_code = llm_code.replace(fence, "")
            llm_code = llm_code.strip()

            step_res = await env.step(CodeReviewAction(code=llm_code))

            obs = step_res.observation
            reward = step_res.reward
            done = step_res.done

            rewards.append(reward)
            log_step(step_count, llm_code, reward, done, None)

            if reward >= 0.95 and obs.task_type == "hard":
                is_success = True
                break

            if done:
                break

        except Exception as e:
            log_step(step_count, "error", 0.0, True, str(e))
            break

    log_end(is_success, step_count, rewards[-1] if rewards else 0.0, rewards)


if __name__ == "__main__":
    asyncio.run(run_inference())
