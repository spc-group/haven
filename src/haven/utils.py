import re

bad_separators = re.compile("[-. ]+")


def titleize(name):
    """Convert a device name into a human-readable title."""
    title = name.replace("_", " ").title()
    # Replace select phrases that are known to be incorrect
    replacements = {"Kb ": "KB "}
    for orig, new in replacements.items():
        title = title.replace(orig, new)
    return title


def sanitize_name(name: str) -> str:
    """Convert *name* into something usable as a queueserver device."""
    return bad_separators.sub("_", name)
