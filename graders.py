import subprocess
import json
import ast

def verify_structural_identity(original_code, submitted_code):
    """
    Returns (raw_multiplier, feedback)
    Multiplier is 1.0 for success, 0.0 for mismatch.
    """
    try:
        orig_tree = ast.parse(original_code)
        sub_tree = ast.parse(submitted_code)

        orig_funcs = [n for n in ast.walk(orig_tree) if isinstance(n, ast.FunctionDef)]
        sub_funcs = [n for n in ast.walk(sub_tree) if isinstance(n, ast.FunctionDef)]

        if not sub_funcs:
            return 0.0, "Missing function definition."

        orig_func = orig_funcs[0]
        sub_func = next((f for f in sub_funcs if f.name == orig_func.name), None)

        if not sub_func:
            return 0.0, f"Identity Mismatch: Function '{orig_func.name}' not found."

        if len(orig_func.args.args) != len(sub_func.args.args):
            return 0.0, "Interface Mismatch: Argument count changed."

        return 1.0, "Identity Verified."
    except Exception as e:
        return 0.0, f"AST Error: {str(e)}"

def evaluate_agent_submission(code: str, level: str, original_code: str, test_cases: list) -> tuple[float, str]:
    id_reward = 0.0
    func_reward = 0.0
    quality_reward = 0.0
    feedback_parts = []

    try:
        ast.parse(code)
        
        id_reward, id_msg = verify_structural_identity(original_code, code)
        feedback_parts.append(id_msg)

        if id_reward > 0.5:
            try:
                ctx = {"builtins": __builtins__}
                exec(code, ctx)
                orig_tree = ast.parse(original_code)
                target_name = [n.name for n in ast.walk(orig_tree) if isinstance(n, ast.FunctionDef)][0]
                target_func = ctx.get(target_name)

                if target_func:
                    passed = 0
                    for tc in test_cases:
                        args = tc["input"] if isinstance(tc["input"], tuple) else (tc["input"],)
                        if target_func(*args) == tc["expected"]:
                            passed += 1
                    func_reward = passed / len(test_cases)
                    feedback_parts.append(f"Functional: {passed}/{len(test_cases)} passed.")
                else:
                    feedback_parts.append(f"Error: Function {target_name} not found.")
            except Exception as e:
                feedback_parts.append(f"Functional Crash: {str(e)}")

            # 5. Quality Check
            rule_map = {"easy": "E,W,F", "medium": "S602", "hard": "C901"}
            select_rules = rule_map.get(level, "E")
            cmd = ["ruff", "check", "-", "--select", select_rules, "--output-format", "json"]
            if level == "hard":
                cmd.extend(["--config", "lint.mccabe.max-complexity=3"])

            res = subprocess.run(cmd, input=code, text=True, capture_output=True)
            if res.returncode == 0 and not res.stdout.strip():
                quality_reward = 1.0
                feedback_parts.append("Quality: Clean.")
            else:
                try:
                    violations = json.loads(res.stdout)
                    quality_reward = 0.0 if level == "medium" else max(0.0, 1.0 - (len(violations) * 0.1))
                    feedback_parts.append(f"Quality: Found {len(violations)} issues.")
                except:
                    quality_reward = 0.0
                    feedback_parts.append("Quality: Analysis failed.")

    except SyntaxError as e:
        feedback_parts.append(f"Syntax Error: {str(e)}")
    except Exception as e:
        feedback_parts.append(f"System Error: {str(e)}")

    raw_total = ((0.5 * func_reward) + (0.5 * quality_reward)) * id_reward

    strictly_between_0_1 = 0.01 + (raw_total * 0.98)

    return float(strictly_between_0_1), " | ".join(feedback_parts)