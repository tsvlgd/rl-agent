import uuid
from openenv.core.env_server import Environment
from models import CodeReviewAction, CodeReviewObservation, CodeReviewState
from graders import evaluate_agent_submission
from tasks.task_registry import TASKS


class CodeReviewEnvironment(Environment):
    MAX_STEPS = 10

    def __init__(self):
        self._state = None
        self._task_list = ["easy", "medium", "hard"]
        self._current_task_idx = 0

    def reset(self, seed=None, episode_id=None, **kwargs) -> CodeReviewObservation:
        self._current_task_idx = 0
        difficulty = self._task_list[self._current_task_idx]
        task_data = TASKS[difficulty]

        self._state = CodeReviewState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            original_code=task_data["code"],
            current_code=task_data["code"],
            task_difficulty=difficulty,
            initial_violations=10,
        )

        return CodeReviewObservation(
            done=False,
            reward=0.0,
            messy_code=self._state.current_code,
            feedback=f"Task started: {task_data['desc']}",
            task_type=difficulty,
            current_step=0,
            max_steps=self.MAX_STEPS,
        )

    def step(self, action: CodeReviewAction) -> CodeReviewObservation:
        if self._state.step_count >= self.MAX_STEPS:
            return CodeReviewObservation(
                done=True,
                reward=0.0,
                messy_code=self._state.current_code,
                feedback="Max steps reached.",
                task_type=self._state.task_difficulty,
                current_step=self._state.step_count,
                max_steps=self.MAX_STEPS,
            )

        self._state.step_count += 1

        # 1. Evaluate the SUBMITTED code
        reward, feedback = evaluate_agent_submission(
            code=action.code,
            level=self._state.task_difficulty,
            original_code=self._state.original_code,
            test_cases=TASKS[self._state.task_difficulty]["test_cases"],
        )

        task_success = reward > 0.8
        is_last_task = self._current_task_idx == len(self._task_list) - 1

        if task_success and not is_last_task:
            self._current_task_idx += 1
            difficulty = self._task_list[self._current_task_idx]
            new_task = TASKS[difficulty]

            # Sync state with new task
            self._state.task_difficulty = difficulty
            self._state.original_code = new_task["code"]
            self._state.current_code = new_task["code"]

            feedback = f"✅ Success! Moving to {difficulty}: {new_task['desc']}"
            done = False
        else:
            self._state.current_code = action.code
            out_of_steps = self._state.step_count >= self.MAX_STEPS
            all_tasks_done = task_success and is_last_task
            done = all_tasks_done or out_of_steps

        return CodeReviewObservation(
            done=done,
            reward=reward,
            messy_code=self._state.current_code,
            feedback=feedback,
            task_type=self._state.task_difficulty,
            current_step=self._state.step_count,
            max_steps=self.MAX_STEPS,  
        )

    @property
    def state(self) -> CodeReviewState:
        return self._state
