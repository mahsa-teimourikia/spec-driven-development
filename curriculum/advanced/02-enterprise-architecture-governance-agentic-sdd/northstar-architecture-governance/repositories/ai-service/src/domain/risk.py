"""Domain logic remains independent of infrastructure adapters."""


def risk_band(score: int) -> str:
    return "high" if score >= 80 else "standard"
