"""A fake Anthropic client for offline tests: returns scripted responses, no API key."""
from types import SimpleNamespace


def usage(inp=100, out=20, cr=0, cw=0):
    return SimpleNamespace(input_tokens=inp, output_tokens=out,
                           cache_read_input_tokens=cr, cache_creation_input_tokens=cw)


def text_response(text):
    return SimpleNamespace(stop_reason="end_turn", usage=usage(),
                           content=[{"type": "text", "text": text}])


def tool_response(*calls):
    """calls: (id, name, input) tuples."""
    blocks = [{"type": "tool_use", "id": i, "name": n, "input": a} for i, n, a in calls]
    return SimpleNamespace(stop_reason="tool_use", usage=usage(), content=blocks)


class FakeClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []  # every request the harness sent, for assertions
        self.messages = self  # so client.messages.create(...) works

    def create(self, **kwargs):
        import copy
        self.requests.append(copy.deepcopy(kwargs))
        return self._responses.pop(0)