"""Runs the scenario on the API version and writes results/api.json.
Usage:  python API/main.py --scenario scenario.json --out results/api.json"""
import argparse
import json
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # so "import API..." and "import shared..." work

from API.agent import JobHuntAgent  # noqa: E402
from shared import checks  # noqa: E402

FILE = "main.py"
HARNESS_PARTS = ["loop", "tools", "history", "memory", "context",
                 "compaction", "caching", "tokens"]


def log(msg: str) -> None:
    print(f"[{FILE}] {msg}")


def lib_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not installed"


def run_scenario(scenario: dict, make_client, model: str, effort: str,
                 compact_threshold: int) -> dict:
    checks.clean_state()
    turns, extra = [], {}
    n = 0
    for s_idx, session in enumerate(scenario["sessions"], start=1):
        log(f"===== session {s_idx}: NEW agent instance =====")
        agent = JobHuntAgent(make_client(), model=model, effort=effort,
                             compact_threshold=compact_threshold)
        if s_idx == 2:
            extra["session2_loaded"] = len(agent.messages)
        for user_text in session:
            n += 1
            log(f"----- turn {n} -----")
            r = agent.ask(user_text)
            u = r["usage"]
            turns.append({
                "session": s_idx, "turn": n, "user": user_text, "response": r["text"],
                "tools_called": r["tools_called"], "model_calls": r["model_calls"],
                "tokens": {k: u[k] for k in ("input", "cache_read", "cache_write", "output")},
                "cost_usd": u["cost_usd"], "seconds": r["seconds"],
            })
    results = checks.run_checks(scenario["checks"], turns, extra)
    harness = ROOT / "API" / "harness"
    loc = {p: checks.count_code_lines(harness / f"{p}.py") for p in HARNESS_PARTS}
    loc["agent+main"] = (checks.count_code_lines(ROOT / "API" / "agent.py")
                         + checks.count_code_lines(ROOT / "API" / "main.py"))
    loc["total"] = sum(loc.values())
    return {
        "version": "api", "model": model, "effort": effort,
        "libraries": {"anthropic": lib_version("anthropic")},
        "turns": turns, "totals": checks.totals(turns),
        "checks": results,
        "checks_passed": f"{sum(c['passed'] for c in results)}/{len(results)}",
        "lines_of_code": loc,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--model", default="claude-opus-5-5")
    p.add_argument("--effort", default="medium")
    p.add_argument("--compact-threshold", type=int, default=20_000)
    args = p.parse_args()

    try:
        import truststore
        truststore.inject_into_ssl()  # use the Windows certificate store (needed behind NetFree)
    except ImportError:
        pass

    import anthropic  # reads ANTHROPIC_API_KEY from the environment
    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    out = run_scenario(scenario, anthropic.Anthropic, args.model, args.effort,
                       args.compact_threshold)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"checks passed: {out['checks_passed']}")
    log(f"totals: {out['totals']}")
    log(f"saved {args.out}")


if __name__ == "__main__":
    main()