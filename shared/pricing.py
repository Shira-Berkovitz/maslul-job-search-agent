"""Claude Opus 5.5 prices, USD per 1M tokens (same numbers as API/harness/tokens.py).
Source: https://platform.claude.com/docs/en/about-claude/pricing"""
PRICE_INPUT = 4.00
PRICE_OUTPUT = 20.00
PRICE_CACHE_WRITE = 5.00   # 5-minute cache write
PRICE_CACHE_READ = 0.20


def cost(tokens: dict) -> float:
    """tokens: {"input", "output", "cache_read", "cache_write"}"""
    return round((tokens["input"] * PRICE_INPUT + tokens["output"] * PRICE_OUTPUT
                  + tokens["cache_read"] * PRICE_CACHE_READ
                  + tokens["cache_write"] * PRICE_CACHE_WRITE) / 1_000_000, 6)