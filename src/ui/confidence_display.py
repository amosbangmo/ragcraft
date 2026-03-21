"""Read-only labels for pipeline confidence (no scoring logic)."""


def confidence_band(confidence: float) -> str:
    if confidence >= 0.7:
        return "High"
    if confidence >= 0.4:
        return "Medium"
    return "Low"


def format_confidence_with_band(confidence: float) -> str:
    return f"{confidence:.2f} ({confidence_band(confidence)})"
