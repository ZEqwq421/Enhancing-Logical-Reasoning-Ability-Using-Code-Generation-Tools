from datasets import load_dataset
from constraint import Problem
import ast
import json

DATASET_NAME = "K-and-K/perturbed-knights-and-knaves"

def is_seq(x):
    return isinstance(x, (list, tuple))


def parse_statements(st):
    if is_seq(st):
    #如果st是list或者tuple则直接输出
        return st

    if isinstance(st, str):
        s = st.strip()
        try:
            obj = ast.literal_eval(s)
            return obj
        except Exception:
            pass
        try:
            obj = json.loads(s)
            return obj
        except Exception:
            pass
        #把一些非常类似于list或者tuple的数据转化为list或者tuple

    raise ValueError(f"Unsupported statements type/value: {type(st)} {st!r}")


def eval_expr(expr, A):
    """
    判断在某一个假设A(假设某人是/不是Knight)
    :param expr: 一个逻辑表达式,是一个list或者tuple
    :param A: 一个list,代表在某一假设下,每个人当前的身份
    e.g.Bob is lying and if I'm telling the truth,then Bob is telling the truth.
    expr = [
        "and",
        ["lying", 1],
        [
            "=>",
            ["telling-truth", 0],
            ["telling-truth", 1]
        ]
    ]
    """
    if is_seq(expr) and len(expr) == 2 and isinstance(expr[0], str):
        op, i = expr
        if op == "telling-truth":
            return A[i] == 1
        if op == "lying":
            return A[i] == 0

    if is_seq(expr) and len(expr) == 2 and expr[0] in ("not", "!"):
        return not eval_expr(expr[1], A)

    if is_seq(expr) and len(expr) == 3 and isinstance(expr[0], str):
        op, lhs, rhs = expr
        if op in ("and", "&"):
            return eval_expr(lhs, A) and eval_expr(rhs, A)
        if op in ("or", "|"):
            return eval_expr(lhs, A) or eval_expr(rhs, A)
        if op in ("=>", "implies", "->"):
            p = eval_expr(lhs, A)
            q = eval_expr(rhs, A)
            return (not p) or q
        if op in ("<=>", "iff", "<->"):
            p = eval_expr(lhs, A)
            q = eval_expr(rhs, A)
            return p == q

    raise ValueError(f"Unknown expression format/type: {type(expr)} value={expr}")

def solve_one(statements):
    """
    用于检查对每个A,其解的情况
    statements: tuple/list, length = n_people.
      statements[i] is the logical content of what person i says.
    return:
      - list[bool] prediction for each person: True=knight, False=knave
      - status string: 'UNIQUE' | 'MULTI' | 'UNSAT'
    """
    n = len(statements)
    people = list(range(n))#index代表每个人

    problem = Problem()
    # variable domain: 0/1
    problem.addVariables(people, [0, 1])

    # Knights tell truth, knaves lie:
    # (A[i] == 1) <=> eval(statements[i], A)
    for i in people:
        def make_c(i_):
            def _c(*vals):
                A = list(vals)
                speaker_is_knight = (A[i_] == 1)
                stmt_truth = eval_expr(statements[i_], A)
                return speaker_is_knight == stmt_truth
            return _c
        problem.addConstraint(make_c(i), people)

    solutions = []
    for sol in problem.getSolutionIter():
        solutions.append(sol)
        if len(solutions) >= 2:
            break
    if len(solutions) == 0:
        return None, "UNSAT"
    if len(solutions) > 1:
        return None, "MULTI"
    sol = solutions[0]
    pred = [bool(sol[i]) for i in range(n)]  # 1->True(knight), 0->False(knave)
    return pred, "UNIQUE"


def run_split(ds, split_name, max_samples=None):
    """测试程序"""
    data = ds[split_name]
    total = 0
    correct = 0
    fail_unsat = 0
    fail_multi = 0
    fail_error = 0
    mismatch = 0

    for idx, ex in enumerate(data):
        if max_samples is not None and idx >= max_samples:#限制最多测试的样本数量
            break
#        print(f"solving {split_name} #{idx}")    
        total += 1
        try:
            statements = parse_statements(ex["statements"])
            pred, status = solve_one(statements)
            gt = ex["solution"]  # list[bool]
            if status == "UNSAT":
                fail_unsat += 1
                continue
            if status == "MULTI":
                fail_multi += 1
                continue

            # UNIQUE
            if pred == gt:
                correct += 1
            else:
                mismatch += 1

        except Exception as e:
            fail_error += 1
            print("ERROR at split:", split_name, "idx:", idx)
            print("names:", ex.get("names"))
            print("statements(parsed):", statements)
            print("exception:", repr(e))
            raise

    acc = correct / total if total else 0.0
    return {
        "split": split_name,
        "total": total,
        "correct": correct,
        "acc": acc,
        "mismatch": mismatch,
        "unsat": fail_unsat,
        "multi": fail_multi,
        "error": fail_error,
    }

def main():
    ds = load_dataset(DATASET_NAME, "train")
    print("available splits:", list(ds.keys()))

    max_samples = None  # 最大测试的样本数量

    results = []
    for split_name in ds.keys():
        r = run_split(ds, split_name, max_samples=max_samples)
        results.append(r)
        print(
            f"[{r['split']}] acc={r['acc']:.4f} "
            f"(correct={r['correct']}/{r['total']}, mismatch={r['mismatch']}, "
            f"unsat={r['unsat']}, multi={r['multi']}, error={r['error']})"
        )

    # overall (加权)
    total = sum(r["total"] for r in results)
    correct = sum(r["correct"] for r in results)
    overall_acc = correct / total if total else 0.0
    print("=" * 60)
    print(f"OVERALL acc={overall_acc:.4f} (correct={correct}/{total})")

if __name__ == "__main__":
    main()
