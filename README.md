# LLM-CSP Logic Agent
An agent that translates natural-language logic puzzles(k-k Problem) into constraint models and solves them using a deterministic CSP solver.
LLM is used for semantic parsing, while logical reasoning is delegated to a constraint solver (python-constraint).

---

## Requirements

- Python 3.10+
- python-constraint
- requests
- datasets

Install dependencies:

```bash
pip install -r requirements.txt
