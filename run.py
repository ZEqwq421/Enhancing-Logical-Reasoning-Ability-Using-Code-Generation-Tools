import ast
from datasets import load_dataset
from llm_ast import llm_quiz_to_statements
from csp_oracle import solve_one, eval_expr

DATASET_NAME = "K-and-K/perturbed-knights-and-knaves"

def parse_oracle_statements(st):
    """
    数据集里的 statements 往往是字符串 "((...),(...))"，先解析成 python 对象供 oracle baseline 使用。
    """
    if isinstance(st, (list, tuple)):
        return st
    if isinstance(st, str):
        return ast.literal_eval(st)
    raise ValueError(type(st))

def run_split(ds, split_name, max_samples=50):
    data = ds[split_name]
    total = 0
    correct_llm = 0
    correct_oracle = 0

    fail_parse = 0
    fail_unsat = 0
    fail_multi = 0
    fail_other = 0

    for idx, ex in enumerate(data):
        if max_samples is not None and idx >= max_samples:
            break

        total += 1
        quiz = ex["quiz"]
        gt = ex["solution"]  # list[bool]

        try:
            oracle_statements = parse_oracle_statements(ex["statements"])
            pred_oracle, st_oracle = solve_one(oracle_statements)
            if st_oracle == "UNIQUE" and pred_oracle == gt:
                correct_oracle += 1
        except Exception:
            pass

        try:
            print(f"\n=== sample {idx} ===")
            print("[1] LLM parse start")
            people, llm_statements = llm_quiz_to_statements(quiz, max_retries=2)
            print("[2] LLM parse done")
            pred, status = solve_one(llm_statements)
            print("[3] CSP solved:", status)
            if status == "UNSAT":
                fail_unsat += 1
                continue
            if status == "MULTI":
                fail_multi += 1
                continue
            if status != "UNIQUE":
                fail_other += 1
                continue

            if pred == gt:
                correct_llm += 1

        except Exception:
            fail_parse += 1

    acc_llm = correct_llm / total if total else 0.0
    acc_oracle = correct_oracle / total if total else 0.0
    return {
        "split": split_name,
        "total": total,
        "llm_acc": acc_llm,
        "oracle_acc": acc_oracle,
        "fail_parse": fail_parse,
        "unsat": fail_unsat,
        "multi": fail_multi,
        "other": fail_other,
    }

def main():
    ds = load_dataset(DATASET_NAME, "train")
    splits = list(ds.keys())
    print("splits:", splits)

    max_samples = 10 #最大样本数量

    for s in splits:
        r = run_split(ds, s, max_samples=max_samples)
        print(
            f"[{r['split']}] llm_acc={r['llm_acc']:.3f} oracle_acc={r['oracle_acc']:.3f} "
            f"total={r['total']} parse_fail={r['fail_parse']} unsat={r['unsat']} multi={r['multi']} other={r['other']}"
        )

if __name__ == "__main__":
    main()