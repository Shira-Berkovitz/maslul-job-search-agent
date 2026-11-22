"""Runs the scenario on the SDK version and writes results/sdk.json.
Usage:  python SDK/main.py --scenario scenario.json --out results/sdk.json
Runs on your Claude Code login: ANTHROPIC_API_KEY must NOT be set."""
import argparse
import asyncio
import json
import os
import re
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared import checks  # noqa: E402

FILE = "main.py"


def log(msg: str) -> None:
    print(f"[SDK/{FILE}] {msg}")


def lib_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not installed"


def count_replaces() -> dict:
    """For each API harness file, how many SDK lines replace it (# replaces: <name>)."""
    counts: dict[str, int] = {}
    for f in sorted((ROOT / "SDK").glob("*.py")):
        for line in f.read_text(encoding="utf-8").splitlines():
            for name in re.findall(r"# replaces: (\w+)", line):
                counts[name] = counts.get(name, 0) + 1
    counts["sdk_total"] = sum(checks.count_code_lines(f) for f in (ROOT / "SDK").glob("*.py"))
    return counts


async def run_scenario(scenario: dict, model: str, effort: str) -> dict:
    from SDK import tools
    from SDK.agent import SdkJobHuntAgent, load_session_id

    checks.clean_state()
    turns, extra = [], {}
    n = 0
    for s_idx, session in enumerate(scenario["sessions"], start=1):
        log(f"===== session {s_idx}: NEW agent instance =====")
        resume = load_session_id() if s_idx > 1 else None
        if s_idx == 2:
            has_memory = (tools.workspace() / "CLAUDE.md").exists()
            extra["session2_loaded"] = int(resume is not None) + int(has_memory)
            log(f"resume={resume}, CLAUDE.md exists={has_memory}")
        async with SdkJobHuntAgent(model=model, effort=effort, resume=resume) as agent:
            for user_text in session:
                n += 1
                log(f"----- turn {n} -----")
                r = await agent.ask(user_text)
                turns.append({"session": s_idx, "turn": n, "user": user_text,
                              "response": r.pop("text"), **r})
    results = checks.run_checks(scenario["checks"], turns, extra)
    return {
        "version": "sdk", "model": model, "effort": effort,
        "libraries": {"claude-agent-sdk": lib_version("claude-agent-sdk")},
        "turns": turns, "totals": checks.totals(turns),
        "checks": results,
        "checks_passed": f"{sum(c['passed'] for c in results)}/{len(results)}",
        "lines_of_code": count_replaces(),
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--model", default="claude-opus-5-5")
    p.add_argument("--effort", default="medium")
    args = p.parse_args()

    if os.environ.pop("ANTHROPIC_API_KEY", None):
        log("ANTHROPIC_API_KEY was set: removed it, so the run uses your Claude Code login")
    try:
        import truststore
        truststore.inject_into_ssl()  # for fetch_job_posting behind NetFree
    except ImportError:
        pass

    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    out = asyncio.run(run_scenario(scenario, args.model, args.effort))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"checks passed: {out['checks_passed']}")
    log(f"totals: {out['totals']}")
    log(f"saved {args.out}")


if __name__ == "__main__":
    main()