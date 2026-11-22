"""The API version of the agent: connects all the harness parts together."""
import time

from API.harness import compaction, context, loop
from API.harness.history import History
from API.harness.tokens import TokenMeter
from API.harness.tools import TOOLS

FILE = "agent.py"


def log(msg: str) -> None:
    print(f"[{FILE}] {msg}")


class JobHuntAgent:
    def __init__(self, client, model: str = "claude-opus-5-5", effort: str = "medium",
                 compact_threshold: int = 20_000):
        self.client = client
        self.model = model
        self.effort = effort
        self.compact_threshold = compact_threshold
        self.history = History()
        self.meter = TokenMeter()
        # A new instance continues from whatever is saved on disk (session 2)
        self.messages = context.messages_from_history(self.history.read_all())
        log(f"agent ready (model={model}, effort={effort}, "
            f"{len(self.messages)} message(s) loaded)")

    def ask(self, user_text: str) -> dict:
        start = time.perf_counter()
        log(f"user: {user_text}")

        self.messages = compaction.maybe_compact(
            self.client, self.messages, history=self.history, meter=self.meter,
            model=self.model, threshold=self.compact_threshold)

        user_msg = context.build_user_message(user_text)
        self.messages.append(user_msg)
        self.history.append(user_msg)

        result = loop.run_turn(
            self.client, self.messages, system=context.SYSTEM_PROMPT, tools=TOOLS,
            meter=self.meter, history=self.history, model=self.model,
            extra={"output_config": {"effort": self.effort}})

        usage = self.meter.end_turn()
        result["usage"] = usage
        result["model_calls"] = usage["model_calls"]  # includes a compaction call, if any
        result["seconds"] = round(time.perf_counter() - start, 2)
        log(f"assistant: {result['text'][:200]}")
        return result