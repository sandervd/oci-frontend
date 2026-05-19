from fnmatch import fnmatchcase


def is_allowed(repository: str, patterns: list[str]) -> bool:
    allowed = False
    for raw_pattern in patterns:
        pattern = raw_pattern.strip()
        if not pattern or pattern.startswith("#"):
            continue
        negated = pattern.startswith("!")
        if negated:
            pattern = pattern[1:]
        if fnmatchcase(repository, pattern):
            allowed = not negated
    return allowed
