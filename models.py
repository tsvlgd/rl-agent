from typing import List, Optional
from openenv.core.env_server import Action, Observation, State

class CodeReviewAction(Action):
    code: str

class CodeReviewObservation(Observation):
    messy_code: str
    feedback: str
    task_type: str
    current_step: int
    max_steps: int

class CodeReviewState(State):
    original_code: str
    current_code: str
    task_difficulty: str
    initial_violations: int
