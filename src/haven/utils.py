import re

bad_separators = re.compile("[-. ]+")


def sanitize_name(name: str) -> str:
    """Convert *name* into something usable as a queueserver device."""
    return bad_separators.sub("_", name)
