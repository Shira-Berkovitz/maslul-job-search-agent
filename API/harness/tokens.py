"""Token usage and cost, per model call and per turn."""
FILE = "tokens.py"


PRICE_INPUT = 4.00
PRICE_OUTPUT = 20.00
PRICE_CACHE_WRITE = 5.00   # 5-minute cache write (1.25x input)
PRICE_CACHE_READ = 0.20    # cache read (0.05x input)


def log(msg: str) -> None:
    print(f"[{FILE}] {msg}")


class TokenMeter:
    def __init__(self):
        self.turn = self._empty()
        self.turns: list[dict] = []

    @staticmethod
    def _empty() -> dict:
        return {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0,
                "model_calls": 0, "cost_usd": 0.0}

    def record(self, usage) -> None:
        """Called after every model call with response.usage."""
        inp = getattr(usage, "input_tokens", 0) or 0
        out = getattr(usage, "output_tokens", 0) or 0
        cr = getattr(usage, "cache_read_input_tokens", 0) or 0
        cw = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cost = (inp * PRICE_INPUT + out * PRICE_OUTPUT
                + cr * PRICE_CACHE_READ + cw * PRICE_CACHE_WRITE) / 1_000_000
        t = self.turn
        t["input"] += inp
        t["output"] += out
        t["cache_read"] += cr
        t["cache_write"] += cw
        t["model_calls"] += 1
        t["cost_usd"] += cost
        log(f"call: in={inp} cache_read={cr} cache_write={cw} out={out} cost=${cost:.4f}")

    def end_turn(self) -> dict:
        t = self.turn
        t["cost_usd"] = round(t["cost_usd"], 6)
        log(f"turn total: {t}")
        self.turns.append(t)
        self.turn = self._empty()
        return t