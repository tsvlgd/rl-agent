import subprocess
import json
import ast
import io
from contextlib import redirect_stdout


def verify_structural_identity(original_code, submitted_code):
    """
    Ensures the agent maintained the function name and argument count.
    This prevents the agent from 'cheating' by writing a different function.
    """
    try:
        orig_tree = ast.parse(original_code)
        sub_tree = ast.parse(submitted_code)

        orig_funcs = [n for n in ast.walk(orig_tree) if isinstance(n, ast.FunctionDef)]
        sub_funcs = [n for n in ast.walk(sub_tree) if isinstance(n, ast.FunctionDef)]

        if not sub_funcs:
            return 0.0, "Missing function definition."

        # Compare the first function defined in the original vs submitted
        orig_func = orig_funcs[0]
        # Find a function with the same name in the submission
        sub_func = next((f for f in sub_funcs if f.name == orig_func.name), None)

        if not sub_func:
            return 0.0, f"Identity Mismatch: Function '{orig_func.name}' not found."

        orig_args = len(orig_func.args.args)
        sub_args = len(sub_func.args.args)

        if orig_args != sub_args:
            return (
                0.0,
                f"Interface Mismatch: Expected {orig_args} arguments, got {sub_args}.",
            )

        return 1.0, "Identity Verified."
    except Exception as e:
        return 0.0, f"AST Error: {str(e)}"


def evaluate_agent_submission(
    code: str, level: str, original_code: str, test_cases: list
) -> tuple[float, str]:
    """
    Calculates a weighted reward:
    - Identity (AST): Multiplier (0 or 1)
    - Functional (Unit Tests): 50%
    - Quality (Ruff Lint/Security/Complexity): 50%
    """
    # 1. Syntax Check
    try:
        ast.parse(code)
    except SyntaxError as e:
        return 0.0, f"Syntax Error: {str(e)}"

    # 2. Identity Check (Mandatory Gatekeeper)
    id_reward, id_feedback = verify_structural_identity(original_code, code)
    if id_reward == 0.0:
        return 0.0, id_feedback

    # 3. Functional Check (50% Weight)
    func_reward = 0.0
    feedback_func = ""
    try:
        # Execute in a restricted scope
        ctx = {"builtins": __builtins__}
        exec(code, ctx)
        # Get the target function name from the original code
        orig_tree = ast.parse(original_code)
        target_name = [
            n.name for n in ast.walk(orig_tree) if isinstance(n, ast.FunctionDef)
        ][0]
        target_func = ctx.get(target_name)

        if not target_func:
            return 0.0, f"Function {target_name} not found after execution."

        passed = 0
        for tc in test_cases:
            # Handle single vs multiple arguments via unpacking
            args = tc["input"] if isinstance(tc["input"], tuple) else (tc["input"],)
            if target_func(*args) == tc["expected"]:
                passed += 1

        func_reward = passed / len(test_cases)
        feedback_func = f"Functional: {passed}/{len(test_cases)} passed."
    except Exception as e:
        func_reward = 0.0
        feedback_func = f"Functional Crash: {str(e)}"

    # 4. Quality Check (50% Weight)
    rule_map = {"easy": "E,W,F", "medium": "S602", "hard": "C901"}
    select_rules = rule_map.get(level, "E")

    cmd = ["ruff", "check", "-", "--select", select_rules, "--output-format", "json"]
    if level == "hard":
        cmd.extend(["--config", "lint.mccabe.max-complexity=3"])

    res = subprocess.run(cmd, input=code, text=True, capture_output=True)

    quality_reward = 1.0
    feedback_quality = "Quality: Clean."

    if res.stdout.strip():
        try:
            violations = json.loads(res.stdout)
            if violations:
                # Extract verbose error messages for the agent to read
                issue_details = [
                    f"{v['code']} ({v['message']}) at line {v['location']['row']}"
                    for v in violations
                ]
                feedback_quality = f"Quality Issues: {' | '.join(issue_details)}"

                # Strict penalty: If it's a security task, any violation = 0 quality reward
                if level == "medium":
                    quality_reward = 0.0
                else:
                    quality_reward = max(0.0, 1.0 - (len(violations) * 0.1))
        except:
            quality_reward = 0.0
            feedback_quality = "Ruff Output Parsing Error."
    elif res.returncode != 0:
        quality_reward = 0.0
        feedback_quality = f"Ruff Execution Error: {res.stderr.strip()}"

    total_reward = ((0.5 * func_reward) + (0.5 * quality_reward)) * id_reward
    strictly_between_0_1 = 0.01 + (total_reward * 0.98)

    combined_feedback = f"{id_feedback} | {feedback_func} | {feedback_quality}"
    return float(strictly_between_0_1), combined_feedback
