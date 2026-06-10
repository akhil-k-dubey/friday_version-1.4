"""
skills/calculator.py — Safe math expression evaluator.
"""
from __future__ import annotations

import math
import re
import subprocess


def skill_calculator(args: str) -> str:
    """Safely evaluate a math expression."""
    expr = args.strip()
    if not expr:
        return "No expression to evaluate."

    # Clean up spoken math
    expr = expr.replace("×", "*").replace("÷", "/").replace("^", "**")
    expr = expr.replace("plus", "+").replace("minus", "-")
    expr = expr.replace("times", "*").replace("divided by", "/")
    expr = expr.replace("to the power of", "**")
    expr = expr.replace("mod", "%").replace("modulo", "%")

    # Allow only safe characters
    safe_pattern = re.compile(r'^[\d\s\+\-\*\/\.\(\)\%\,]+$')
    # Also allow math function names
    func_pattern = re.compile(r'\b(sqrt|sin|cos|tan|log|log2|log10|abs|pow|round|pi|e)\b')

    clean = func_pattern.sub('', expr)
    if not safe_pattern.match(clean.replace(' ', '').replace(',', '')):
        return f"I cannot safely evaluate: {expr}"

    # Replace math functions with math module calls
    expr = re.sub(r'\bsqrt\b', 'math.sqrt', expr)
    expr = re.sub(r'\bsin\b', 'math.sin', expr)
    expr = re.sub(r'\bcos\b', 'math.cos', expr)
    expr = re.sub(r'\btan\b', 'math.tan', expr)
    expr = re.sub(r'\blog10\b', 'math.log10', expr)
    expr = re.sub(r'\blog2\b', 'math.log2', expr)
    expr = re.sub(r'\blog\b', 'math.log', expr)
    expr = re.sub(r'\bpi\b', 'math.pi', expr)
    expr = re.sub(r'\be\b', 'math.e', expr)
    expr = re.sub(r'\babs\b', 'abs', expr)
    expr = re.sub(r'\bround\b', 'round', expr)

    try:
        result = eval(expr, {"__builtins__": {}, "math": math, "abs": abs, "round": round, "pow": pow})
        # Format nicely
        if isinstance(result, float):
            if result == int(result):
                ans = str(int(result))
            else:
                ans = f"{result:.6g}"
        else:
            ans = str(result)

        # Copy answer to clipboard
        try:
            import pyperclip
            pyperclip.copy(ans)
        except Exception:
            try:
                escaped = ans.replace("'", "''")
                subprocess.run(
                    ["powershell", "-Command", f"Set-Clipboard '{escaped}'"],
                    timeout=3,
                )
            except Exception:
                pass

        return f"The answer is {ans}."
    except Exception as exc:
        return f"Could not calculate: {exc}"
