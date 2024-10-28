import re

bad_separators = re.compile("[-.]+")


def sanitize_name(name: str) -> str:
    return bad_separators.sub("_", name)
