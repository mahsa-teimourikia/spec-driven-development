"""Northstar classification through the governed gateway."""

from northstar_ai_gateway import GatewayClient


def classify(document_text: str) -> str:
    return GatewayClient().classify(document_text)
