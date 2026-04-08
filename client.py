from openenv.core.env_client import EnvClient
from openenv.core.client_types import StepResult
from models import CodeReviewAction, CodeReviewObservation, CodeReviewState


class CodeReviewEnv(
    EnvClient[CodeReviewAction, CodeReviewObservation, CodeReviewState]
):
    def _step_payload(self, action: CodeReviewAction) -> dict:
        return {"code": action.code}

    def _parse_result(self, payload: dict) -> StepResult:
        obs_data = payload.get("observation", {})
        observation = CodeReviewObservation(
            done=payload.get("done", False),
            reward=payload.get("reward", 0.0),
            messy_code=obs_data.get("messy_code", ""),
            feedback=obs_data.get("feedback", ""),
            task_type=obs_data.get("task_type", "easy"),
            current_step=obs_data.get("current_step", 0),
            max_steps=obs_data.get("max_steps", 5),
        )
        return StepResult(
            observation=observation,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> CodeReviewState:
        return CodeReviewState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            original_code=payload.get("original_code", ""),
            current_code=payload.get("current_code", ""),
            task_difficulty=payload.get("task_difficulty", "easy"),
            initial_violations=payload.get("initial_violations", 10),
        )
