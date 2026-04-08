# tasks/task_registry.py
TASKS = {
    "easy": {
        "code": "def add(a,b):\n    return a+b\nimport os",
        "test_cases": [
            {"input": (2, 3), "expected": 5},
            {"input": (-1, 1), "expected": 0},
        ],
        "rules": "E,W,F",
        "desc": "Fix PEP8 formatting and remove unused imports.",
    },
    "medium": {
        "code": "import subprocess\ndef execute_command(cmd):\n    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout",
        "test_cases": [{"input": (["echo", "hello"],), "expected": "hello\n"}],
        "rules": "S",
        "desc": "Secure the subprocess call by removing shell=True.",
    },
    "hard": {
        "code": "def check(x):\n    if x > 0:\n        if x < 10:\n            if x % 2 == 0:\n                return True\n    return False",
        "test_cases": [
            {"input": (4,), "expected": True},
            {"input": (11,), "expected": False},
        ],
        "rules": "C901",
        "desc": "Refactor nested logic using guard clauses.",
    },
}
