import sys

from bluesky import Msg, RunEngine
from bluesky import plans as bp
from bluesky.preprocessors import plan_mutator


def _inject_something(msg: Msg):
    # We only want to mutate the open_run metadata
    if msg.command != "open_run":
        return (None, None)

    def head(msg: Msg):
        # Create a new, but equivalent, message
        new_msg = msg._replace(kwargs=msg.kwargs)
        assert msg == new_msg
        assert msg is not new_msg
        return (yield new_msg)

    return (head(msg), None)


def main() -> int:
    # Create a simple plan
    plan = bp.count([])
    plan = plan_mutator(plan, _inject_something)
    # Let the plan run
    msgs = list(plan)
    assert len(msgs) == 7
    print(f"Emitted {len(msgs)} messages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
