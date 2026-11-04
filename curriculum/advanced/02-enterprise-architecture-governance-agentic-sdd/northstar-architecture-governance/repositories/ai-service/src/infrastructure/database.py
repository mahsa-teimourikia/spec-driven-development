"""Infrastructure adapter used by application services, never by domain code."""


def connection() -> str:
    return "governed-adapter"
