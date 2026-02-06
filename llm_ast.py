import json
import re
from typing import Any, Dict, List, Tuple
from deepseek_client import call_llm as deepseek_call

_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)

def safe_parse_json(text: str) -> Dict[str, Any]:
    """
    允许 LLM 输出夹杂少量文本时，仍可提取 JSON。
    """
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = _JSON_RE.search(text)
    if not m:
        raise ValueError("No JSON object found in LLM output.")
    blob = m.group(0)
    return json.loads(blob)

#AST
ALLOWED_ATOMS = {"telling-truth", "lying"}
ALLOWED_UNARY = {"not", "!"}
ALLOWED_BINARY = {"and", "&", "or", "|", "=>", "implies", "->", "<=>", "iff", "<->"}

def _check_expr(expr: Any, n_people: int) -> None:
    """检查是否为正确的逻辑表达式"""
    if not isinstance(expr, list):
        raise ValueError(f"Expr must be list, got {type(expr)}: {expr!r}")
    if len(expr) == 0:
        raise ValueError("Empty expr list.")

    op = expr[0]
    if not isinstance(op, str):
        raise ValueError(f"Expr op must be str, got {type(op)}: {expr!r}")

    # atom: [op, i]
    if op in ALLOWED_ATOMS:
        if len(expr) != 2:
            raise ValueError(f"Atom expr must have 2 items: {expr!r}")
        i = expr[1]
        if not isinstance(i, int):
            raise ValueError(f"Atom index must be int: {expr!r}")
        if not (0 <= i < n_people):
            raise ValueError(f"Atom index out of range: {expr!r}")
        return

    # unary: [op, x]
    if op in ALLOWED_UNARY:
        if len(expr) != 2:
            raise ValueError(f"Unary expr must have 2 items: {expr!r}")
        _check_expr(expr[1], n_people)
        return

    # binary: [op, a, b]
    if op in ALLOWED_BINARY:
        if len(expr) != 3:
            raise ValueError(f"Binary expr must have 3 items: {expr!r}")
        _check_expr(expr[1], n_people)
        _check_expr(expr[2], n_people)
        return

    raise ValueError(f"Unknown op: {op!r} in expr {expr!r}")


def validate_payload(payload: Dict[str, Any]) -> Tuple[List[str], List[Any]]:
    """类型检查"""
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a JSON object.")

    people = payload.get("people")
    statements = payload.get("statements")

    if not isinstance(people, list) or not all(isinstance(x, str) for x in people):
        raise ValueError("'people' must be a list of strings.")
    if len(people) == 0:
        raise ValueError("'people' must be non-empty.")

    if not isinstance(statements, list):
        raise ValueError("'statements' must be a list.")
    if len(statements) != len(people):
        raise ValueError("len(statements) must equal len(people).")

    n = len(people)
    for i, expr in enumerate(statements):
        if not isinstance(expr, list):
            raise ValueError(f"statements[{i}] must be list expr, got {type(expr)}")
        _check_expr(expr, n)

    return people, statements

def build_prompt(quiz_text: str) -> str:
    """Prompt"""
    return f"""
You are a semantic parser. Convert a Knights-and-Knaves puzzle into a constrained JSON AST.

Rules:
- Output MUST be a single JSON object, no markdown, no extra text.
- people: list of names in the order they appear in the puzzle.
- statements[i]: the logical content uttered by people[i], expressed as an AST using ONLY:
    Atoms: ["telling-truth", i], ["lying", i]
    Unary: ["not", expr]
    Binary: ["and", a, b], ["or", a, b], ["=>", a, b], ["<=>", a, b]
- Use indices i based on people list, 0..n-1.
- Do NOT include explanations.
- Do NOT output python code.
- If the puzzle includes quotes, parse them as logical content.
- If someone says multiple sentences, combine with ["and", ...].

Puzzle:
{quiz_text}
""".strip()

def llm_quiz_to_statements(quiz_text: str, max_retries: int = 3) -> Tuple[List[str], List[Any]]:
    """
    返回 (people, statements_ast)
    """
    last_err = None
    for _ in range(max_retries + 1):
        prompt = build_prompt(quiz_text)
        raw, usage = deepseek_call(
            user_text=prompt,
            system_text="You are a semantic parser that outputs strict JSON only.",
            max_tokens=512,
            stream=False,
        )
        try:
            payload = safe_parse_json(raw)
            people, statements = validate_payload(payload)
            return people, statements
        except Exception as e:
            last_err = e
            # retry: 给模型更强的约束（把错误信息反馈回去）
            quiz_text = quiz_text  # no-op
    raise RuntimeError(f"LLM parse failed after retries: {last_err!r}")
